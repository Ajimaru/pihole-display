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
echo "[1/6] Installing system packages..."
apt-get update -qq
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-libgpiod \
    gpiod \
    i2c-tools \
    libi2c-dev \
    fonts-dejavu-core \
    --no-install-recommends

# Enable I2C
echo "[2/6] Enabling I2C..."
if ! grep -q "^dtparam=i2c_arm=on" /boot/uEnv.txt 2>/dev/null; then
    # BeagleBone uses uEnv.txt or cape overlays
    echo "Note: Make sure I2C2 is enabled in the device tree."
    echo "  Check with: ls /dev/i2c*"
fi

# Create installation directory
echo "[3/6] Creating installation directory: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cp -r ./* "$INSTALL_DIR/"

# Python Virtual Environment
echo "[4/6] Installing Python venv and packages..."
# --system-site-packages: needed so the venv can see the apt-installed
# python3-libgpiod module (not available via pip on all platforms)
python3 -m venv --system-site-packages "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip -q
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q

# Systemd service
echo "[5/6] Installing systemd service..."
cp "$INSTALL_DIR/pihole-display.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable "$SERVICE"

# Optional: unbound-control for the Unbound screen
echo "[6/6] Checking unbound-control..."
UNBOUND_CONF_DIR="/etc/unbound/unbound.conf.d"
UNBOUND_RC_CONF="$UNBOUND_CONF_DIR/remote-control.conf"
UNBOUND_CONTROL_OK=0

if ! command -v unbound-control >/dev/null 2>&1; then
    echo "Unbound is not installed - skipping."
elif unbound-control status >/dev/null 2>&1; then
    echo "unbound-control already works - nothing to do."
    UNBOUND_CONTROL_OK=1
elif [ -e "$UNBOUND_RC_CONF" ]; then
    echo "$UNBOUND_RC_CONF exists but unbound-control does not answer."
    echo "Leaving it untouched - please check it manually."
elif [ ! -t 0 ]; then
    echo "Not running interactively - skipping (see next steps below)."
else
    echo ""
    echo "The Unbound screen needs unbound-control, which Debian ships disabled."
    echo "This step creates $UNBOUND_RC_CONF"
    echo "(local socket /run/unbound.ctl, no certificates) and restarts Unbound."
    echo ""
    echo "RISK: While Unbound restarts, Pi-hole cannot resolve new DNS queries,"
    echo "so every device using this Pi-hole loses name resolution for a few"
    echo "seconds. The config is validated first and the change is reverted if"
    echo "the check or the restart fails, but run this at a quiet moment."
    echo ""
    read -r -p "Enable unbound-control and restart Unbound now? [y/N] " answer
    if [[ "$answer" =~ ^[Yy]$ ]]; then
        if [ -f "$UNBOUND_RC_CONF.dpkg-dist" ]; then
            cp "$UNBOUND_RC_CONF.dpkg-dist" "$UNBOUND_RC_CONF"
        else
            printf 'remote-control:\n  control-enable: yes\n  control-interface: /run/unbound.ctl\n' \
                > "$UNBOUND_RC_CONF"
        fi
        if ! unbound-checkconf >/dev/null; then
            echo "unbound-checkconf failed - reverting, Unbound was not restarted."
            rm -f "$UNBOUND_RC_CONF"
        elif ! systemctl restart unbound; then
            echo "Unbound failed to restart - reverting and restarting again."
            rm -f "$UNBOUND_RC_CONF"
            systemctl restart unbound || echo "WARNING: Unbound is not running!"
        else
            echo "unbound-control enabled."
            UNBOUND_CONTROL_OK=1
        fi
    else
        echo "Skipped (see next steps below)."
    fi
fi

echo ""
echo "=== Installation complete ==="
echo ""
echo "Next steps:"
echo ""
echo "- Check I2C (is the display connected?):"
echo "   sudo i2cdetect -y -r 2"
echo "   -> Address 3c or 3d should appear"
echo ""
if [ "$UNBOUND_CONTROL_OK" -eq 0 ]; then
    echo "- Enable unbound-control (needed for the Unbound screen,"
    echo "  restarting Unbound briefly interrupts DNS for the network):"
    echo "   sudo cp /etc/unbound/unbound.conf.d/remote-control.conf.dpkg-dist \\"
    echo "        /etc/unbound/unbound.conf.d/remote-control.conf"
    echo "   sudo unbound-checkconf && sudo systemctl restart unbound"
    echo ""
fi
echo "- Start service:"
echo "   sudo systemctl start $SERVICE"
echo ""
echo "- Show logs:"
echo "   sudo journalctl -u $SERVICE -f"
echo ""
echo "Note: Pi-hole v6 login needs no setup. With PIHOLE_PASSWORD empty in"
echo "$INSTALL_DIR/config.py, /etc/pihole/cli_pw is used."
echo ""
