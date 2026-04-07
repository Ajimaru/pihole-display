#!/usr/bin/env python3
"""Main runtime loop for pihole-display UI and button interaction."""

# ============================================================
# main.py — pihole-display Hauptprogramm
# BeagleBone Black + SSD1315 OLED + 4 Tasten
#
# Tasten:
#   K1 (^) = vorheriger Screen / Menü hoch
#   K2 (v) = nächster Screen   / Menü runter
#   K3 (#) = Aktion / Bestätigen
#   K4 (*) = Zurück / lang = Home
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


# ── Applikation ──────────────────────────────────────────────

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
        log.info('pihole-display startet')
        self._running = True

        # Erster Datenabruf
        self._display.show_message('Lade Daten...')
        self._data.refresh()

        self._buttons.start()

        # Signal-Handler
        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT,  self._shutdown)

        log.info('Hauptschleife aktiv')
        try:
            while self._running:
                # Daten bei Bedarf aktualisieren
                if self._data.needs_refresh():
                    with self._data_lock:
                        self._data.refresh()

                # Display rendern
                self._display.update()
                time.sleep(0.1)
        except (RuntimeError, OSError, ValueError) as e:
            log.error('Hauptschleife Fehler: %s', e)
        finally:
            self._cleanup()

    def _shutdown(self, *_):
        log.info('Beende...')
        self._running = False

    def _cleanup(self):
        self._buttons.stop()
        self._display.cleanup()
        log.info('Beendet')

    # ── Button-Handler ───────────────────────────────────────

    def _on_button(self, event: ButtonEvent):
        """Wird im Button-Thread aufgerufen — schnell halten!"""
        mode = self._display.mode

        # Display aufwecken bei jedem Druck
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
            # Screen-spezifische Aktion
            self._open_screen_menu(screen)

        elif event == ButtonEvent.UP_LONG:
            # Manueller Daten-Refresh
            self._trigger_refresh('Aktualisiere...')

        elif event == ButtonEvent.DOWN_LONG:
            # Display schlafen
            self._display.toggle_sleep()

    def _handle_menu_input(self, event: ButtonEvent):
        if event in (ButtonEvent.UP_SHORT, ButtonEvent.UP_LONG):
            self._display.menu_up()

        elif event in (ButtonEvent.DOWN_SHORT, ButtonEvent.DOWN_LONG):
            self._display.menu_down()

        elif event == ButtonEvent.OK_SHORT:
            action = self._display.menu_confirm()
            if action:
                # Aktion in eigenem Thread ausführen (kann länger dauern)
                threading.Thread(target=action, daemon=True).start()

        elif event in (ButtonEvent.BACK_SHORT, ButtonEvent.BACK_LONG):
            self._display.menu_cancel()

    # ── Screen-Menüs ─────────────────────────────────────────

    def _open_screen_menu(self, screen: Screen):
        if screen == Screen.PIHOLE:
            self._menu_pihole()
        elif screen == Screen.UNBOUND:
            self._menu_unbound()
        elif screen == Screen.STATUS:
            self._menu_status()
        # NETWORK und SYSTEM haben kein Menü

    def _menu_pihole(self):
        ph = self._data.pihole
        items = []

        if ph.enabled:
            for label, secs in config.PAUSE_OPTIONS:
                items.append((
                    f'Pause {label}',
                    partial(self._pihole_pause, secs)
                ))
            items.append(('Deaktivieren', self._pihole_disable))
        else:
            items.append(('Aktivieren', self._pihole_enable))

        items += [
            ('Gravity Update',  self._pihole_gravity),
            ('DNS Cache leeren', self._pihole_flush),
        ]
        self._display.show_menu(items)

    def _menu_unbound(self):
        self._display.show_menu([
            ('Cache leeren', self._unbound_flush),
            ('Neustart',     self._unbound_restart),
        ])

    def _menu_status(self):
        self._display.show_menu([
            ('Pi-hole neu starten',  self._pihole_restart),
            ('Unbound neu starten',  self._unbound_restart),
            ('Alles neu starten',    self._restart_all),
            (
                'Daten aktualisieren',
                lambda: self._trigger_refresh('Aktualisiere...'),
            ),
        ])

    # ── Aktionen ─────────────────────────────────────────────

    def _pihole_pause(self, seconds: int):
        mins = seconds // 60
        self._display.show_message(f'Pi-hole\nPause {mins} Min...')
        ok = self._data.pihole_set_blocking(False, seconds)
        self._display.show_message(
            'Pi-hole pausiert' if ok else 'Fehler!'
        )

    def _pihole_disable(self):
        self._display.show_message('Pi-hole\ndeaktiviere...')
        ok = self._data.pihole_set_blocking(False, 0)
        self._display.show_message(
            'Pi-hole AUS' if ok else 'Fehler!'
        )

    def _pihole_enable(self):
        self._display.show_message('Pi-hole\naktiviere...')
        ok = self._data.pihole_set_blocking(True)
        self._display.show_message(
            'Pi-hole AKTIV' if ok else 'Fehler!'
        )

    def _pihole_gravity(self):
        self._display.show_message(
            'Gravity\nUpdate...\n(dauert!)',
            duration=120,
        )
        ok = self._data.pihole_gravity_update()
        self._display.show_message(
            'Update OK' if ok else 'Fehler!'
        )
        self._trigger_refresh()

    def _pihole_flush(self):
        self._display.show_message('Flushe\nDNS Cache...')
        ok = self._data.pihole_flush()
        self._display.show_message(
            'Cache geleert' if ok else 'Fehler!'
        )

    def _pihole_restart(self):
        self._display.show_message('Pi-hole\nNeustart...')
        subprocess.run(
            ['pihole', 'restartdns'],
            capture_output=True,
            timeout=15,
            check=False,
        )
        self._trigger_refresh('Neustart OK')

    def _unbound_flush(self):
        self._display.show_message('Unbound\nCache leeren...')
        ok = self._data.unbound_flush()
        self._display.show_message(
            'Cache geleert' if ok else 'Fehler!'
        )

    def _unbound_restart(self):
        self._display.show_message('Unbound\nNeustart...')
        subprocess.run(
            ['systemctl', 'restart', 'unbound'],
            capture_output=True,
            timeout=15,
            check=False,
        )
        time.sleep(2)
        self._trigger_refresh('Neustart OK')

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
