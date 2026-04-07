"""Configuration values for pihole-display hardware and runtime behavior."""

# ============================================================
# config.py — Configuration for pihole-display
# BeagleBone Black + SSD1315 OLED + 4 buttons
# ============================================================

# --- I2C Display ---
I2C_PORT = 2      # /dev/i2c-2 (P9_19=SCL, P9_20=SDA)
I2C_ADDRESS = 0x3C   # SSD1306/SSD1315 default (0x3D if solder bridge is set)

# --- GPIO buttons (all on gpiochip2) ---
# Button pressed = LOW (4.7K pull-up on board)
GPIO_CHIP = '/dev/gpiochip2'
BTN_UP = 2   # P8_7  = GPIO2_2 = K1 (^)
BTN_DOWN = 3   # P8_8  = GPIO2_3 = K2 (v)
BTN_OK = 5   # P8_9  = GPIO2_5 = K3 (#)
BTN_BACK = 4   # P8_10 = GPIO2_4 = K4 (*)

# --- Pi-hole ---
PIHOLE_HOST = 'localhost'
PIHOLE_SETUPVARS = '/etc/pihole/setupVars.conf'
# Pi-hole v6 password (leave empty if not set)
PIHOLE_PASSWORD = ''

# --- Timing ---
REFRESH_INTERVAL = 10    # Seconds between data refreshes
DISPLAY_TIMEOUT = 60    # Seconds until display sleeps (0 = never)
DEBOUNCE_MS = 200   # Debounce time in milliseconds
LONG_PRESS_MS = 1500  # Long press threshold in milliseconds

# --- Pause options (seconds) ---
PAUSE_OPTIONS = [
    ('5 Min',   5 * 60),
    ('15 Min', 15 * 60),
    ('30 Min', 30 * 60),
    ('1 Hour', 60 * 60),
]
