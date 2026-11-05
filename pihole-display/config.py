"""Configuration values for pihole-display hardware and runtime behavior."""

import os as _os
import runpy

# ============================================================
# config.py — Configuration for pihole-display
# BeagleBone Black + SSD1315 OLED + 4 buttons
# ============================================================

# --- I2C Display ---
I2C_PORT = 2      # /dev/i2c-2 (P9_19=SCL, P9_20=SDA)
I2C_ADDRESS = 0x3C   # SSD1306/SSD1315 default (0x3D if solder bridge is set)
DISPLAY_ROTATE = 2   # 0=0°, 1=90°, 2=180°, 3=270°

# --- GPIO buttons (all on gpiochip1, confirmed via /sys/kernel/debug/gpio) ---
# Button pressed = LOW (4.7K pull-up on board)
GPIO_CHIP = '/dev/gpiochip1'
# UP/DOWN swapped: the display is mounted rotated by 180 degrees
BTN_UP = 3   # P8_8  = K2 (^)
BTN_DOWN = 2   # P8_7  = K1 (v)
BTN_OK = 5   # P8_9  = K3 (#)
BTN_BACK = 4   # P8_10 = K4 (*)

# --- Pi-hole ---
PIHOLE_HOST = 'localhost'
PIHOLE_SETUPVARS = '/etc/pihole/setupVars.conf'
# Pi-hole v6 password. Leave empty to log in with Pi-hole's local CLI
# password file (needs root, which the service runs as).
PIHOLE_PASSWORD = ''
PIHOLE_CLI_PW = '/etc/pihole/cli_pw'
# Pi-hole writes the installed component versions here; read directly so
# an update can be verified while FTL is restarting and the API is down.
PIHOLE_VERSIONS = '/etc/pihole/versions'

# --- Timing ---
REFRESH_INTERVAL = 10    # Seconds between data refreshes
UPDATE_CHECK_INTERVAL = 3600  # Seconds between Pi-hole update checks
DISPLAY_TIMEOUT = 60    # Seconds until display sleeps (0 = never)
DEBOUNCE_MS = 200   # Debounce time in milliseconds
LONG_PRESS_MS = 1500  # Long press threshold in milliseconds
HOLD_MS = 5000  # Hold * this long to wake a locked display (milliseconds)

# --- Persistent UI state (screen lock setting) ---
STATE_FILE = '/var/lib/pihole-display/state.json'

# --- Pause options (seconds) ---
PAUSE_OPTIONS = [
    ('5 Min',   5 * 60),
    ('15 Min', 15 * 60),
    ('30 Min', 30 * 60),
    ('1 Hour', 60 * 60),
]

# --- Webserver (OLED mirror + clickable buttons) ---
WEB_ENABLED = True          # False disables the web UI entirely
WEB_HOST = '0.0.0.0'        # '127.0.0.1' = local only (SSH tunnel)
WEB_PORT = 8080             # Pi-hole admin already uses :80
WEB_USER = 'admin'          # Login name
WEB_AUTH_FILE = '/var/lib/pihole-display/web_auth.json'
WEB_SESSION_HOURS = 168     # Session lifetime (7 days)
WEB_MAX_ATTEMPTS = 5        # Failed logins before lockout
WEB_LOCKOUT_SEC = 60        # Lockout duration per IP
WEB_SCALE = 4               # Display zoom in the browser (128x64 -> 512x256)

# --- Site overrides -------------------------------------------------
# This file only carries the defaults and is replaced on every update. Site
# settings belong in /etc/pihole-display/config.py, which is loaded on top of
# this module: assign any name defined above to override it, and leave the
# rest out to keep its default.
_OVERRIDE_PATH = _os.environ.get(
    'PIHOLE_DISPLAY_CONFIG', '/etc/pihole-display/config.py')

if (_os.path.isfile(_OVERRIDE_PATH)
        and _os.path.realpath(_OVERRIDE_PATH)
        != _os.path.realpath(__file__)):
    # Run in its own namespace: the file is not imported as a module, and a
    # copy of this file used as the override skips its own loader instead of
    # running it again.
    _site_values = runpy.run_path(_OVERRIDE_PATH)
    globals().update(
        {name: value for name, value in _site_values.items()
         if not name.startswith('__')})
