"""HTTP server mirroring the OLED and exposing the buttons to a browser.

Standard library only. The server owns no display or GPIO state: it reads
rendered frames through a sink registered on DisplayManager, and feeds
button events into the very same callback the GPIO thread uses, so a click
in the browser is indistinguishable from a real key press.
"""

# ============================================================
# web_server.py — OLED mirror + clickable hardware buttons
# ============================================================

import hashlib
import io
import json
import logging
import threading
import time
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, Optional

from PIL import Image

import config
import web_ui
from button_handler import ButtonEvent
from version import __version__

log = logging.getLogger(__name__)

COOKIE_NAME = 'phd_session'

# Bodies are tiny (a login form, a button name). Anything larger is junk.
MAX_BODY = 4096

# A press whose release never arrives - closed tab, dropped Wi-Fi - must not
# leave a button stuck down forever.
PRESS_TIMEOUT = config.HOLD_MS / 1000.0 + 2.0

_BUTTONS = {'up', 'down', 'ok', 'back'}

_EVENTS = {
    ('up',   'short'): ButtonEvent.UP_SHORT,
    ('up',   'long'):  ButtonEvent.UP_LONG,
    ('down', 'short'): ButtonEvent.DOWN_SHORT,
    ('down', 'long'):  ButtonEvent.DOWN_LONG,
    ('ok',   'short'): ButtonEvent.OK_SHORT,
    ('ok',   'long'):  ButtonEvent.OK_LONG,
    ('back', 'short'): ButtonEvent.BACK_SHORT,
    ('back', 'long'):  ButtonEvent.BACK_LONG,
    ('back', 'hold'):  ButtonEvent.BACK_HOLD,
}


# ── Frame buffer ─────────────────────────────────────────────

class FrameBuffer:
    """Hold the latest rendered frame and encode it only when asked.

    The display renders ~10x a second, but the picture rarely changes and
    nobody may be watching. Hashing 1024 bytes of raw pixels per frame is
    cheap; PNG encoding is not, so it happens lazily and at most once per
    distinct frame.
    """

    def __init__(self, width: int, height: int):
        self._width = width
        self._height = height
        self._lock = threading.Lock()
        self._image = None
        self._hash = ''
        self._png = None
        self._blank = Image.new('1', (width, height), 0)
        self.put(None)

    def put(self, image):
        """Store a frame. None means the display is asleep (black).

        The caller hands in the live canvas image and must not keep a
        reference to it; this takes its own copy, but only for a frame it
        actually keeps. The display renders ~10x a second while the
        picture usually stays the same, so copying first and discarding
        after would waste a copy on nearly every frame.
        """
        img = self._blank if image is None else image
        if not isinstance(img, Image.Image):
            # Guard against being handed a raw ImagingCore or similar:
            # converting one silently yields a blank frame, which looks
            # like a working mirror showing nothing.
            raise TypeError(f'expected PIL.Image, got {type(img).__name__}')
        if img.mode != '1':
            img = img.convert('1')
        digest = hashlib.blake2b(img.tobytes(), digest_size=8).hexdigest()
        with self._lock:
            if digest == self._hash:
                return
            # New frame: now the copy is worth making. convert() above
            # already produced a fresh image, so only copy when it did not.
            self._image = img if img is not image else img.copy()
            self._hash = digest
            self._png = None      # invalidate, encode on demand

    @property
    def etag(self) -> str:
        """Current frame identity, used for If-None-Match."""
        with self._lock:
            return f'"{self._hash}"'

    def png(self) -> bytes:
        """Return the current frame as PNG, encoding it at most once."""
        with self._lock:
            if self._png is None:
                buf = io.BytesIO()
                self._image.save(buf, format='PNG', optimize=False)
                self._png = buf.getvalue()
            return self._png


# ── Press tracking ───────────────────────────────────────────

class PressTracker:
    """Turn browser down/up events into the same events the GPIO emits.

    Classification lives here rather than in the browser so the web UI
    cannot drift away from button_handler.py when the thresholds in
    config.py are changed.
    """

    def __init__(self, dispatch: Callable[[ButtonEvent], None]):
        self._dispatch = dispatch
        self._lock = threading.Lock()
        self._down = {}       # button -> [start, hold_fired, timer]

    def press(self, button: str):
        """Record a button going down and arm its hold timer."""
        with self._lock:
            self._drop_stale()
            if button in self._down:
                return
            timer = threading.Timer(
                config.HOLD_MS / 1000.0, self._on_hold, args=(button,),
            )
            timer.daemon = True
            self._down[button] = [time.monotonic(), False, timer]
            timer.start()

    def release(self, button: str):
        """Record a button going up and emit the short or long event."""
        with self._lock:
            entry = self._down.pop(button, None)
            if entry is None:
                return
            start, hold_fired, timer = entry
            timer.cancel()
            if hold_fired:
                # The hold already fired while the button was down - the
                # GPIO handler suppresses the release event too.
                return
            held = time.monotonic() - start
        kind = 'long' if held >= config.LONG_PRESS_MS / 1000.0 else 'short'
        self._emit(button, kind)

    def _on_hold(self, button: str):
        with self._lock:
            entry = self._down.get(button)
            if entry is None or entry[1]:
                return
            entry[1] = True
        self._emit(button, 'hold')

    def _drop_stale(self):
        """Forget presses whose release never arrived. Caller holds lock."""
        now = time.monotonic()
        for button in [
            b for b, e in self._down.items()
            if now - e[0] > PRESS_TIMEOUT
        ]:
            self._down.pop(button)[2].cancel()
            log.debug('Dropped stale web press: %s', button)

    def cancel_all(self):
        """Cancel every pending hold timer, used on shutdown."""
        with self._lock:
            for entry in self._down.values():
                entry[2].cancel()
            self._down.clear()

    def _emit(self, button: str, kind: str):
        event = _EVENTS.get((button, kind))
        if event is None:
            return
        log.debug('Web button: %s', event.name)
        try:
            self._dispatch(event)
        except Exception as e:  # pylint: disable=broad-except
            log.error('Web button dispatch failed: %s', e)


# ── Request handler ──────────────────────────────────────────

class _Handler(BaseHTTPRequestHandler):
    """Route requests. The WebServer is attached to the socket server."""

    server_version = 'pihole-display'
    sys_version = ''
    protocol_version = 'HTTP/1.1'

    # ── plumbing ─────────────────────────────────────────────

    @property
    def _app(self) -> 'WebServer':
        return self.server.app  # type: ignore[attr-defined]

    def log_message(self, format, *args):  # pylint: disable=redefined-builtin
        """Silence per-request logging.

        A browser polls twice a second; logging that would write thousands
        of journal lines an hour onto the SD card.
        """

    def _client_ip(self) -> str:
        return self.client_address[0] if self.client_address else '?'

    def _send(self, status, body=b'', ctype='text/html; charset=utf-8',
              extra=None):
        if isinstance(body, str):
            body = body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'same-origin')
        self.send_header(
            'Content-Security-Policy',
            "default-src 'none'; img-src 'self' data: blob:; "
            "style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
            "connect-src 'self'; form-action 'self'; base-uri 'none'",
        )
        for key, value in (extra or []):
            self.send_header(key, value)
        self.end_headers()
        if self.command != 'HEAD' and body:
            self.wfile.write(body)

    def _redirect(self, location: str, extra=None):
        self._send(
            HTTPStatus.SEE_OTHER, b'',
            extra=[('Location', location)] + list(extra or []),
        )

    def _json(self, status, payload: dict):
        self._send(
            status, json.dumps(payload), 'application/json; charset=utf-8',
        )

    def _body(self) -> bytes:
        try:
            length = int(self.headers.get('Content-Length') or 0)
        except ValueError:
            return b''
        if length <= 0 or length > MAX_BODY:
            return b''
        return self.rfile.read(length)

    def _form(self) -> dict:
        parsed = urllib.parse.parse_qs(
            self._body().decode('utf-8', 'replace'),
        )
        return {k: v[0] for k, v in parsed.items()}

    # ── auth helpers ─────────────────────────────────────────

    def _token(self) -> Optional[str]:
        raw = self.headers.get('Cookie') or ''
        for part in raw.split(';'):
            name, _, value = part.strip().partition('=')
            if name == COOKIE_NAME:
                return value
        return None

    def _authed(self) -> bool:
        return self._app.auth.validate_session(self._token())

    def _same_origin(self) -> bool:
        """Reject cross-site POSTs.

        SameSite=Strict already blocks the cookie on cross-site requests;
        this is the second lock on the same door.
        """
        origin = self.headers.get('Origin')
        if origin is None:
            referer = self.headers.get('Referer')
            if referer is None:
                return True          # curl and friends, no browser context
            origin = '://'.join(urllib.parse.urlparse(referer)[:2])
        host = self.headers.get('Host') or ''
        return urllib.parse.urlparse(origin).netloc == host

    @staticmethod
    def _cookie(token: str) -> tuple:
        return (
            'Set-Cookie',
            f'{COOKIE_NAME}={token}; Path=/; HttpOnly; SameSite=Strict; '
            f'Max-Age={config.WEB_SESSION_HOURS * 3600}',
        )

    @staticmethod
    def _clear_cookie() -> tuple:
        return (
            'Set-Cookie',
            f'{COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0',
        )

    # ── routing ──────────────────────────────────────────────

    # A flat chain of early returns is the clearest way to express
    # routing; splitting it would only scatter it.
    def do_GET(self):  # pylint: disable=invalid-name,R0911
        """Serve the mirror page, the forms, and the current frame."""
        path = urllib.parse.urlparse(self.path).path.rstrip('/') or '/'
        auth = self._app.auth

        if path == '/login':
            if self._authed():
                self._redirect('/')
                return
            self._send(HTTPStatus.OK, web_ui.login(
                auth.user, show_default_hint=auth.is_default_password(),
            ))
            return

        if not self._authed():
            if path == '/frame.png':
                self._send(HTTPStatus.UNAUTHORIZED, b'', 'text/plain')
            else:
                self._redirect('/login')
            return

        if auth.must_change() and path != '/change':
            self._redirect('/change')
            return

        if path == '/change':
            self._send(HTTPStatus.OK, web_ui.change(forced=auth.must_change()))
            return

        if path == '/frame.png':
            self._serve_frame()
            return

        if path == '/':
            self._send(HTTPStatus.OK, web_ui.page(
                __version__,
                auth.is_default_password(),
                self._app.frames_width,
                self._app.frames_height,
            ))
            return

        self._send(HTTPStatus.NOT_FOUND, 'Not found', 'text/plain')

    def do_HEAD(self):  # pylint: disable=invalid-name
        """HEAD is handled by do_GET, which omits the body."""
        self.do_GET()

    def do_POST(self):  # pylint: disable=invalid-name,R0911
        """Handle login, logout, password change, and button events."""
        path = urllib.parse.urlparse(self.path).path.rstrip('/') or '/'

        if not self._same_origin():
            self._send(HTTPStatus.FORBIDDEN, 'Bad origin', 'text/plain')
            return

        if path == '/api/login':
            self._post_login()
            return

        if not self._authed():
            self._json(HTTPStatus.UNAUTHORIZED, {'error': 'unauthorized'})
            return

        if path == '/api/logout':
            self._app.auth.destroy_session(self._token())
            self._json(HTTPStatus.OK, {'ok': True})
            return

        if path == '/api/password':
            self._post_password()
            return

        if self._app.auth.must_change():
            self._json(
                HTTPStatus.FORBIDDEN, {'error': 'password change required'},
            )
            return

        if path in ('/api/press', '/api/release'):
            self._post_button(path.endswith('press'))
            return

        self._json(HTTPStatus.NOT_FOUND, {'error': 'not found'})

    # ── handlers ─────────────────────────────────────────────

    def _serve_frame(self):
        frames = self._app.frames
        etag = frames.etag
        if self.headers.get('If-None-Match') == etag:
            # Unchanged: no PNG is encoded at all.
            self.send_response(HTTPStatus.NOT_MODIFIED)
            self.send_header('ETag', etag)
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            return
        self._send(
            HTTPStatus.OK, frames.png(), 'image/png',
            extra=[('ETag', etag), ('Cache-Control', 'no-store')],
        )

    def _post_login(self):
        auth = self._app.auth
        ip = self._client_ip()
        remaining = auth.lockout_remaining(ip)
        if remaining:
            self._send(HTTPStatus.TOO_MANY_REQUESTS, web_ui.login(
                auth.user,
                f'Too many attempts. Locked for {remaining}s.',
            ))
            return

        form = self._form()
        if auth.verify(form.get('user', ''), form.get('password', '')):
            auth.record_success(ip)
            token = auth.create_session()
            log.info('Web login from %s', ip)
            self._redirect(
                '/change' if auth.must_change() else '/',
                extra=[self._cookie(token)],
            )
            return

        auth.record_failure(ip)
        log.warning('Failed web login from %s', ip)
        default_active = auth.is_default_password()
        message = 'Wrong username or password.'
        if default_active:
            # The usual cause here is a password manager filling in a
            # value saved earlier - say so instead of just "wrong".
            message += (
                ' This device still has the default password. If your'
                ' browser filled the field in, clear it and type it'
                ' by hand.'
            )
        self._send(HTTPStatus.UNAUTHORIZED, web_ui.login(
            auth.user,
            message,
            show_default_hint=default_active,
        ))

    def _post_password(self):
        auth = self._app.auth
        form = self._form()
        password = form.get('password', '')
        problem = auth.password_problem(password, form.get('repeat', ''))
        if problem:
            self._send(HTTPStatus.BAD_REQUEST, web_ui.change(
                problem, forced=auth.must_change(),
            ))
            return
        auth.set_password(password)
        # set_password drops every session, so issue a fresh one instead of
        # bouncing the user back to the login form they just came through.
        self._redirect('/', extra=[self._cookie(auth.create_session())])

    def _post_button(self, is_press: bool):
        try:
            payload = json.loads(self._body().decode('utf-8', 'replace'))
            button = payload.get('button')
        except (ValueError, AttributeError):
            button = None

        if button not in _BUTTONS:
            self._json(HTTPStatus.BAD_REQUEST, {'error': 'unknown button'})
            return

        if is_press:
            self._app.presses.press(button)
        else:
            self._app.presses.release(button)
        self._json(HTTPStatus.OK, {'ok': True})


class _Server(ThreadingHTTPServer):
    """ThreadingHTTPServer carrying a reference to its WebServer."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, handler, app):
        self.app = app
        super().__init__(address, handler)


# ── Public API ───────────────────────────────────────────────

class WebServer:  # pylint: disable=R0902
    """Run the web UI in a daemon thread alongside the main loop."""

    def __init__(
        self, display, on_button: Callable[[ButtonEvent], None], auth,
    ):
        self.auth = auth
        self.frames_width = display.W
        self.frames_height = display.H
        self.frames = FrameBuffer(display.W, display.H)
        self.presses = PressTracker(on_button)
        self._display = display
        self._httpd = None
        self._thread = None

    def start(self):
        """Bind the socket and start serving. Raises if the port is taken."""
        self._httpd = _Server(
            (config.WEB_HOST, config.WEB_PORT), _Handler, self,
        )
        self._display.set_frame_sink(self.frames.put)
        self._thread = threading.Thread(
            target=self._httpd.serve_forever,
            kwargs={'poll_interval': 0.5},
            daemon=True,
        )
        self._thread.start()
        log.info(
            'Web UI on http://%s:%d',
            config.WEB_HOST, config.WEB_PORT,
        )

    def stop(self):
        """Stop serving and detach from the display."""
        self._display.set_frame_sink(None)
        self.presses.cancel_all()
        if self._httpd:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None
        log.info('Web UI stopped')
