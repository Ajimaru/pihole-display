#!/usr/bin/env python3
"""Generate OLED mockup PNGs for pihole-display documentation."""

# ============================================================
# generate_mockups.py — Render all OLED screens as PNG
# Drives the real DisplayManager on a luma dummy device, so the
# mockups are pixel-exact copies of the 128x64 display.
# Output: mockups/*.png  (4x nearest-neighbour upscale = 512x256 px)
#
# Needs the app requirements (luma.oled, Pillow, requests, psutil)
# and the DejaVu fonts, e.g. run it with the venv on the target:
#   /opt/pihole-display/venv/bin/python docs/generate_mockups.py
# ============================================================

import os
import sys
import time
from dataclasses import replace
from types import SimpleNamespace

from PIL import Image
from luma.core.device import dummy

DOCS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(DOCS_DIR, '..', 'pihole-display'))

# pylint: disable=wrong-import-position
import display_manager as dm  # noqa: E402
from data import PiholeStats, SystemStats, UnboundStats  # noqa: E402

SCALE = 4  # 4x enlarged for better readability
OUT_DIR = os.path.join(DOCS_DIR, 'mockups')
os.makedirs(OUT_DIR, exist_ok=True)

# Fixed clock so mockups don't change on every run
dm.time = SimpleNamespace(
    strftime=lambda fmt: '14:32',
    monotonic=time.monotonic,
)
dm.DisplayManager._init_device = (  # pylint: disable=protected-access
    lambda self: dummy(width=self.W, height=self.H, mode='1')
)

PIHOLE = PiholeStats(
    enabled=True, queries_today=4821, block_percent=23.4, clients=8,
)
UNBOUND = UnboundStats(
    running=True, cache_percent=67.2, queries_total=12847, queries_ps=4.1,
)
SYSTEM = SystemStats(
    hostname='beaglebone', ip_address='192.168.1.10',
    gateway='192.168.1.1', cpu_percent=12, cpu_temp=48,
    ram_used_mb=234, ram_total_mb=512, disk_used_gb=3.1,
    disk_total_gb=16.0, uptime_str='3d 14:22',
    pihole_ok=True, unbound_ok=True, dns_ok=True,
)

PIHOLE_MENU = [
    'Pause 5 Min', 'Pause 15 Min', 'Pause 30 Min', 'Pause 1 Hour',
    'Disable', 'Gravity update', 'Clear DNS cache',
]
PIHOLE_OFF_MENU = ['Enable', 'Gravity update', 'Clear DNS cache']
UNBOUND_MENU = ['Clear cache', 'Restart']
STATUS_MENU = [
    'Restart Pi-hole', 'Restart Unbound', 'Restart all', 'Refresh data',
]


def new_display(pihole=PIHOLE, unbound=UNBOUND, system=SYSTEM):
    """Create a DisplayManager on a dummy device with the given data."""
    data = SimpleNamespace(pihole=pihole, unbound=unbound, system=system)
    return dm.DisplayManager(data)


def save(disp, name: str, render: bool = True):
    """Render the current UI state and save it upscaled as RGB PNG."""
    if render:
        disp.update()
    img = disp._device.image.convert('RGB')  # pylint: disable=protected-access
    img = img.resize((img.width * SCALE, img.height * SCALE), Image.NEAREST)
    img.save(os.path.join(OUT_DIR, name))
    print(f'  -> {name}')


def screen(name: str, which, **data):
    """Render one top-level screen with optional data overrides."""
    disp = new_display(**data)
    disp._screen_idx = dm.SCREEN_ORDER.index(which)  # pylint: disable=W0212
    save(disp, name)


def menu(name: str, labels, selected: int = 0, title: str = 'Action:'):
    """Render an action menu with the given entry selected."""
    disp = new_display()
    disp.show_menu([(label, None) for label in labels], title=title)
    for _ in range(selected):
        disp.menu_down()
    save(disp, name)


def message(text: str, name: str):
    """Render a centered multiline message screen."""
    disp = new_display()
    disp.show_message(text, duration=60)
    save(disp, name)


def splash():
    """Render the startup splash screen."""
    disp = new_display()
    disp.show_splash()
    save(disp, '00_splash.png', render=False)


def sleep():
    """Render a fully black screen representing OLED sleep mode."""
    disp = new_display()
    disp._device.clear()  # pylint: disable=protected-access
    save(disp, '20_sleep.png', render=False)


# ── Main ────────────────────────────────────────────────────

if __name__ == '__main__':
    print(f'Rendering mockups to: {OUT_DIR}')
    print()

    print('--- Screens ---')
    splash()
    screen('01_pihole_active.png', dm.Screen.PIHOLE)
    screen(
        '02_pihole_pause.png', dm.Screen.PIHOLE,
        pihole=replace(PIHOLE, enabled=False, pause_remaining=14 * 60 + 22),
    )
    screen(
        '03_pihole_off.png', dm.Screen.PIHOLE,
        pihole=replace(PIHOLE, enabled=False, block_percent=0.0),
    )
    screen('04_unbound.png', dm.Screen.UNBOUND)
    screen(
        '05_unbound_error.png', dm.Screen.UNBOUND,
        unbound=replace(UNBOUND, running=False, error='not active'),
    )
    screen('06_network.png', dm.Screen.NETWORK)
    screen('07_system.png', dm.Screen.SYSTEM)
    screen('08_status_ok.png', dm.Screen.STATUS)
    screen(
        '09_status_error.png', dm.Screen.STATUS,
        system=replace(SYSTEM, unbound_ok=False),
    )

    print('--- Menus ---')
    menu('10_menu_pihole_active.png', PIHOLE_MENU)
    menu('11_menu_pihole_scroll.png', PIHOLE_MENU, selected=5)
    menu('12_menu_pihole_off.png', PIHOLE_OFF_MENU)
    menu('13_menu_unbound.png', UNBOUND_MENU)
    menu('14_menu_status_actions.png', STATUS_MENU)
    menu('14b_menu_status_scrolled.png', STATUS_MENU, selected=3)
    menu('14c_menu_system.png', ['Reboot', 'Shutdown', 'Screen lock: off'])
    menu('14d_confirm_reboot.png', ['No', 'Yes'], title='Reboot?')

    print('--- Messages ---')
    message('Pi-hole\nPause 15 min...', '15_message_pause.png')
    message('Pi-hole ACTIVE', '16_message_active.png')
    message('Pi-hole OFF', '17_message_off.png')
    message('Cache cleared', '18_message_flush.png')
    message(
        'Gravity\nupdate...\n(takes time!)',
        '19_message_gravity_update.png',
    )
    message('Rebooting...', '19b_message_reboot.png')
    message('Screen lock\nON\n(hold * 5s)', '19c_message_lock_on.png')
    sleep()

    print()
    print(f'Done! {len(os.listdir(OUT_DIR))} files in {OUT_DIR}')
