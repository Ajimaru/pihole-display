#!/usr/bin/env python3
"""Main runtime loop for pihole-display UI and button interaction."""

# ============================================================
# main.py — pihole-display main program
# BeagleBone Black + SSD1315 OLED + 4 buttons
#
# Buttons:
#   K1 (^) = previous screen / menu up
#   K2 (v) = next screen     / menu down
#   K3 (#) = action / confirm
#   K4 (*) = back / long = home
# ============================================================

import logging
import signal
import threading
import time
import subprocess
from functools import partial

import config
from data import DataCache
from display_manager import DisplayManager, Screen, UIMode
from button_handler import ButtonHandler, ButtonEvent

# ── Logging ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger('main')


# ── Application ──────────────────────────────────────────────

class App:  # pylint: disable=too-few-public-methods
    """Wire data, display, and button components into one application."""

    def __init__(self):
        self._data = DataCache()
        self._display = DisplayManager(self._data)
        self._buttons = ButtonHandler(self._on_button)
        self._running = False
        self._data_lock = threading.Lock()

    # ── Start / Stop ─────────────────────────────────────────

    def run(self):
        """Start the app loop, refresh data, and update display continuously.

        The loop also handles periodic data refresh and clean shutdown.
        """
        log.info('pihole-display starting')
        self._running = True

        # Initial data fetch
        self._display.show_message('Loading data...')
        self._data.refresh()

        self._buttons.start()

        # Signal handlers
        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT,  self._shutdown)

        log.info('Main loop active')
        try:
            while self._running:
                # Refresh data when needed
                if self._data.needs_refresh():
                    with self._data_lock:
                        self._data.refresh()

                # Render display
                self._display.update()
                time.sleep(0.1)
        except (RuntimeError, OSError, ValueError) as e:
            log.error('Main loop error: %s', e)
        finally:
            self._cleanup()

    def _shutdown(self, *_):
        log.info('Shutting down...')
        self._running = False

    def _cleanup(self):
        self._buttons.stop()
        self._display.cleanup()
        log.info('Stopped')

    # ── Button handler ───────────────────────────────────────

    def _on_button(self, event: ButtonEvent):
        """Called from the button thread - keep it fast."""
        mode = self._display.mode

        # Wake display on every button press
        if mode == UIMode.SLEEP:
            self._display.wake()
            return

        if mode == UIMode.MENU:
            self._handle_menu_input(event)
        else:
            self._handle_normal_input(event)

    def _handle_normal_input(self, event: ButtonEvent):
        screen = self._display.current_screen

        if event == ButtonEvent.UP_SHORT:
            self._display.prev_screen()

        elif event == ButtonEvent.DOWN_SHORT:
            self._display.next_screen()

        elif event == ButtonEvent.BACK_SHORT:
            self._display.home()

        elif event == ButtonEvent.BACK_LONG:
            self._display.home()

        elif event == ButtonEvent.OK_SHORT:
            # Screen-specific action
            self._open_screen_menu(screen)

        elif event == ButtonEvent.UP_LONG:
            # Manual data refresh
            self._trigger_refresh('Refreshing...')

        elif event == ButtonEvent.DOWN_LONG:
            # Put display to sleep
            self._display.toggle_sleep()

    def _handle_menu_input(self, event: ButtonEvent):
        if event in (ButtonEvent.UP_SHORT, ButtonEvent.UP_LONG):
            self._display.menu_up()

        elif event in (ButtonEvent.DOWN_SHORT, ButtonEvent.DOWN_LONG):
            self._display.menu_down()

        elif event == ButtonEvent.OK_SHORT:
            action = self._display.menu_confirm()
            if action:
                # Run action in a separate thread (can take longer)
                threading.Thread(target=action, daemon=True).start()

        elif event in (ButtonEvent.BACK_SHORT, ButtonEvent.BACK_LONG):
            self._display.menu_cancel()

    # ── Screen menus ─────────────────────────────────────────

    def _open_screen_menu(self, screen: Screen):
        if screen == Screen.PIHOLE:
            self._menu_pihole()
        elif screen == Screen.UNBOUND:
            self._menu_unbound()
        elif screen == Screen.STATUS:
            self._menu_status()
        # NETWORK and SYSTEM have no menu

    def _menu_pihole(self):
        ph = self._data.pihole
        items = []

        if ph.enabled:
            for label, secs in config.PAUSE_OPTIONS:
                items.append((
                    f'Pause {label}',
                    partial(self._pihole_pause, secs)
                ))
            items.append(('Disable', self._pihole_disable))
        else:
            items.append(('Enable', self._pihole_enable))

        items += [
            ('Gravity update',  self._pihole_gravity),
            ('Clear DNS cache', self._pihole_flush),
        ]
        self._display.show_menu(items)

    def _menu_unbound(self):
        self._display.show_menu([
            ('Clear cache', self._unbound_flush),
            ('Restart',     self._unbound_restart),
        ])

    def _menu_status(self):
        self._display.show_menu([
            ('Restart Pi-hole',  self._pihole_restart),
            ('Restart Unbound',  self._unbound_restart),
            ('Restart all',      self._restart_all),
            (
                'Refresh data',
                lambda: self._trigger_refresh('Refreshing...'),
            ),
        ])

    # ── Actions ──────────────────────────────────────────────

    def _pihole_pause(self, seconds: int):
        mins = seconds // 60
        self._display.show_message(f'Pi-hole\nPause {mins} min...')
        ok = self._data.pihole_set_blocking(False, seconds)
        self._display.show_message(
            'Pi-hole paused' if ok else 'Error!'
        )

    def _pihole_disable(self):
        self._display.show_message('Pi-hole\ndisabling...')
        ok = self._data.pihole_set_blocking(False, 0)
        self._display.show_message(
            'Pi-hole OFF' if ok else 'Error!'
        )

    def _pihole_enable(self):
        self._display.show_message('Pi-hole\nenabling...')
        ok = self._data.pihole_set_blocking(True)
        self._display.show_message(
            'Pi-hole ACTIVE' if ok else 'Error!'
        )

    def _pihole_gravity(self):
        self._display.show_message(
            'Gravity\nupdate...\n(takes time!)',
            duration=120,
        )
        ok = self._data.pihole_gravity_update()
        self._display.show_message(
            'Update OK' if ok else 'Error!'
        )
        self._trigger_refresh()

    def _pihole_flush(self):
        self._display.show_message('Flushing\nDNS cache...')
        ok = self._data.pihole_flush()
        self._display.show_message(
            'Cache cleared' if ok else 'Error!'
        )

    def _pihole_restart(self):
        self._display.show_message('Pi-hole\nRestarting...')
        subprocess.run(
            ['pihole', 'restartdns'],
            capture_output=True,
            timeout=15,
            check=False,
        )
        self._trigger_refresh('Restart OK')

    def _unbound_flush(self):
        self._display.show_message('Unbound\nClearing cache...')
        ok = self._data.unbound_flush()
        self._display.show_message(
            'Cache cleared' if ok else 'Error!'
        )

    def _unbound_restart(self):
        self._display.show_message('Unbound\nRestarting...')
        subprocess.run(
            ['systemctl', 'restart', 'unbound'],
            capture_output=True,
            timeout=15,
            check=False,
        )
        time.sleep(2)
        self._trigger_refresh('Restart OK')

    def _restart_all(self):
        self._pihole_restart()
        self._unbound_restart()

    def _trigger_refresh(self, msg: str = ''):
        def _do():
            with self._data_lock:
                self._data.refresh()
            if msg:
                self._display.show_message(msg)
        threading.Thread(target=_do, daemon=True).start()


# ── Einstiegspunkt ───────────────────────────────────────────

if __name__ == '__main__':
    App().run()
