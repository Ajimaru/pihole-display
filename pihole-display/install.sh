#!/bin/bash
# ============================================================
# install.sh — Installation pihole-display auf BeagleBone Black
# Debian 13 (Trixie)
# ============================================================
set -e

INSTALL_DIR="/opt/pihole-display"
SERVICE="pihole-display"

echo "=== pihole-display Installation ==="
echo ""

# Root-Check
if [ "$EUID" -ne 0 ]; then
    echo "Bitte als root ausführen: sudo ./install.sh"
    exit 1
fi

# Abhängigkeiten (System)
echo "[1/5] System-Pakete installieren..."
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

# I2C aktivieren
echo "[2/5] I2C aktivieren..."
if ! grep -q "^dtparam=i2c_arm=on" /boot/uEnv.txt 2>/dev/null; then
    # BeagleBone nutzt uEnv.txt oder cape-overlays
    echo "Hinweis: Bitte sicherstellen dass I2C2 im Device Tree aktiviert ist."
    echo "  Prüfe mit: ls /dev/i2c*"
fi

# Verzeichnis anlegen
echo "[3/5] Installationsverzeichnis erstellen: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cp -r ./* "$INSTALL_DIR/"

# Python Virtual Environment
echo "[4/5] Python venv und Pakete installieren..."
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip -q
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q

# Systemd-Service
echo "[5/5] Systemd-Service installieren..."
cp "$INSTALL_DIR/pihole-display.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable "$SERVICE"

echo ""
echo "=== Installation abgeschlossen ==="
echo ""
echo "Nächste Schritte:"
echo ""
echo "1. I2C prüfen (Display angeschlossen?):"
echo "   i2cdetect -y -r 2"
echo "   → Adresse 0x3C oder 0x3D sollte erscheinen"
echo ""
echo "2. (Optional) Pi-hole v6 Passwort in config.py eintragen:"
echo "   nano $INSTALL_DIR/config.py"
echo "   → PIHOLE_PASSWORD = 'dein-passwort'"
echo ""
echo "3. Service starten:"
echo "   systemctl start $SERVICE"
echo ""
echo "4. Logs anzeigen:"
echo "   journalctl -u $SERVICE -f"
echo ""
