"""Render and manage OLED UI screens, menus, and transient messages."""

# ============================================================
# display_manager.py — OLED screen rendering (luma.oled)
# SSD1315 / SSD1306 compatible, 128x64 pixels
# ============================================================

import time
import logging
from enum import Enum, auto
from typing import Callable, List, Optional, Tuple

from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas
from PIL import ImageFont

import config
from data import DataCache

log = logging.getLogger(__name__)

# ── Fonts ─────────────────────────────────────────────────────

try:
    # Better font if available
    _FONT_SM = ImageFont.truetype(
        '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
        9,
    )
    _FONT_MD = ImageFont.truetype(
        '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
        11,
    )
    _FONT_LG = ImageFont.truetype(
        '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf',
        13,
    )
except OSError:
    _FONT_SM = ImageFont.load_default()
    _FONT_MD = ImageFont.load_default()
    _FONT_LG = ImageFont.load_default()


# ── Screen definitions ───────────────────────────────────────

class Screen(Enum):
    """Logical top-level screens shown in normal UI mode."""

    PIHOLE = 0
    UNBOUND = 1
    NETWORK = 2
    SYSTEM = 3
    STATUS = 4


SCREEN_NAMES = {
    Screen.PIHOLE:  'Pi-hole',
    Screen.UNBOUND: 'Unbound',
    Screen.NETWORK: 'Network',
    Screen.SYSTEM:  'System',
    Screen.STATUS:  'Status',
}

SCREEN_ORDER = [
    Screen.PIHOLE,
    Screen.UNBOUND,
    Screen.NETWORK,
    Screen.SYSTEM,
    Screen.STATUS,
]


class UIMode(Enum):
    """UI state machine modes for screen, menu, message, and sleep."""

    NORMAL = auto()   # Screen view
    MENU = auto()   # Action menu
    CONFIRM = auto()   # Confirmation dialog
    MESSAGE = auto()   # Short status message
    SLEEP = auto()   # Display sleeping


# ── Display manager ──────────────────────────────────────────

class DisplayManager:  # pylint: disable=too-many-instance-attributes
    """Coordinate OLED rendering and UI navigation state."""

    W = 128
    H = 64

    def __init__(self, data: DataCache):
        """Initialize display device, UI state, and message/menu buffers."""
        self._data = data
        self._device = self._init_device()
        self._mode = UIMode.NORMAL
        self._screen_idx = 0
        self._menu_items: List[Tuple[str, Callable[[], None]]] = []
        self._menu_sel = 0
        self._msg_text = ''
        self._msg_until = 0.0
        self._last_input = time.monotonic()

    def _init_device(self):
        """Initialize the OLED device using configured I2C settings."""
        try:
            serial = i2c(port=config.I2C_PORT, address=config.I2C_ADDRESS)
            device = ssd1306(
                serial,
                width=self.W,
                height=self.H,
                rotate=config.DISPLAY_ROTATE,
            )
            log.info(
                'OLED initialized on I2C%d @ 0x%02X',
                config.I2C_PORT,
                config.I2C_ADDRESS,
            )
            return device
        except Exception as e:
            log.error('OLED initialization failed: %s', e)
            raise

    # ── Public API ───────────────────────────────────────────

    @property
    def current_screen(self) -> Screen:
        """Return the currently selected top-level screen."""
        return SCREEN_ORDER[self._screen_idx]

    @property
    def mode(self) -> UIMode:
        """Expose current UI mode without exposing private attributes."""
        return self._mode

    def wake(self):
        """Public wrapper to wake display and reset inactivity timer."""
        self._wake()

    def next_screen(self):
        """Switch to the next screen in cyclic order."""
        self._screen_idx = (self._screen_idx + 1) % len(SCREEN_ORDER)
        self._mode = UIMode.NORMAL
        self._wake()

    def prev_screen(self):
        """Switch to the previous screen in cyclic order."""
        self._screen_idx = (self._screen_idx - 1) % len(SCREEN_ORDER)
        self._mode = UIMode.NORMAL
        self._wake()

    def home(self):
        """Return to the default first screen."""
        self._screen_idx = 0
        self._mode = UIMode.NORMAL
        self._wake()

    def show_menu(self, items: List[Tuple[str, Callable[[], None]]]):
        """Open the action menu with the provided label/action entries."""
        self._menu_items = items
        self._menu_sel = 0
        self._mode = UIMode.MENU
        self._wake()

    def menu_up(self):
        """Move menu selection one item up with wrap-around."""
        if self._menu_items:
            self._menu_sel = (self._menu_sel - 1) % len(self._menu_items)

    def menu_down(self):
        """Move menu selection one item down with wrap-around."""
        if self._menu_items:
            self._menu_sel = (self._menu_sel + 1) % len(self._menu_items)

    def menu_confirm(self) -> Optional[Callable[[], None]]:
        """Confirm current menu item and return its action callback."""
        if self._menu_items:
            _, action = self._menu_items[self._menu_sel]
            self._mode = UIMode.NORMAL
            return action
        return None

    def menu_cancel(self):
        """Close menu and return to normal screen mode."""
        self._mode = UIMode.NORMAL

    def show_splash(self):
        """Render startup splash screen directly to the display."""
        with canvas(self._device) as draw:
            draw.text((20, 8), 'pihole-display', font=_FONT_LG, fill='white')
            draw.line([(10, 22), (self.W - 10, 22)], fill='white', width=1)
            draw.text(
                (15, 26), 'BeagleBone Black', font=_FONT_SM, fill='white',
            )
            draw.text(
                (10, 37), 'Pi-hole + Unbound', font=_FONT_SM, fill='white',
            )
            draw.text((20, 50), 'Loading data...', font=_FONT_SM, fill='white')
        self._wake()

    def show_message(self, text: str, duration: float = 2.0):
        """Show a temporary centered message for the given duration."""
        self._msg_text = text
        self._msg_until = time.monotonic() + duration
        self._mode = UIMode.MESSAGE
        self._wake()

    def toggle_sleep(self):
        """Toggle display sleep mode on or off."""
        if self._mode == UIMode.SLEEP:
            self._wake()
        else:
            self._mode = UIMode.SLEEP
            self._device.hide()

    def update(self):
        """Main render loop, call periodically."""
        now = time.monotonic()

        if self._enter_sleep_on_timeout(now):
            return

        self._handle_message_timeout(now)
        if self._mode == UIMode.SLEEP:
            return

        with canvas(self._device) as draw:
            self._render_mode(draw)

    def _enter_sleep_on_timeout(self, now: float) -> bool:
        """Put display to sleep when inactivity timeout is reached."""
        if (
            config.DISPLAY_TIMEOUT > 0
            and self._mode != UIMode.SLEEP
            and now - self._last_input > config.DISPLAY_TIMEOUT
        ):
            self._mode = UIMode.SLEEP
            self._device.hide()
            return True
        return False

    def _handle_message_timeout(self, now: float):
        """Return from message mode once the message duration is over."""
        if self._mode == UIMode.MESSAGE and now > self._msg_until:
            self._mode = UIMode.NORMAL

    def _render_mode(self, draw):
        """Render the current UI mode into the draw canvas."""
        if self._mode == UIMode.NORMAL:
            self._render_screen(draw)
            return
        if self._mode == UIMode.MENU:
            self._render_menu(draw)
            return
        if self._mode == UIMode.MESSAGE:
            self._render_message(draw)

    def _wake(self):
        """Reset inactivity timer and wake display if it is sleeping."""
        self._last_input = time.monotonic()
        if self._mode == UIMode.SLEEP:
            self._mode = UIMode.NORMAL
            self._device.show()

    # ── Screen renderer ──────────────────────────────────────

    def _render_screen(self, draw):
        screen = SCREEN_ORDER[self._screen_idx]
        {
            Screen.PIHOLE:  self._screen_pihole,
            Screen.UNBOUND: self._screen_unbound,
            Screen.NETWORK: self._screen_network,
            Screen.SYSTEM:  self._screen_system,
            Screen.STATUS:  self._screen_status,
        }[screen](draw)

    def _header(self, draw, title: str, status: str = '', ok: bool = True):
        """Header row: title (LG, left) + status/time (SM, right)."""
        now = time.strftime('%H:%M')
        dot = '\u25CF' if ok else '!'
        draw.text((0, 0), title, font=_FONT_LG, fill='white')
        right = f'{status} {dot}{now}' if status else f'{dot}{now}'
        # Right align: ~6px per character with FONT_SM
        rx = max(0, self.W - len(right) * 6)
        draw.text((rx, 3), right, font=_FONT_SM, fill='white')
        draw.line([(0, 14), (self.W, 14)], fill='white', width=1)

    def _nav_hint(self, draw, action_label: str = ''):
        """Bottom navigation: ^ Screen v  [#]Action"""
        y = self.H - 10
        draw.line([(0, y - 1), (self.W, y - 1)], fill='white', width=1)
        hint = '[^][v] Screen'
        if action_label:
            hint += f'  [#]{action_label}'
        draw.text((0, y), hint, font=_FONT_SM, fill='white')

    def _screen_pihole(self, draw):
        ph = self._data.pihole
        ok = ph.enabled and not ph.error

        if ph.pause_remaining > 0:
            mins = ph.pause_remaining // 60
            secs = ph.pause_remaining % 60
            status = 'PAUSE'
        elif ph.enabled:
            status = 'ACTIVE'
        else:
            status = 'OFF'

        self._header(draw, 'Pi-hole', status, ok)

        if ph.error:
            draw.text(
                (0, 17),
                'Error: ' + ph.error[:18],
                font=_FONT_SM,
                fill='white',
            )
        elif ph.pause_remaining > 0:
            mins = ph.pause_remaining // 60
            secs = ph.pause_remaining % 60
            draw.text(
                (0, 17),
                f'Left:  {mins:02d}:{secs:02d}',
                font=_FONT_MD,
                fill='white',
            )
            draw.text(
                (0, 30),
                f'Req:   {ph.queries_today:>7,}',
                font=_FONT_MD,
                fill='white',
            )
            draw.text(
                (0, 43),
                f'Clients:{ph.clients:>6}',
                font=_FONT_MD,
                fill='white',
            )
        else:
            draw.text(
                (0, 17),
                f'Block: {ph.block_percent:5.1f}%',
                font=_FONT_MD,
                fill='white',
            )
            draw.text(
                (0, 30),
                f'Req:   {ph.queries_today:>7,}',
                font=_FONT_MD,
                fill='white',
            )
            draw.text(
                (0, 43),
                f'Clients:{ph.clients:>6}',
                font=_FONT_MD,
                fill='white',
            )

        self._nav_hint(draw, 'Menu')

    def _screen_unbound(self, draw):
        ub = self._data.unbound
        ok = ub.running and not ub.error

        self._header(draw, 'Unbound', '', ok)

        if ub.error:
            draw.text(
                (0, 17),
                'Error: ' + ub.error[:18],
                font=_FONT_SM,
                fill='white',
            )
        else:
            draw.text(
                (0, 17),
                f'Cache: {ub.cache_percent:5.1f}%',
                font=_FONT_MD,
                fill='white',
            )
            draw.text(
                (0, 30),
                f'Q/s:   {ub.queries_ps:>6.1f}',
                font=_FONT_MD,
                fill='white',
            )
            draw.text(
                (0, 43),
                f'Total: {ub.queries_total:>7,}',
                font=_FONT_MD,
                fill='white',
            )

        self._nav_hint(draw, 'Menu')

    def _screen_network(self, draw):
        sy = self._data.system
        self._header(draw, 'Network', '', True)
        draw.text(
            (0, 16),
            f'IP:   {sy.ip_address}',
            font=_FONT_SM,
            fill='white',
        )
        draw.text((0, 26), f'GW:   {sy.gateway}', font=_FONT_SM, fill='white')
        draw.text(
            (0, 36),
            f'Host: {sy.hostname[:14]}',
            font=_FONT_SM,
            fill='white',
        )
        draw.text(
            (0, 44),
            f'Up:   {sy.uptime_str}',
            font=_FONT_SM,
            fill='white',
        )
        self._nav_hint(draw)

    def _screen_system(self, draw):
        sy = self._data.system
        self._header(draw, 'System', '', True)
        draw.text(
            (0, 17),
            f'CPU: {sy.cpu_percent:4.0f}%  {sy.cpu_temp:.0f}\u00b0C',
            font=_FONT_MD,
            fill='white',
        )
        draw.text(
            (0, 30),
            f'RAM: {sy.ram_used_mb}/{sy.ram_total_mb}MB',
            font=_FONT_MD,
            fill='white',
        )
        draw.text(
            (0, 43),
            f'Disk:{sy.disk_used_gb}/{sy.disk_total_gb}GB',
            font=_FONT_MD,
            fill='white',
        )
        self._nav_hint(draw)

    def _screen_status(self, draw):
        sy = self._data.system
        self._header(draw, 'Status', '', True)

        def row(y, label, ok):
            marker = '[OK]' if ok else '[!!]'
            draw.text((0, y), f'{marker} {label}', font=_FONT_SM, fill='white')

        row(17, 'Pi-hole ', sy.pihole_ok)
        row(28, 'Unbound ', sy.unbound_ok)
        row(39, 'DNS     ', sy.dns_ok)
        self._nav_hint(draw, 'Actions')

    # ── Menu renderer ────────────────────────────────────────

    def _render_menu(self, draw):
        draw.text((0, 0), 'Action:', font=_FONT_SM, fill='white')
        # Scroll indicator
        total = len(self._menu_items)
        draw.text(
            (45, 0),
            f'{self._menu_sel + 1}/{total}',
            font=_FONT_SM,
            fill='white',
        )
        draw.line([(0, 10), (self.W, 10)], fill='white', width=1)

        visible = 3   # 3 items = no overflow in nav row
        start = max(0, self._menu_sel - visible + 1)
        visible_items = self._menu_items[start:start + visible]
        for i, (label, _) in enumerate(visible_items):
            y = 13 + i * 13
            idx = start + i
            prefix = '>' if idx == self._menu_sel else ' '
            draw.text((0, y), f'{prefix} {label}', font=_FONT_SM, fill='white')

        draw.line(
            [(0, self.H - 10), (self.W, self.H - 10)],
            fill='white',
            width=1,
        )
        draw.text(
            (0, self.H - 9),
            '[^][v] Nav  [#]OK  [*]Back',
            font=_FONT_SM,
            fill='white',
        )

    # ── Message renderer ─────────────────────────────────────

    def _render_message(self, draw):
        """Render the active multiline message centered on screen."""
        lines = self._msg_text.split('\n')
        y = max(0, (self.H - len(lines) * 14) // 2)
        for line in lines:
            w = self.W
            # Center text
            try:
                bbox = _FONT_MD.getbbox(line)
                tw = bbox[2] - bbox[0]
            except (AttributeError, TypeError):
                tw = len(line) * 7
            draw.text(((w - tw) // 2, y), line, font=_FONT_MD, fill='white')
            y += 14

    def cleanup(self):
        """Release display resources and ignore cleanup errors."""
        try:
            self._device.cleanup()
        except (AttributeError, OSError):
            pass
