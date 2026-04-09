#!/usr/bin/env python3
"""Generate a KiCad 7 .kicad_pcb file for the pihole-display BeagleBone cape.

Board: 55 × 28 mm, 1.6 mm FR4, covers BBB P8/P9 pins 1–20.
Outputs footprints + ratsnest only — route interactively in KiCad.

Suggested routing:
  F.Cu  ← K1–K4 signals (short traces from P8 side)
  B.Cu  ← GND, +3.3V, SCL, SDA (from P9 side)
"""

import os
import uuid

# ── Board constants ───────────────────────────────────────────

BOARD_W = 55.0  # mm
BOARD_H = 28.0  # mm
PITCH = 2.54  # mm

# P8 column X positions (left header)
P8_ODD = 2.54  # odd pins  (1, 3, 5 …)
P8_EVEN = 5.08  # even pins (2, 4, 6 …)

# P9 column X positions (right header)
P9_ODD = 49.53  # odd pins  (1, 3, 5 …)
P9_EVEN = 52.07  # even pins (2, 4, 6 …)

# Row Y positions: row r (1-indexed) → y = r * PITCH
# Row 1 (pins 1,2) at y=2.54 … row 10 (pins 19,20) at y=25.40

# Display 1×8 header: placed at pin-3/4 row level (y = 2*PITCH = 5.08)
DISP_Y = 2 * PITCH  # 5.08 mm
DISP_X1 = 18.415             # x of pin 1 (GND)

# ── Net table ─────────────────────────────────────────────────

NETS = [
    (0, '""'),
    (1, '"/GND"'),
    (2, '"/+3.3V"'),
    (3, '"/SCL"'),
    (4, '"/SDA"'),
    (5, '"/BTN_K4"'),
    (6, '"/BTN_K3"'),
    (7, '"/BTN_K2"'),
    (8, '"/BTN_K1"'),
]

_NET_IDS = {name.strip('"'): nid for nid, name in NETS}


def _net_clause(name: str) -> str:
    """Return (net N "name") clause, or empty string for unconnected."""
    if not name:
        return ''
    nid = _NET_IDS.get(name, 0)
    return f'\n      (net {nid} "{name}")'


# ── Helpers ───────────────────────────────────────────────────

def _uid() -> str:
    return str(uuid.uuid4())


def _row_y(row: int) -> float:
    """Absolute Y of header row (1-indexed)."""
    return row * PITCH


# ── Pad builders ──────────────────────────────────────────────

def _pad(num: str, abs_x: float, abs_y: float,
         fp_x: float, fp_y: float, net: str = '') -> str:
    """Through-hole pad, coordinates relative to footprint origin."""
    rx = abs_x - fp_x
    ry = abs_y - fp_y
    shape = 'rect' if num == '1' else 'circle'
    return (
        f'    (pad "{num}" thru_hole {shape}\n'
        f'      (at {rx:.4f} {ry:.4f})\n'
        f'      (size 1.8 1.8)\n'
        f'      (drill 1.0)\n'
        f'      (layers "*.Cu" "*.Mask"){_net_clause(net)}\n'
        f'      (uuid "{_uid()}")\n'
        f'    )'
    )


# ── P8 pad definitions ────────────────────────────────────────

# Net assignments for P8 pins (unconnected pins omitted)
_P8_NET: dict[int, str] = {
    7:  '/BTN_K1',   # GPIO2_2  K1 = ^ (up)
    8:  '/BTN_K2',   # GPIO2_3  K2 = v (down)
    9:  '/BTN_K3',   # GPIO2_5  K3 = # (ok)
    10: '/BTN_K4',   # GPIO2_4  K4 = * (back)
}

# Footprint centre for J2
_P8_CX = (P8_ODD + P8_EVEN) / 2     # 3.81
_P8_CY = (_row_y(1) + _row_y(10)) / 2  # 13.97


def _p8_pads() -> str:
    lines = []
    for row in range(1, 11):
        y = _row_y(row)
        pin_odd = 2 * row - 1
        pin_even = 2 * row
        lines.append(_pad(str(pin_odd),  P8_ODD,  y, _P8_CX, _P8_CY,
                          _P8_NET.get(pin_odd, '')))
        lines.append(_pad(str(pin_even), P8_EVEN, y, _P8_CX, _P8_CY,
                          _P8_NET.get(pin_even, '')))
    return '\n'.join(lines)


# ── P9 pad definitions ────────────────────────────────────────

_P9_NET: dict[int, str] = {
    1:  '/GND',
    2:  '/GND',
    3:  '/+3.3V',
    4:  '/+3.3V',
    19: '/SCL',
    20: '/SDA',
}

_P9_CX = (P9_ODD + P9_EVEN) / 2     # 50.80
_P9_CY = _P8_CY                      # 13.97


def _p9_pads() -> str:
    lines = []
    for row in range(1, 11):
        y = _row_y(row)
        pin_odd = 2 * row - 1
        pin_even = 2 * row
        lines.append(_pad(str(pin_odd),  P9_ODD,  y, _P9_CX, _P9_CY,
                          _P9_NET.get(pin_odd, '')))
        lines.append(_pad(str(pin_even), P9_EVEN, y, _P9_CX, _P9_CY,
                          _P9_NET.get(pin_even, '')))
    return '\n'.join(lines)


# ── Display header pad definitions ────────────────────────────

_DISP_NET = [
    '/GND',       # pin 1
    '/+3.3V',     # pin 2
    '/SCL',       # pin 3
    '/SDA',       # pin 4
    '/BTN_K4',    # pin 5
    '/BTN_K3',    # pin 6
    '/BTN_K2',    # pin 7
    '/BTN_K1',    # pin 8
]

_DISP_CX = DISP_X1 + 3.5 * PITCH    # 27.305  (centre of 8-pin row)
_DISP_CY = DISP_Y                    # 5.08


def _disp_pads() -> str:
    lines = []
    for i, net in enumerate(_DISP_NET, start=1):
        x = DISP_X1 + (i - 1) * PITCH
        lines.append(_pad(str(i), x, DISP_Y, _DISP_CX, _DISP_CY, net))
    return '\n'.join(lines)


# ── Courtyard helpers ─────────────────────────────────────────

def _fp_rect(x1: float, y1: float, x2: float, y2: float,
             layer: str = 'F.CrtYd', width: float = 0.05) -> str:
    return (
        f'    (fp_rect\n'
        f'      (start {x1:.4f} {y1:.4f})\n'
        f'      (end {x2:.4f} {y2:.4f})\n'
        f'      (layer "{layer}")\n'
        f'      (uuid "{_uid()}")\n'
        f'      (stroke (width {width}) (type default))\n'
        f'    )'
    )


def _fp_line(x1: float, y1: float, x2: float, y2: float,
             layer: str = 'F.SilkS', width: float = 0.12) -> str:
    return (
        f'    (fp_line\n'
        f'      (start {x1:.4f} {y1:.4f})\n'
        f'      (end {x2:.4f} {y2:.4f})\n'
        f'      (layer "{layer}")\n'
        f'      (uuid "{_uid()}")\n'
        f'      (stroke (width {width}) (type default))\n'
        f'    )'
    )


# ── Footprint builder ─────────────────────────────────────────

def _footprint(ref: str, val: str, cx: float, cy: float,
               pads: str, decorations: str,
               ref_dy: float = -2.0) -> str:
    return (
        f'  (footprint "pihole_display:{ref}"\n'
        f'    (layer "F.Cu")\n'
        f'    (at {cx:.4f} {cy:.4f})\n'
        f'    (uuid "{_uid()}")\n'
        f'    (fp_text reference "{ref}"\n'
        f'      (at 0 {ref_dy:.2f})\n'
        f'      (layer "F.SilkS")\n'
        f'      (uuid "{_uid()}")\n'
        f'      (effects (font (size 1 1) (thickness 0.15)))\n'
        f'    )\n'
        f'    (fp_text value "{val}"\n'
        f'      (at 0 2.0)\n'
        f'      (layer "F.Fab")\n'
        f'      (uuid "{_uid()}")\n'
        f'      (effects (font (size 1 1) (thickness 0.15)))\n'
        f'    )\n'
        + decorations + '\n'
        + pads + '\n'
        '  )'
    )


def _build_j2_p8() -> str:
    # Courtyard (relative to _P8_CX, _P8_CY)
    hw = 1.27 + 0.50   # half-width + margin
    hy = 11.43 + 0.50   # half-height + margin
    dec = '\n'.join([
        _fp_rect(-hw, -hy, hw, hy),
        _fp_rect(-hw, -hy, hw, hy, layer='F.Fab', width=0.10),
        # Pin-1 triangle marker (silk)
        _fp_line(-hw, -hy, 0, -hy - 1.0),
        _fp_line(0, -hy - 1.0, hw, -hy),
    ])
    return _footprint('J2', 'P8_1-20', _P8_CX, _P8_CY,
                      _p8_pads(), dec, ref_dy=-14.5)


def _build_j1_p9() -> str:
    hw = 1.27 + 0.50
    hy = 11.43 + 0.50
    dec = '\n'.join([
        _fp_rect(-hw, -hy, hw, hy),
        _fp_rect(-hw, -hy, hw, hy, layer='F.Fab', width=0.10),
        _fp_line(-hw, -hy, 0, -hy - 1.0),
        _fp_line(0, -hy - 1.0, hw, -hy),
    ])
    return _footprint('J1', 'P9_1-20', _P9_CX, _P9_CY,
                      _p9_pads(), dec, ref_dy=-14.5)


def _build_j3_disp() -> str:
    # 1×8 header — single row
    hw = 3.5 * PITCH + 0.50   # 9.39 mm
    hh = 1.27 + 0.50          # 1.77 mm
    dec = '\n'.join([
        _fp_rect(-hw, -hh, hw, hh),
        _fp_rect(-hw, -hh, hw, hh, layer='F.Fab', width=0.10),
    ])
    return _footprint('J3', 'DISP_1x8', _DISP_CX, _DISP_CY,
                      _disp_pads(), dec, ref_dy=-2.8)


# ── Board graphics ────────────────────────────────────────────

def _board_outline() -> str:
    return (
        f'  (gr_rect\n'
        f'    (start 0 0)\n'
        f'    (end {BOARD_W:.3f} {BOARD_H:.3f})\n'
        f'    (layer "Edge.Cuts")\n'
        f'    (uuid "{_uid()}")\n'
        f'    (stroke (width 0.05) (type default))\n'
        f'  )'
    )


def _silk_text(text: str, x: float, y: float,
               size: float = 0.8, thickness: float = 0.12) -> str:
    return (
        f'  (gr_text "{text}"\n'
        f'    (at {x:.3f} {y:.3f})\n'
        f'    (layer "F.SilkS")\n'
        f'    (uuid "{_uid()}")\n'
        f'    (effects (font (size {size} {size}) (thickness {thickness})))\n'
        f'  )'
    )


def _fab_text(text: str, x: float, y: float, size: float = 0.7) -> str:
    return (
        f'  (gr_text "{text}"\n'
        f'    (at {x:.3f} {y:.3f})\n'
        f'    (layer "F.Fab")\n'
        f'    (uuid "{_uid()}")\n'
        f'    (effects (font (size {size} {size}) (thickness 0.10)))\n'
        f'  )'
    )


# ── Assembly ──────────────────────────────────────────────────

def generate() -> str:
    """Assemble and return the complete KiCad PCB file content."""
    nets_str = '\n'.join(f'  (net {nid} {name})' for nid, name in NETS)

    j1 = _build_j1_p9()
    j2 = _build_j2_p8()
    j3 = _build_j3_disp()

    # Silkscreen: connector labels + pin-1 callouts
    silk_items = [
        _silk_text('P9',  P9_ODD - 1.8, 0.8, size=0.7),
        _silk_text('P8',  P8_ODD - 0.5, 0.8, size=0.7),
        _silk_text('DISP', _DISP_CX,    3.0, size=0.7),
    ]
    silk = '\n'.join(silk_items)

    # Fab layer: net assignment legend
    fab_items = [
        _fab_text('Routing: F.Cu=BTN  B.Cu=PWR/I2C',
                  BOARD_W / 2, BOARD_H - 1.5, size=0.6),
    ]
    fab = '\n'.join(fab_items)

    return f"""(kicad_pcb
  (version 20230121)
  (generator "python-generator")
  (general
    (thickness 1.6)
    (legacy_teardrops no)
  )
  (paper "A4")
  (layers
    (0 "F.Cu" signal)
    (31 "B.Cu" signal)
    (36 "B.SilkS" user "B.Silkscreen")
    (37 "F.SilkS" user "F.Silkscreen")
    (44 "B.CrtYd" user "B.Courtyard")
    (45 "F.CrtYd" user "F.Courtyard")
    (46 "B.Fab" user "B.Fab")
    (47 "F.Fab" user "F.Fab")
    (48 "Edge.Cuts" user)
  )
  (setup
    (pad_to_mask_clearance 0)
    (solder_mask_min_width 0)
    (pcbplotparams
      (layerselection 0x00010fc_ffffffff)
      (plot_on_all_layers_selection 0x0000000_00000000)
      (disableapertmacros false)
      (usegerberextensions false)
      (usegerberattributes true)
      (usegerberadvancedattributes true)
      (creategerberjobfile true)
      (dashed_line_gap_ratio 0.5)
      (svguseinch false)
      (svgprecision 4)
      (excludeedgelayer true)
      (plotframeref false)
      (viasonmask false)
      (mode 1)
      (useauxorigin false)
      (hpglpennumber 1)
      (hpglpenspeed 20)
      (hpglpendiameter 15.000000)
      (pdf_front_fp_property_popups true)
      (pdf_back_fp_property_popups true)
      (dxfpolygonmode true)
      (dxfimperialunits true)
      (dxfusepcbnewfont true)
      (psnegative false)
      (psa4output false)
      (plotreference true)
      (plotvalue true)
      (plotfptext true)
      (plotinvisibletext false)
      (sketchpadsonfab false)
      (subtractmaskfromsilk false)
      (outputformat 1)
      (mirror false)
      (drillshape 0)
      (scaleselection 1)
      (outputdirectory "")
    )
  )
{nets_str}
{_board_outline()}
{j1}
{j2}
{j3}
{silk}
{fab}
)
"""


# ── Entry point ───────────────────────────────────────────────

if __name__ == '__main__':
    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_file = os.path.join(out_dir, 'pihole_display_cape.kicad_pcb')
    content = generate()
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'Written: {out_file}')
    print(f'  Board:    {BOARD_W} x {BOARD_H} mm')
    print(f'  J1 (P9):  center ({_P9_CX:.2f}, {_P9_CY:.2f})')
    print(f'  J2 (P8):  center ({_P8_CX:.2f}, {_P8_CY:.2f})')
    print(f'  J3 (DISP): center ({_DISP_CX:.3f}, {_DISP_CY:.2f})')
