#!/usr/bin/env python3
"""Generate OLED mockup PNGs for pihole-display documentation."""

# ============================================================
# generate_mockups.py — Render all OLED screens as PNG
# Shows exactly how the 128x64 display will look
# Output: mockups/*.png  (4x scale = 512x256 px)
# ============================================================

import os
from PIL import Image, ImageDraw, ImageFont

SCALE = 4  # 4x enlarged for better readability
W, H = 128, 64
SW, SH = W * SCALE, H * SCALE
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Fonts ────────────────────────────────────────────────────


def load_fonts(scale):
    """Load regular/large fonts with fallback to default Pillow font."""
    paths = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf',
        '/usr/share/fonts/truetype/freefont/FreeMono.ttf',
    ]
    available = [p for p in paths if os.path.exists(p)]
    if not available:
        f = ImageFont.load_default()
        return f, f, f

    regular = available[0]
    bold = next(
        (p for p in available if 'Bold' in os.path.basename(p)),
        regular,
    )

    try:
        return (
            ImageFont.truetype(regular, 9 * scale),
            ImageFont.truetype(regular, 11 * scale),
            ImageFont.truetype(bold, 13 * scale),
        )
    except OSError:
        f = ImageFont.load_default()
        return f, f, f


FONT_SM, FONT_MD, FONT_LG = load_fonts(SCALE)


# ── Base renderer ────────────────────────────────────────────


def new_image():
    """Create a new monochrome scaled image and its drawing context."""
    img = Image.new('1', (SW, SH), 0)
    draw = ImageDraw.Draw(img)
    return img, draw


def s(v):
    """Scale a pixel value."""
    return v * SCALE


def header(
    draw,
    title: str,
    status: str = '',
    ok: bool = True,
    time_str: str = '14:32',
):
    """Render the top header with title, status indicator and time."""

    dot = '●' if ok else '!'
    # Title on the left, large
    draw.text((s(0), s(0)), title, font=FONT_LG, fill=1)
    # Status + time on the right, small; right-aligned via getbbox
    right = f'{status} {dot}{time_str}' if status else f'{dot}{time_str}'
    try:
        bbox = FONT_SM.getbbox(right)
        tw = bbox[2] - bbox[0]
    except (AttributeError, TypeError):
        tw = len(right) * 6 * SCALE
    draw.text((SW - tw - SCALE, s(3)), right, font=FONT_SM, fill=1)
    draw.line([(s(0), s(14)), (s(W), s(14))], fill=1, width=SCALE)


def nav_hint(draw, action: str = ''):
    """Render bottom navigation hints and optional action label."""
    y = H - 10
    draw.line([(s(0), s(y - 1)), (s(W), s(y - 1))], fill=1, width=SCALE)
    hint = '[^][v] Screen'
    if action:
        hint += f'  [#]{action}'
    draw.text((s(0), s(y)), hint, font=FONT_SM, fill=1)


def save(img, name: str):
    """Save monochrome image as RGB PNG in the docs output directory."""
    path = os.path.join(OUT_DIR, name)
    # Save as RGB: white content on black background.
    rgb = Image.new('RGB', (SW, SH), (0, 0, 0))
    rgb.paste((255, 255, 255), mask=img)
    rgb.save(path)
    print(f'  -> {name}')


# ── Screen 1: Pi-hole active ────────────────────────────────


def screen_pihole_active():
    """Render screen showing active Pi-hole metrics."""
    img, draw = new_image()
    header(draw, 'Pi-hole', status='ACTIVE', ok=True)
    draw.text((s(0), s(17)), 'Block:  23.4%', font=FONT_MD, fill=1)
    draw.text((s(0), s(30)), 'Req:     4,821', font=FONT_MD, fill=1)
    draw.text((s(0), s(43)), 'Clients:     8', font=FONT_MD, fill=1)
    nav_hint(draw, 'Menu')
    save(img, '01_pihole_aktiv.png')


def screen_pihole_paused():
    """Render screen showing paused Pi-hole state."""
    img, draw = new_image()
    header(draw, 'Pi-hole', status='PAUSE', ok=False)
    draw.text((s(0), s(17)), 'Left:   14:22', font=FONT_MD, fill=1)
    draw.text((s(0), s(30)), 'Req:     4,821', font=FONT_MD, fill=1)
    draw.text((s(0), s(43)), 'Clients:     8', font=FONT_MD, fill=1)
    nav_hint(draw, 'Menu')
    save(img, '02_pihole_pause.png')


def screen_pihole_off():
    """Render screen showing disabled Pi-hole state."""
    img, draw = new_image()
    header(draw, 'Pi-hole', status='OFF', ok=False)
    draw.text((s(0), s(17)), 'Block:   0.0%', font=FONT_MD, fill=1)
    draw.text((s(0), s(30)), 'Req:     4,821', font=FONT_MD, fill=1)
    draw.text((s(0), s(43)), 'Clients:     8', font=FONT_MD, fill=1)
    nav_hint(draw, 'Menu')
    save(img, '03_pihole_aus.png')


# ── Screen 2: Unbound ───────────────────────────────────────


def screen_unbound():
    """Render Unbound runtime statistics screen."""
    img, draw = new_image()
    header(draw, 'Unbound', status='OK', ok=True)
    draw.text((s(0), s(17)), 'Cache:  67.2%', font=FONT_MD, fill=1)
    draw.text((s(0), s(30)), 'Q/s:      4.1', font=FONT_MD, fill=1)
    draw.text((s(0), s(43)), 'Total: 12,847', font=FONT_MD, fill=1)
    nav_hint(draw, 'Flush')
    save(img, '04_unbound.png')


def screen_unbound_error():
    """Render Unbound error status screen."""
    img, draw = new_image()
    header(draw, 'Unbound', status='ERROR', ok=False)
    draw.text((s(0), s(17)), 'Error: not active', font=FONT_SM, fill=1)
    nav_hint(draw, 'Restart')
    save(img, '05_unbound_fehler.png')


# ── Screen 3: Network ───────────────────────────────────────


def screen_network():
    """Render network information screen."""
    img, draw = new_image()
    header(draw, 'Network', ok=True)
    draw.text((s(0), s(16)), 'IP:   192.168.1.10', font=FONT_SM, fill=1)
    draw.text((s(0), s(26)), 'GW:   192.168.1.1',  font=FONT_SM, fill=1)
    draw.text((s(0), s(36)), 'Host: beaglebone',   font=FONT_SM, fill=1)
    draw.text((s(0), s(44)), 'Up:   3d 14:22',     font=FONT_SM, fill=1)
    nav_hint(draw)
    save(img, '06_netzwerk.png')


# ── Screen 4: System ────────────────────────────────────────


def screen_system():
    """Render system metrics screen (CPU, RAM, disk)."""
    img, draw = new_image()
    header(draw, 'System', ok=True)
    draw.text((s(0), s(17)), 'CPU:  12%   48\u00b0C', font=FONT_MD, fill=1)
    draw.text((s(0), s(30)), 'RAM: 234/512MB',        font=FONT_MD, fill=1)
    draw.text((s(0), s(43)), 'Disk:3.1/16.0GB',       font=FONT_MD, fill=1)
    nav_hint(draw)
    save(img, '07_system.png')


# ── Screen 5: Status ────────────────────────────────────────


def screen_status_ok():
    """Render overall status screen with all services healthy."""
    img, draw = new_image()
    header(draw, 'Status', ok=True)
    draw.text((s(0), s(17)), '[OK] Pi-hole ', font=FONT_SM, fill=1)
    draw.text((s(0), s(28)), '[OK] Unbound ', font=FONT_SM, fill=1)
    draw.text((s(0), s(39)), '[OK] DNS     ', font=FONT_SM, fill=1)
    nav_hint(draw, 'Actions')
    save(img, '08_status_ok.png')


def screen_status_error():
    """Render overall status screen with at least one service failure."""
    img, draw = new_image()
    header(draw, 'Status', ok=False)
    draw.text((s(0), s(17)), '[OK] Pi-hole ', font=FONT_SM, fill=1)
    draw.text((s(0), s(28)), '[!!] Unbound ', font=FONT_SM, fill=1)
    draw.text((s(0), s(39)), '[OK] DNS     ', font=FONT_SM, fill=1)
    nav_hint(draw, 'Actions')
    save(img, '09_status_fehler.png')


# ── Menu: Pi-hole (active) ──────────────────────────────────


def _menu_block(draw, title_count: str, items_3: list):
    """Helper: 3 items + scroll counter + nav bar."""
    draw.text((s(0), s(0)), 'Action:', font=FONT_SM, fill=1)
    draw.text((s(45), s(0)), title_count, font=FONT_SM, fill=1)
    draw.line([(s(0), s(10)), (s(W), s(10))], fill=1, width=SCALE)
    for i, label in enumerate(items_3):
        draw.text((s(0), s(13 + i * 13)), label, font=FONT_SM, fill=1)
    draw.line([(s(0), s(H - 10)), (s(W), s(H - 10))], fill=1, width=SCALE)
    nav_text = '[^][v] Nav  [#]OK  [*]Back'
    draw.text((s(0), s(H - 9)), nav_text, font=FONT_SM, fill=1)


def menu_pihole_active():
    """Render first page of the Pi-hole active-state action menu."""
    img, draw = new_image()
    _menu_block(draw, '1/6', [
        '> Pause 5 min',
        '  Pause 15 min',
        '  Pause 30 min',
    ])
    save(img, '10_menu_pihole_aktiv.png')


def menu_pihole_active2():
    """Render scrolled page of the Pi-hole active-state action menu."""
    img, draw = new_image()
    _menu_block(draw, '4/6', [
        '  Pause 1 hour',
        '  Disable',
        '> Gravity upd.',
    ])
    save(img, '11_menu_pihole_scroll.png')


def menu_pihole_off():
    """Render Pi-hole disabled-state action menu."""
    img, draw = new_image()
    _menu_block(draw, '1/3', [
        '> Enable',
        '  Gravity upd.',
        '  Clear DNS cache',
    ])
    save(img, '12_menu_pihole_aus.png')


# ── Menu: Unbound ───────────────────────────────────────────


def menu_unbound():
    """Render Unbound action menu."""
    img, draw = new_image()
    _menu_block(draw, '1/2', [
        '> Clear cache',
        '  Restart',
    ])
    save(img, '13_menu_unbound.png')


# ── Menu: Status / Actions ──────────────────────────────────


def menu_status():
    """Render first page of generic status actions menu."""
    img, draw = new_image()
    _menu_block(draw, '1/4', [
        '> Restart Pi-hole',
        '  Restart Unbound',
        '  Restart all',
    ])
    save(img, '14_menu_status.png')


def menu_status2():
    """Render scrolled page of generic status actions menu."""
    img, draw = new_image()
    _menu_block(draw, '4/4', [
        '  Restart all',
        '> Refresh data',
    ])
    save(img, '14b_menu_status_scroll.png')


# ── Messages ────────────────────────────────────────────────


def message(text: str, filename: str):
    """Render a centered multiline message screen and save it."""
    img, draw = new_image()
    lines = text.split('\n')
    y = max(0, (H - len(lines) * 14) // 2)
    for line in lines:
        try:
            bbox = FONT_MD.getbbox(line)
            tw = (bbox[2] - bbox[0]) // SCALE
        except (AttributeError, TypeError):
            tw = len(line) * 7
        x = max(0, (W - tw) // 2)
        draw.text((s(x), s(y)), line, font=FONT_MD, fill=1)
        y += 14
    save(img, filename)


def screen_sleep():
    """Render a fully black screen representing OLED sleep mode."""
    img = Image.new('1', (SW, SH), 0)
    # Fully black = display off
    save(img, '20_sleep.png')


def screen_splash():
    """Render startup splash screen."""
    img, draw = new_image()
    draw.text((s(20), s(8)), 'pihole-display', font=FONT_LG, fill=1)
    draw.line([(s(10), s(22)), (s(W - 10), s(22))], fill=1, width=SCALE)
    draw.text((s(15), s(26)), 'BeagleBone Black', font=FONT_SM, fill=1)
    draw.text((s(25), s(37)), 'Pi-hole + Unbound', font=FONT_SM, fill=1)
    draw.text((s(35), s(50)), 'Loading data...', font=FONT_SM, fill=1)
    save(img, '00_splash.png')


# ── Main ────────────────────────────────────────────────────

if __name__ == '__main__':
    print(f'Rendering mockups to: {OUT_DIR}')
    print()

    print('--- Screens ---')
    screen_splash()
    screen_pihole_active()
    screen_pihole_paused()
    screen_pihole_off()
    screen_unbound()
    screen_unbound_error()
    screen_network()
    screen_system()
    screen_status_ok()
    screen_status_error()

    print('--- Menus ---')
    menu_pihole_active()
    menu_pihole_active2()
    menu_pihole_off()
    menu_unbound()
    menu_status()
    menu_status2()

    print('--- Messages ---')
    message('Pi-hole\nPause 15 min...', '15_msg_pause.png')
    message('Pi-hole\nACTIVE', '16_msg_aktiv.png')
    message('Pi-hole\nOFF', '17_msg_aus.png')
    message('Cache\ncleared', '18_msg_flush.png')
    message('Gravity\nupdate...\n(takes time!)', '19_msg_gravity.png')
    screen_sleep()

    print()
    print(f'Done! {len(os.listdir(OUT_DIR))} files in {OUT_DIR}')
