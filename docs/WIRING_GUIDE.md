# Wiring Guide: pihole-display with a DIY Perfboard Adapter

This guide explains how to correctly wire the OLED display and the 4 buttons on a homemade perfboard adapter that sits between the BeagleBone Black (BBB) P8 and P9 headers.

## DIY Perfboard Adapter

### Bill of Materials

| Part | Qty |
| --- | --- |
| 2.54mm perfboard | 1x (min. 10x21 holes) |
| 1x16 pin header (male) | 1x |
| wire | 8x, about 7cm each |
| OLED display (SSD1315) with four buttons | 1x |
| **Total** | **4 items** |

```text
BeagleBone Black
├── P8 header (left)   ──┐
│                        ├──[Perfboard adapter]──┐
└── P9 header (right)  ──┘                       │
                                                 ├── OLED display (SSD1315)
                                                 ├── Button K1 (up)
                                                 ├── Button K2 (down)
                                                 ├── Button K3 (select/enter)
                                                 └── Button K4 (home/cancel)
```

## Materials

- BeagleBone Black with Debian 13 Trixie
- Perfboard with OLED display (SSD1315) and four buttons mounted

## BeagleBone Black Headers - Pinouts

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

## Detailed Wiring Schematic

```text
P9 header (left)            Perfboard adapter                 P8 header (right)
┌──────────────┐            ┌──────────────────────┐         ┌──────────────┐
│ Pin 2 (GND)  ├────────────┤ GND bus rail         │         │              │
│ Pin 4 (3.3V) ├────────────┤        ↓             │         │              │
│ Pin 19(SCL)  ├────────────┤        |             │         │              │
│ Pin 20(SDA)  ├────────────┤        |             │         │              │
│              ├────────────┤        |             │         │              │
│              │            │        |             │         │              │
└──────────────┘            │        |             │         │              │
                            │ 3.3V bus rail        │         │              │
                            │        ↑             │         │              │
                            │              │       │         │              │
                            │              │       │         │              │
                            │  Display     │       │         │              │
                            │  (I2C SSD1315)       │         │              │
                            │  VCC ────────|       │         │              │
                            │  GND ────────|       │         │              │
                            │  K1  ────────────────┤─────────┤ Pin 7 (GPIO) │
                            │  K2  ────────────────┤─────────┤ Pin 8 (GPIO) │
                            │  K3  ────────────────┤─────────┤ Pin 9 (GPIO) │
                            │  K4  ────────────────┤─────────┤ Pin 10(GPIO) │
                            └──────────────────────┘         └──────────────┘
```

## Verification After Wiring

After wiring is complete, run the following checks:

```bash
# 1. SSH to BBB (root login is disabled on the BeagleBoard images)
ssh <user>@<BBB_IP_ADDRESS>

# 2. Install the test tools (install.sh installs them too)
sudo apt install i2c-tools gpiod

# 3. Check I2C display (should show 3c, or 3d if the address bridge is set)
sudo i2cdetect -y -r 2

# 4. Check GPIO pins (P8_7/P8_8/P8_10/P8_9 = gpiochip1 lines 2/3/4/5)
sudo cat /sys/kernel/debug/gpio | grep -A6 'gpiochip1:'

# 5. Test buttons: prints an event per press and release, Ctrl+C to stop.
#    If pihole-display is already running it holds the lines, so stop it
#    first: sudo systemctl stop pihole-display
sudo gpiomon -c gpiochip1 2 3 4 5

# 6. Test display: after install.sh the log should contain
#    "OLED initialized on I2C2 @ 0x3C"
sudo journalctl -u pihole-display -n 20
```

## Troubleshooting

- **I2C display is not detected**
  - Cause: SCL/SDA swapped or not connected
  - Fix: Verify pin mapping and continuity
- **Buttons do not respond**
  - Cause: GPIO pin not connected or wrong pin used
  - Fix: Verify wiring against the diagram
  - Cause: Wrong `/dev/gpiochipN` in `config.py` (TRM silicon names like
    `gpio2[2]` do not match the Linux `gpiochip` numbering)
  - Fix: Confirm the real mapping with `sudo cat /sys/kernel/debug/gpio`
    and match the `P8_x` labels shown there to `GPIO_CHIP`/`BTN_*` in
    `config.py`
- **Display flickers**
  - Cause: Insufficient power supply stability
  - Fix: Verify 3.3V line, use thicker wires
- **Suspicious solder joint**
  - Cause: Cold solder joint
  - Fix: Rework with soldering iron

## KiCad PCB files

A KiCad PCB with all footprints and the ratsnest pre-wired is available in
[`kicad/`](kicad/):

```text
docs/kicad/
├── pihole_display_cape.kicad_pcb  — PCB layout (last saved with KiCad 10)
├── pihole_display_cape.kicad_pro  — KiCad project file
└── generate_kicad.py              — Python generator (KiCad 7 format)
```

> **Note:** Re-running `generate_kicad.py` overwrites
> `pihole_display_cape.kicad_pcb`, so any changes made in the PCB Editor are
> lost.

Board dimensions: **55 × 28 mm**, covers P8/P9 pins 1–20.

Suggested routing strategy inside KiCad:

- **F.Cu** (top): K1–K4 button signals from P8 side
- **B.Cu** (bottom): GND, +3.3V, SCL, SDA from P9 side

## Display header pin assignment

| Pin | Signal | Net       |
|-----|--------|-----------|
| 1   | GND    | /GND      |
| 2   | VCC    | /+3.3V    |
| 3   | SCL    | /SCL      |
| 4   | SDA    | /SDA      |
| 5   | K4 (*) | /BTN_K4   |
| 6   | K3 (#) | /BTN_K3   |
| 7   | K2 (v) | /BTN_K2   |
| 8   | K1 (^) | /BTN_K1   |

The `^`/`v` labels are the ones printed on the display module. Because the
display is mounted rotated by 180°, the software uses K2 as up and K1 as down
(`BTN_UP`/`BTN_DOWN` in `config.py`).

> **Note on GPIO numbering:** The P8/P9 header table above uses the AM335x TRM
> silicon names (e.g. `gpio2[2]` for P8_7). This does **not** match the Linux
> `/dev/gpiochipN` enumeration used in software! Verified via
> `sudo cat /sys/kernel/debug/gpio` on Debian 13 Trixie, P8_7/P8_8/P8_9/P8_10
> are exposed as `gpiochip1` lines 2/3/5/4 (not `gpiochip2` as the TRM name
> would suggest). `config.py`'s `GPIO_CHIP`/`BTN_*` constants reflect this
> confirmed Linux-side mapping.

## References

- BeagleBone Black P8/P9 headers: [BeagleBone Black documentation – Connectors](https://docs.beagleboard.org/boards/beaglebone/black/ch07.html)
- SSD1315 OLED driver: [SSD1315 Datasheet](https://files.waveshare.com/upload/f/f0/SSD1315_1.1.pdf)
