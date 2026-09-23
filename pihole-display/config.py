"""Configuration values for pihole-display hardware and runtime behavior."""

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

# --- Timing ---
REFRESH_INTERVAL = 10    # Seconds between data refreshes
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
