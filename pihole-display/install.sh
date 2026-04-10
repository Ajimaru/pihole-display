#!/bin/bash
# ============================================================
# install.sh — Install pihole-display on BeagleBone Black
# Debian 13 (Trixie)
# ============================================================
set -e

INSTALL_DIR="/opt/pihole-display"
SERVICE="pihole-display"

echo "=== pihole-display Installation ==="
echo ""

# Root check
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root: sudo ./install.sh"
    exit 1
fi

# Dependencies (system)
echo "[1/5] Installing system packages..."
apt-get update -qq
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-gpiod \
    gpiod \
    i2c-tools \
    libi2c-dev \
    fonts-dejavu-core \
    --no-install-recommends

# Enable I2C
echo "[2/5] Enabling I2C..."
if ! grep -q "^dtparam=i2c_arm=on" /boot/uEnv.txt 2>/dev/null; then
    # BeagleBone uses uEnv.txt or cape overlays
    echo "Note: Make sure I2C2 is enabled in the device tree."
    echo "  Check with: ls /dev/i2c*"
fi

# Create installation directory
echo "[3/5] Creating installation directory: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cp -r ./* "$INSTALL_DIR/"

# Python Virtual Environment
echo "[4/5] Installing Python venv and packages..."
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip -q
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q

# Systemd service
echo "[5/5] Installing systemd service..."
cp "$INSTALL_DIR/pihole-display.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable "$SERVICE"

echo ""
echo "=== Installation complete ==="
echo ""
echo "Next steps:"
echo ""
echo "1. Check I2C (is the display connected?):"
echo "   i2cdetect -y -r 2"
echo "   -> Address 0x3C or 0x3D should appear"
echo ""
echo "2. (Optional) Set Pi-hole v6 password in config.py:"
echo "   nano $INSTALL_DIR/config.py"
echo "   -> PIHOLE_PASSWORD = 'your-password'"
echo ""
echo "3. Start service:"
echo "   systemctl start $SERVICE"
echo ""
echo "4. Show logs:"
echo "   journalctl -u $SERVICE -f"
echo ""
