"""HTML, CSS, and JavaScript for the web UI, served inline.

Everything is a Python constant: nothing is read from disk at request time,
so the server has no file-serving surface at all. No CDN, no web fonts, no
build step - the BBB serves this as-is.
"""

# ============================================================
# web_ui.py — the mirrored display and its four buttons
# ============================================================

import config

# Buttons top to bottom, ordered by what they do: up above down, so the
# arrows point the way they move. That is not the board order - K1 is 'v'
# and K2 is '^' because the display is mounted upside down (see
# config.py) - so every key keeps its hardware marking.
BUTTON_LAYOUT = [
    ('up',   'K2', '▲'),
    ('down', 'K1', '▼'),
    ('ok',   'K3', '#'),
    ('back', 'K4', '*'),
]

_BASE_CSS = """
:root {
  color-scheme: dark;
  --bg: #15181c;
  --case: #23272e;
  --case-edge: #0d0f12;
  --panel: #05070a;
  --pixel: #c8e4ff;
  --text: #d6dbe2;
  --muted: #828b98;
  --accent: #4a9eff;
  --warn-bg: #4a2318;
  --warn-edge: #b4541f;
  --warn-text: #ffd5bd;
  --err: #ff7a6b;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  padding: 24px 16px;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 18px;
  background: var(--bg);
  color: var(--text);
  font: 15px/1.5 ui-sans-serif, system-ui, -apple-system, "Segoe UI",
        Roboto, sans-serif;
  -webkit-text-size-adjust: 100%;
}
a { color: var(--accent); }
.muted { color: var(--muted); font-size: 13px; }
"""

# ── Main page ────────────────────────────────────────────────

_PAGE_CSS = """
.case {
  background: linear-gradient(180deg, var(--case) 0%, #1b1f25 100%);
  border: 1px solid var(--case-edge);
  border-radius: 14px;
  padding: 20px;
  box-shadow: 0 10px 30px rgba(0,0,0,.55), inset 0 1px 0 rgba(255,255,255,.04);
  max-width: 100%;
  /* display on the left, the button strip down the right-hand side */
  display: flex;
  align-items: stretch;
  gap: 18px;
}
.board { display: flex; flex-direction: column; min-width: 0; }
.panel {
  background: var(--panel);
  border: 1px solid #000;
  border-radius: 6px;
  padding: 7px;
  box-shadow: inset 0 0 14px rgba(0,0,0,.9);
  line-height: 0;
}
#frame {
  display: block;
  width: 512px;
  max-width: 100%;
  height: auto;
  /* keep the 128x64 grid crisp instead of smearing it */
  image-rendering: pixelated;
  image-rendering: crisp-edges;
}
.panel.stale { opacity: .35; transition: opacity .3s; }

.buttons {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 8px;
}
.btn {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
  flex: 1;
  background: none;
  border: 0;
  padding: 0;
  color: inherit;
  font: inherit;
  cursor: pointer;
  /* stop long-press from selecting text or firing the iOS callout */
  -webkit-touch-callout: none;
  -webkit-user-select: none;
  user-select: none;
  touch-action: manipulation;
}
.cap {
  width: 46px;
  height: 100%;
  min-height: 42px;
  border-radius: 4px;
  background: linear-gradient(180deg, #434a55 0%, #2b3038 62%, #1e222a 100%);
  border: 1px solid #0b0d10;
  box-shadow: 0 3px 0 #101318, 0 5px 9px rgba(0,0,0,.5),
              inset 0 1px 1px rgba(255,255,255,.1);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 17px;
  color: #aeb6c2;
  transition: transform .04s, box-shadow .04s, background .04s;
}
.btn.down .cap {
  transform: translateY(3px);
  background: linear-gradient(180deg, #2f343c 0%, #22262d 62%, #181b21 100%);
  box-shadow: 0 0 0 #101318, 0 1px 3px rgba(0,0,0,.6),
              inset 0 2px 4px rgba(0,0,0,.6);
  color: var(--pixel);
}
.btn:focus-visible .cap { outline: 2px solid var(--accent); outline-offset: 3px; }
.label {
  font-family: ui-monospace, "DejaVu Sans Mono", Menlo, Consolas, monospace;
  font-size: 11px; color: var(--muted); letter-spacing: .06em;
  order: -1;            /* marking to the left of the key, as on the board */
  width: 20px;
  text-align: right;
}
.btn.down .label { color: var(--pixel); }
.hold {
  margin-top: 10px;
  height: 16px;
  text-align: center;
  font-family: ui-monospace, "DejaVu Sans Mono", Menlo, Consolas, monospace;
  font-size: 12px;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}
.hold.armed { color: var(--pixel); }

@media (max-width: 560px) {
  .case { flex-direction: column; gap: 14px; }
  .buttons { flex-direction: row; gap: 10px; }
  .btn { flex-direction: column; gap: 6px; }
  .label { order: 0; width: auto; text-align: center; }
  .cap { width: 100%; min-height: 46px; }
}

.banner {
  max-width: 560px;
  font-family: ui-monospace, "DejaVu Sans Mono", Menlo, Consolas, monospace;
  background: var(--warn-bg);
  border: 1px solid var(--warn-edge);
  border-radius: 9px;
  padding: 12px 15px;
  color: var(--warn-text);
  font-size: 14px;
}
.banner a { color: #ffd5bd; font-weight: 600; }
.foot {
  display: flex;
  gap: 16px;
  align-items: center;
  font-family: ui-monospace, "DejaVu Sans Mono", Menlo, Consolas, monospace;
  font-size: 12px;
}
.foot button {
  background: none; border: 0; color: var(--muted);
  font: inherit; cursor: pointer; padding: 0;
}
.foot button:hover { color: var(--pixel); }
"""

_PAGE_JS = """
(function () {
  'use strict';

  var frame   = document.getElementById('frame');
  var panel   = document.getElementById('panel');
  var holdBox = document.getElementById('hold');
  var etag    = '';
  var missed  = 0;
  var timer   = null;

  var LONG_MS = %(long_ms)d;
  var HOLD_MS = %(hold_ms)d;

  // ---- display mirror ----------------------------------------------
  // The server answers 304 while the frame is unchanged, so this costs
  // almost nothing on the BBB when the screen is static.

  function poll() {
    var headers = etag ? { 'If-None-Match': etag } : {};
    fetch('frame.png', { headers: headers, cache: 'no-store' })
      .then(function (r) {
        if (r.status === 401) { location.href = 'login'; return null; }
        missed = 0;
        panel.classList.remove('stale');
        if (r.status === 304) return null;
        etag = r.headers.get('ETag') || '';
        return r.blob();
      })
      .then(function (blob) {
        if (!blob) return;
        var url = URL.createObjectURL(blob);
        var old = frame.src;
        frame.src = url;
        if (old.indexOf('blob:') === 0) URL.revokeObjectURL(old);
      })
      .catch(function () {
        if (++missed > 2) panel.classList.add('stale');
      })
      .finally(schedule);
  }

  function schedule() {
    clearTimeout(timer);
    // A hidden tab barely needs to be current; back off hard so a
    // forgotten background tab costs the BBB nothing.
    var delay = document.hidden ? 5000 : (missed > 2 ? 5000 : 500);
    timer = setTimeout(poll, delay);
  }

  document.addEventListener('visibilitychange', function () {
    if (!document.hidden) { missed = 0; poll(); }
  });

  // ---- buttons ------------------------------------------------------
  // Only down/up are sent. The server measures the real duration and
  // classifies it with the same thresholds as the GPIO handler, so the
  // web buttons cannot drift away from the hardware ones.

  var pressStart = null;
  var pressBtn   = null;
  var ticker     = null;

  function post(path, name) {
    return fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ button: name })
    }).then(function (r) {
      if (r.status === 401) location.href = 'login';
    }).catch(function () { /* mirror will show it went stale */ });
  }

  function tick() {
    if (pressStart === null) return;
    var held = Date.now() - pressStart;
    var kind = held >= HOLD_MS ? 'HOLD'
             : held >= LONG_MS ? 'LONG' : 'SHORT';
    holdBox.textContent = (held / 1000).toFixed(1) + 's \\u2014 ' + kind;
    holdBox.classList.toggle('armed', held >= LONG_MS);
  }

  function down(el, name, ev) {
    if (pressBtn) return;             // one button at a time, like a thumb
    ev.preventDefault();
    pressBtn = el;
    pressStart = Date.now();
    el.classList.add('down');
    tick();
    ticker = setInterval(tick, 100);
    post('api/press', name);
  }

  function up(name) {
    if (!pressBtn) return;
    clearInterval(ticker);
    pressBtn.classList.remove('down');
    pressBtn = null;
    pressStart = null;
    holdBox.textContent = '';
    holdBox.classList.remove('armed');
    post('api/release', name);
  }

  Array.prototype.forEach.call(
    document.querySelectorAll('.btn'),
    function (el) {
      var name = el.dataset.btn;
      el.addEventListener('pointerdown', function (ev) {
        down(el, name, ev);
      });
      ['pointerup', 'pointercancel', 'pointerleave'].forEach(function (type) {
        el.addEventListener(type, function () { up(name); });
      });
      // Keyboard access: space/enter behave like a short press.
      el.addEventListener('keydown', function (ev) {
        if ((ev.key === ' ' || ev.key === 'Enter') && !ev.repeat) {
          down(el, name, ev);
        }
      });
      el.addEventListener('keyup', function (ev) {
        if (ev.key === ' ' || ev.key === 'Enter') up(name);
      });
    }
  );

  // A press whose release never arrives (tab closed, Wi-Fi dropped) is
  // dropped server-side too; this keeps the UI in step.
  window.addEventListener('blur', function () {
    if (pressBtn) up(pressBtn.dataset.btn);
  });

  document.getElementById('logout').addEventListener('click', function () {
    fetch('api/logout', { method: 'POST' })
      .finally(function () { location.href = 'login'; });
  });

  poll();
})();
"""

_PAGE_HTML = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>pihole-display</title>
<style>%(base_css)s%(page_css)s</style>
</head>
<body>
%(banner)s
<div class="case">
  <div class="board">
    <div class="panel" id="panel">
      <img id="frame" width="%(w)d" height="%(h)d" alt="OLED display"
           src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==">
    </div>
    <div class="hold" id="hold"></div>
  </div>
  <div class="buttons">%(buttons)s</div>
</div>
<div class="foot">
  <span class="muted">pihole-display v%(version)s</span>
  <button type="button" id="logout">[*] Log out</button>
</div>
<script>%(page_js)s</script>
</body>
</html>
"""

_BANNER_HTML = """<div class="banner">
  <strong>[!!] Default password active.</strong>
  Anyone on this network can operate the device.
  <a href="change">Change it now</a>
</div>
"""

# ── Login and password pages ─────────────────────────────────

_FORM_CSS = """
/* The forms are styled as if they were another OLED screen: the same
   case around a black panel, monospace text in OLED blue, and the rule
   lines the display draws under its header and above its hint row. */
.card {
  width: 100%;
  max-width: 330px;
  background: linear-gradient(180deg, var(--case) 0%, #1b1f25 100%);
  border: 1px solid var(--case-edge);
  border-radius: 14px;
  padding: 18px;
  box-shadow: 0 10px 30px rgba(0,0,0,.55),
              inset 0 1px 0 rgba(255,255,255,.04);
}
.screen {
  background: var(--panel);
  border: 1px solid #000;
  border-radius: 6px;
  padding: 11px 13px 9px;
  box-shadow: inset 0 0 14px rgba(0,0,0,.9);
  font-family: ui-monospace, "DejaVu Sans Mono", Menlo, Consolas, monospace;
  color: var(--pixel);
}
h1 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: .02em;
  /* mirrors the rule the display draws under its header */
  border-bottom: 1px solid var(--pixel);
  padding-bottom: 4px;
}
.sub { margin: 6px 0 13px; font-size: 11px; opacity: .72; }
label {
  display: block;
  margin-bottom: 3px;
  font-size: 11px;
  opacity: .72;
  letter-spacing: .04em;
}
input {
  width: 100%;
  padding: 7px 8px;
  margin-bottom: 11px;
  background: #0b1016;
  border: 1px solid #1d3347;
  border-radius: 3px;
  color: var(--pixel);
  font-family: inherit;
  font-size: 14px;
}
input:focus {
  outline: none;
  border-color: var(--pixel);
  box-shadow: 0 0 0 1px var(--pixel);
}
button[type=submit] {
  width: 100%;
  padding: 8px;
  margin-top: 3px;
  background: var(--pixel);
  border: 0;
  border-radius: 3px;
  color: #04080d;
  font-family: inherit;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: .04em;
  cursor: pointer;
}
button[type=submit]:hover { filter: brightness(1.12); }
button[type=submit]:active { transform: translateY(1px); }
.err {
  border: 1px solid var(--err);
  border-radius: 3px;
  padding: 6px 8px;
  margin-bottom: 11px;
  font-size: 11px;
  line-height: 1.45;
  color: var(--err);
}
.note {
  margin: 11px 0 0;
  padding-top: 7px;
  /* like the rule above the display's hint row */
  border-top: 1px solid rgba(200,228,255,.4);
  font-size: 11px;
  line-height: 1.45;
  opacity: .72;
}
.note strong { opacity: 1; }
"""

_LOGIN_HTML = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Log in · pihole-display</title>
<style>%(base_css)s%(form_css)s</style>
</head>
<body>
<form class="card" method="post" action="api/login">
 <div class="screen">
  <h1>pihole-display</h1>
  <p class="sub">Login required</p>
  %(error)s
  <label for="u">User</label>
  <input id="u" name="user" autocomplete="username" value="%(user)s"
         autocapitalize="none" spellcheck="false" required>
  <label for="p">Password</label>
  <input id="p" name="password" type="password"
         autocomplete="%(pw_autocomplete)s" required autofocus>
  <button type="submit">[#] Log in</button>
  %(note)s
 </div>
</form>
</body>
</html>
"""

_LOGIN_NOTE = """<p class="note">
  First login: <strong>%(user)s</strong> / <strong>%(pw)s</strong>.
  It must be changed immediately afterwards.
</p>
"""

_CHANGE_HTML = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Change password · pihole-display</title>
<style>%(base_css)s%(form_css)s</style>
</head>
<body>
<form class="card" method="post" action="api/password">
 <div class="screen">
  <h1>Change password</h1>
  <p class="sub">%(sub)s</p>
  %(error)s
  <label for="p1">New password</label>
  <input id="p1" name="password" type="password"
         autocomplete="new-password" required autofocus>
  <label for="p2">Repeat</label>
  <input id="p2" name="repeat" type="password"
         autocomplete="new-password" required>
  <button type="submit">[#] Save</button>
  <p class="note">At least %(minlen)d characters.</p>
 </div>
</form>
</body>
</html>
"""


# ── Builders ─────────────────────────────────────────────────

def _escape(text: str) -> str:
    """Minimal HTML escaping for the few values echoed back into pages."""
    return (
        str(text)
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
    )


def _error_block(message: str) -> str:
    return f'<div class="err">{_escape(message)}</div>' if message else ''


def _buttons_html() -> str:
    parts = []
    for name, label, glyph in BUTTON_LAYOUT:
        parts.append(
            f'<button type="button" class="btn" data-btn="{name}" '
            f'aria-label="Button {label}">'
            f'<span class="cap">{glyph}</span>'
            f'<span class="label">{label}</span>'
            f'</button>'
        )
    return ''.join(parts)


def page(version: str, show_banner: bool, width: int, height: int) -> str:
    """Render the mirror page."""
    scale = max(1, config.WEB_SCALE)
    return _PAGE_HTML % {
        'base_css': _BASE_CSS,
        'page_css': _PAGE_CSS.replace('512px', f'{width * scale}px'),
        'page_js': _PAGE_JS % {
            'long_ms': config.LONG_PRESS_MS,
            'hold_ms': config.HOLD_MS,
        },
        'banner': _BANNER_HTML if show_banner else '',
        'buttons': _buttons_html(),
        'version': _escape(version),
        'w': width,
        'h': height,
    }


def login(user: str, error: str = '', show_default_hint: bool = False) -> str:
    """Render the login form."""
    note = ''
    if show_default_hint:
        from web_auth import DEFAULT_PASSWORD  # local: avoids a cycle
        note = _LOGIN_NOTE % {
            'user': _escape(user),
            'pw': _escape(DEFAULT_PASSWORD),
        }
    return _LOGIN_HTML % {
        'base_css': _BASE_CSS,
        'form_css': _FORM_CSS,
        'error': _error_block(error),
        'user': _escape(user),
        'note': note,
        # While the default password is still in place, stop the browser's
        # password manager from filling in something it saved earlier: it
        # looks like a wrong password and there is nothing to autofill yet.
        'pw_autocomplete': 'off' if show_default_hint else 'current-password',
    }


def change(error: str = '', forced: bool = False) -> str:
    """Render the password-change form."""
    from web_auth import MIN_PASSWORD_LEN  # local: avoids a cycle
    sub = (
        'The default password must be replaced.' if forced
        else 'New password for the web UI.'
    )
    return _CHANGE_HTML % {
        'base_css': _BASE_CSS,
        'form_css': _FORM_CSS,
        'error': _error_block(error),
        'sub': sub,
        'minlen': MIN_PASSWORD_LEN,
    }
