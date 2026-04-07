"""Configuration values for pihole-display hardware and runtime behavior."""

# ============================================================
# config.py — Konfiguration für pihole-display
# BeagleBone Black + SSD1315 OLED + 4 Tasten
# ============================================================

# --- I2C Display ---
I2C_PORT = 2      # /dev/i2c-2 (P9_19=SCL, P9_20=SDA)
I2C_ADDRESS = 0x3C   # SSD1306/SSD1315 Standard (0x3D falls Lötbrücke)

# --- GPIO Buttons (alle auf gpiochip2) ---
# Taste gedrückt = LOW (4.7K Pull-up auf Platine)
GPIO_CHIP = '/dev/gpiochip2'
BTN_UP = 2   # P8_7  = GPIO2_2 = K1 (^)
BTN_DOWN = 3   # P8_8  = GPIO2_3 = K2 (v)
BTN_OK = 5   # P8_9  = GPIO2_5 = K3 (#)
BTN_BACK = 4   # P8_10 = GPIO2_4 = K4 (*)

# --- Pi-hole ---
PIHOLE_HOST = 'localhost'
PIHOLE_SETUPVARS = '/etc/pihole/setupVars.conf'
# Pi-hole v6 Passwort (leer lassen wenn nicht gesetzt)
PIHOLE_PASSWORD = ''

# --- Timing ---
REFRESH_INTERVAL = 10    # Sekunden zwischen Daten-Aktualisierung
DISPLAY_TIMEOUT = 60    # Sekunden bis Display schläft (0 = nie)
DEBOUNCE_MS = 200   # Entprell-Zeit in Millisekunden
LONG_PRESS_MS = 1500  # Langer Druck in Millisekunden

# --- Pause-Optionen (Sekunden) ---
PAUSE_OPTIONS = [
    ('5 Min',   5 * 60),
    ('15 Min', 15 * 60),
    ('30 Min', 30 * 60),
    ('1 Std',  60 * 60),
]
