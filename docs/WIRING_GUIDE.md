# Verkabelungsanleitung: pihole-display mit DIY Lochraster-Adapterplatine

Diese Anleitung erklärt die korrekte Verkabelung des OLED-Displays und der 4 Buttons auf einer selbstgebauten Lochrasterplatine, die zwischen den BeagleBone Black (BBB) Headern P8 und P9 steckt.

## DIY Lochraster-Adapterplatine

### Materialliste

| Bauteil | Menge | Preis ca. |
| --- | --- | --- |
| Lochrasterplatine 2.54mm | 1× (min. 12×6 Löcher) | ~0.50€ |
| 1×8 Stiftleiste (männlich) | 1× | ~0.20€ |
| Einzelne Female Dupont Crimp-Pins + Kabel | 8× je ~10cm | ~1€ |
| Lötdraht (Ø 0.5mm) | 1 Rolle | ~2€ |
| **Gesamt** | **~4€** | |

```text
BeagleBone Black
├── P8 Header (links)  ──┐
│                        ├──[Lochrasterplatine]──┐
└── P9 Header (rechts) ──┘                        │
                                                  ├── OLED Display (SSD1315)
                                                  ├── Button K1 (nach oben)
                                                  ├── Button K2 (nach unten)
                                                  ├── Button K3 (Select/Enter)
                                                  └── Button K4 (Home/Cancel)
```

## Material

- BeagleBone Black mit Debian 13 Trixie
- 0.96" OLED Display SSD1315 (128×64 Pixel, I2C)
- 4× Tactile Push Buttons (z. B. 6mm × 6mm)
- Lochrasterplatine (2.54mm Raster, min. 12×6 Löcher)
- 1×8 Stiftleiste (männlich) für Display-Anschluss

## BeagleBone Black Header — Pinouts

<!-- markdownlint-disable MD033 -->
<table>
<tr><th align="center">P9</th><th>Board</th><th align="center">P8</th></tr>
<tr><td align="center">GND (Pin 1) ◼◼ (Pin 2) GND</td><td rowspan="23" align="center"><img src="https://raw.githubusercontent.com/beagleboard/beaglebone-black/master/images/image68.jpg" alt="BeagleBone Black Expansion Header Position"><br><em>Expansion Connector Location — BeagleBoard.org (CC-BY-SA-4.0)</em></td><td align="center">GND (Pin 1) ◼◼ (Pin 2) GND</td></tr>
<tr><td align="center">DC_3.3V (Pin 3) ◼◼ (Pin 4) DC_3.3V</td><td align="center">GPIO1_6 (Pin 3) ◼◼ (Pin 4) GPIO1_7</td></tr>
<tr><td align="center">VDD_5V (Pin 5) ◼◼ (Pin 6) VDD_5V</td><td align="center">GPIO1_2 (Pin 5) ◼◼ (Pin 6) GPIO1_3</td></tr>
<tr><td align="center">SYS_5V (Pin 7) ◼◼ (Pin 8) SYS_5V</td><td align="center">TIMER4/gpio2[2] (Pin 7) ◼◼ (Pin 8) TIMER7/gpio2[3]</td></tr>
<tr><td align="center">PWR_BUT (Pin 9) ◼◼ (Pin 10) SYS_RESETn</td><td align="center">TIMER5/gpio2[5] (Pin 9) ◼◼ (Pin 10) TIMER6/gpio2[4]</td></tr>
<tr><td align="center">UART4_RXD (Pin 11) ◼◼ (Pin 12) GPIO1_28</td><td align="center">GPIO1_13 (Pin 11) ◼◼ (Pin 12) GPIO1_12</td></tr>
<tr><td align="center">UART4_TXD (Pin 13) ◼◼ (Pin 14) EHRPWM1A</td><td align="center">EHRPWM2B (Pin 13) ◼◼ (Pin 14) GPIO0_26</td></tr>
<tr><td align="center">GPIO1_16 (Pin 15) ◼◼ (Pin 16) EHRPWM1B</td><td align="center">GPIO1_15 (Pin 15) ◼◼ (Pin 16) GPIO1_14</td></tr>
<tr><td align="center">I2C1_SCL (Pin 17) ◼◼ (Pin 18) I2C1_SDA</td><td align="center">GPIO0_27 (Pin 17) ◼◼ (Pin 18) GPIO2_1</td></tr>
<tr><td align="center">I2C2_SCL (Pin 19) ◼◼ (Pin 20) I2C2_SDA</td><td align="center">EHRPWM2A (Pin 19) ◼◼ (Pin 20) GPIO1_31</td></tr>
<tr><td align="center">UART2_TXD (Pin 21) ◼◼ (Pin 22) UART2_RXD</td><td align="center">GPIO1_30 (Pin 21) ◼◼ (Pin 22) GPIO1_5</td></tr>
<tr><td align="center">GPIO1_17 (Pin 23) ◼◼ (Pin 24) UART1_TXD</td><td align="center">GPIO1_4 (Pin 23) ◼◼ (Pin 24) GPIO1_1</td></tr>
<tr><td align="center">GPIO3_21 (Pin 25) ◼◼ (Pin 26) UART1_RXD</td><td align="center">GPIO1_0 (Pin 25) ◼◼ (Pin 26) GPIO1_29</td></tr>
<tr><td align="center">GPIO3_19 (Pin 27) ◼◼ (Pin 28) SPI1_CS0</td><td align="center">GPIO2_22 (Pin 27) ◼◼ (Pin 28) GPIO2_24</td></tr>
<tr><td align="center">SPI1_D0 (Pin 29) ◼◼ (Pin 30) SPI1_D1</td><td align="center">GPIO2_23 (Pin 29) ◼◼ (Pin 30) GPIO2_25</td></tr>
<tr><td align="center">SPI1_SCLK (Pin 31) ◼◼ (Pin 32) VADC</td><td align="center">UART5_CTSN (Pin 31) ◼◼ (Pin 32) UART5_RTSN</td></tr>
<tr><td align="center">AIN4 (Pin 33) ◼◼ (Pin 34) AGND</td><td align="center">UART4_RTSN (Pin 33) ◼◼ (Pin 34) UART3_RTSN</td></tr>
<tr><td align="center">AIN6 (Pin 35) ◼◼ (Pin 36) AIN5</td><td align="center">UART4_CTSN (Pin 35) ◼◼ (Pin 36) UART3_CTSN</td></tr>
<tr><td align="center">AIN2 (Pin 37) ◼◼ (Pin 38) AIN3</td><td align="center">UART5_TXD (Pin 37) ◼◼ (Pin 38) UART5_RXD</td></tr>
<tr><td align="center">AIN0 (Pin 39) ◼◼ (Pin 40) AIN1</td><td align="center">GPIO2_12 (Pin 39) ◼◼ (Pin 40) GPIO2_13</td></tr>
<tr><td align="center">CLKOUT2 (Pin 41) ◼◼ (Pin 42) GPIO0_7</td><td align="center">GPIO2_10 (Pin 41) ◼◼ (Pin 42) GPIO2_11</td></tr>
<tr><td align="center">GND (Pin 43) ◼◼ (Pin 44) GND</td><td align="center">GPIO2_8 (Pin 43) ◼◼ (Pin 44) GPIO2_9</td></tr>
<tr><td align="center">GND (Pin 45) ◼◼ (Pin 46) GND</td><td align="center">GPIO2_6 (Pin 45) ◼◼ (Pin 46) GPIO2_7</td></tr>
</table>
<!-- markdownlint-enable MD033 -->

## Detailliertes Verkabelungs-Schaltschema

```text
P9 Header (links)           Lochrasterplatine                P8 Header (rechts)
┌──────────────┐            ┌──────────────────────┐        ┌──────────────┐
│ Pin 1 (GND)  ├────────────┤ GND Sammelschiene    ├────────┤ Pin 1 (GND)  │
│ Pin 2 (GND)  ├────────────┤        ↓             ├────────┤ Pin 2 (GND)  │
│ Pin 3 (3.3V) ├────────────┤        |             │        │              │
│ Pin 19(SCL)  ├────────────┤        |             │        │              │
│ Pin 20(SDA)  ├────────────┤        |             │        │              │
│              │            │        |             │        │              │
└──────────────┘            │        |             │        │              │
                            │ 3.3V Sammelschiene   ├────────┤              │
                            │        ↑             │        │              │
                            │   Pull-up Res.       │        │              │
                            │              │       │        │              │
                            │  Display     │       │        │              │
                            │  (I2C SSD1315)       │        │              │
                            │  VCC ────────|       │        │              │
                            │  GND ────────|       │        │              │
                            │  K1  ────────────────┤────────┤ Pin 7 (GPIO) │
                            │  K2  ────────────────┤────────┤ Pin 8 (GPIO) │
                            │  K3  ────────────────┤────────┤ Pin 9 (GPIO) │
                            │  K4  ────────────────┤────────┤ Pin 10(GPIO) │
                            └──────────────────────┘        └──────────────┘
```

## Verifikation nach Verbindung

Nach der Verkabelung folgende Schritte durchführen:

```bash
# 1. SSH auf BBB
ssh root@beaglebone

# 2. I2C-Display prüfen (sollte 0x3C oder 0x3D zeigen)
i2cdetect -y -r 2

# 3. GPIO-Pins prüfen (sollte GPIO2_2 bis GPIO2_5 anzeigen)
ls /sys/class/gpio/

# 4. Buttons testen (vor Installation)
cd /tmp/pihole-display
python3 button_handler.py

# 5. Display testen
python3 display_manager.py
```

## Fehlerbehebung

- **I2C-Display wird nicht erkannt**
  - Ursache: SCL/SDA vertauscht oder nicht verbunden
  - Lösung: Pinbelegung überprüfen, Durchgang messen
- **Buttons reagieren nicht**
  - Ursache: GPIO-Pin nicht verbunden oder falscher Pin
  - Lösung: Verkabelung gegen Diagramm überprüfen
- **Display flackert**
  - Ursache: Unzureichende Stromversorgung
  - Lösung: 3.3V Leitung überprüfen, dickere Drähte verwenden
- **Lötbrücke suspekt**
  - Ursache: Kalte Lötstelle
  - Lösung: Mit Lötkolben nacharbeiten

## Referenzen

- BeagleBone Black P8/P9 Header: [BeagleBone Black System Reference Manual](https://www.beagleboard.org/support/bone101/)
- SSD1315 OLED Driver: [SSD1315 Datasheet](https://cdn-shop.adafruit.com/datasheets/SSD1315.pdf)
