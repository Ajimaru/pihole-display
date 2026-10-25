"""Password hashing, sessions, and login rate limiting for the web UI."""

# ============================================================
# web_auth.py — authentication state for the web server
# Standard library only: no extra dependency on the BBB.
# ============================================================

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import threading
import time
from typing import Optional

import config

log = logging.getLogger(__name__)

# The password every fresh install starts with. It is public (it is in the
# repository), so must_change is set until the user picks a new one.
DEFAULT_PASSWORD = 'pihole'

MIN_PASSWORD_LEN = 8

# PBKDF2 cost. Deliberately slow to make brute force expensive; this only
# runs on login, never on frame or button requests. The value is stored in
# the auth file, so it can be lowered on slow hardware without invalidating
# existing hashes.
DEFAULT_ITERATIONS = 200000

_ALGO = 'pbkdf2_sha256'


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode('ascii')


def _unb64(text: str) -> bytes:
    return base64.b64decode(text.encode('ascii'))


def _derive(password: str, salt: bytes, iterations: int) -> bytes:
    return hashlib.pbkdf2_hmac(
        'sha256', password.encode('utf-8'), salt, iterations,
    )


class AuthManager:
    """Store the web password, hand out session tokens, throttle logins.

    Sessions live in memory only, so restarting the service logs everyone
    out and no tokens are ever written to the SD card.
    """

    def __init__(self, path: str = None):
        self._path = path or config.WEB_AUTH_FILE
        self._lock = threading.Lock()
        self._sessions = {}          # token -> expiry (monotonic)
        self._attempts = {}          # ip -> [failures, locked_until]
        self._record = self._load_or_create()

    # ── Persistence ──────────────────────────────────────────

    def _load_or_create(self) -> dict:
        try:
            with open(self._path, encoding='utf-8') as f:
                record = json.load(f)
            if record.get('algo') == _ALGO and record.get('hash'):
                return record
            log.warning('Auth file %s unusable - recreating', self._path)
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as e:
            log.warning('Reading %s failed (%s) - recreating', self._path, e)

        record = self._build_record(DEFAULT_PASSWORD, must_change=True)
        self._write(record)
        return record

    @staticmethod
    def _build_record(password: str, must_change: bool) -> dict:
        salt = secrets.token_bytes(16)
        iterations = DEFAULT_ITERATIONS
        return {
            'user': config.WEB_USER,
            'algo': _ALGO,
            'iterations': iterations,
            'salt': _b64(salt),
            'hash': _b64(_derive(password, salt, iterations)),
            'must_change': must_change,
            'updated': int(time.time()),
        }

    def _write(self, record: dict):
        """Write the auth file, never leaving it world-readable."""
        directory = os.path.dirname(self._path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        tmp = f'{self._path}.tmp'
        try:
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(record, f)
            os.replace(tmp, self._path)
        except OSError as e:
            log.error('Writing %s failed: %s', self._path, e)

    # ── Passwords ────────────────────────────────────────────

    @property
    def user(self) -> str:
        """Return the configured login name."""
        return self._record.get('user', config.WEB_USER)

    def verify(self, user: str, password: str) -> bool:
        """Check a login, in constant time for both name and password.

        The user name is matched case-insensitively and without
        surrounding whitespace: it is not a secret, and phones like to
        capitalise it. The password is compared exactly, but stripped of
        surrounding whitespace, which is otherwise an invisible reason
        for a copy-pasted password to be rejected.
        """
        with self._lock:
            record = self._record
        password = password.strip()
        expected = _derive(
            password,
            _unb64(record['salt']),
            record.get('iterations', DEFAULT_ITERATIONS),
        )
        user_ok = hmac.compare_digest(
            user.strip().lower().encode('utf-8'),
            record.get('user', config.WEB_USER).strip().lower().encode('utf-8'),
        )
        pw_ok = hmac.compare_digest(expected, _unb64(record['hash']))
        return user_ok and pw_ok

    def set_password(self, password: str):
        """Replace the stored password and clear the forced-change flag.

        Stripped the same way verify() strips, so a password that was
        pasted with a stray space can still be typed in later.
        """
        record = self._build_record(password.strip(), must_change=False)
        with self._lock:
            self._record = record
            self._write(record)
            # A new password invalidates every existing session.
            self._sessions.clear()
        log.info('Web password changed')

    @staticmethod
    def password_problem(password: str, repeat: str) -> Optional[str]:
        """Return why a new password is unacceptable, or None if it is fine.

        Judges the stripped password, because that is what gets stored.
        """
        password = password.strip()
        if password != repeat.strip():
            return 'The passwords do not match.'
        if len(password) < MIN_PASSWORD_LEN:
            return f'At least {MIN_PASSWORD_LEN} characters required.'
        if password == DEFAULT_PASSWORD:
            return 'The default password is not allowed.'
        return None

    def must_change(self) -> bool:
        """Whether the user still has to pick their own password."""
        return bool(self._record.get('must_change'))

    def is_default_password(self) -> bool:
        """Whether the publicly known default password is still active."""
        return self.must_change() and self.verify(
            self.user, DEFAULT_PASSWORD,
        )

    # ── Sessions ─────────────────────────────────────────────

    def create_session(self) -> str:
        """Issue a new session token valid for WEB_SESSION_HOURS."""
        token = secrets.token_urlsafe(32)
        expiry = time.monotonic() + config.WEB_SESSION_HOURS * 3600
        with self._lock:
            self._prune_sessions()
            self._sessions[token] = expiry
        return token

    def validate_session(self, token: Optional[str]) -> bool:
        """Check a session token and drop it if it has expired."""
        if not token:
            return False
        with self._lock:
            expiry = self._sessions.get(token)
            if expiry is None:
                return False
            if expiry < time.monotonic():
                del self._sessions[token]
                return False
            return True

    def destroy_session(self, token: Optional[str]):
        """Invalidate a single session token."""
        if not token:
            return
        with self._lock:
            self._sessions.pop(token, None)

    def _prune_sessions(self):
        """Drop expired tokens. Caller holds the lock."""
        now = time.monotonic()
        for token in [t for t, e in self._sessions.items() if e < now]:
            del self._sessions[token]

    # ── Rate limiting ────────────────────────────────────────

    def lockout_remaining(self, ip: str) -> int:
        """Return how many seconds this IP stays locked out, 0 if it is not."""
        with self._lock:
            self._prune_attempts()
            entry = self._attempts.get(ip)
            if not entry:
                return 0
            return max(0, int(entry[1] - time.monotonic()))

    def record_failure(self, ip: str):
        """Count a failed login and lock the IP out once the limit is hit."""
        with self._lock:
            self._prune_attempts()
            entry = self._attempts.setdefault(ip, [0, 0.0])
            entry[0] += 1
            if entry[0] >= config.WEB_MAX_ATTEMPTS:
                entry[0] = 0
                entry[1] = time.monotonic() + config.WEB_LOCKOUT_SEC
                log.warning(
                    'Web login locked out for %s (%ds)',
                    ip, config.WEB_LOCKOUT_SEC,
                )

    def record_success(self, ip: str):
        """Clear the failure count for an IP after a successful login."""
        with self._lock:
            self._attempts.pop(ip, None)

    def _prune_attempts(self):
        """Drop entries whose lockout has expired. Caller holds the lock.

        Without this the dict would grow for every IP that ever failed.
        """
        now = time.monotonic()
        for ip in [
            i for i, e in self._attempts.items()
            if e[1] < now and e[0] == 0
        ]:
            del self._attempts[ip]
