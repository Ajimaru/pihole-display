#!/usr/bin/env python3
"""Main runtime loop for pihole-display UI and button interaction."""

# ============================================================
# main.py — pihole-display main program
# BeagleBone Black + SSD1315 OLED + 4 buttons
#
# Buttons (display mounted rotated, see config.py):
#   K2 (^) = previous screen / menu up
#   K1 (v) = next screen     / menu down
#   K3 (#) = action / confirm
#   K4 (*) = back / long = home, held 5s = wake locked display
# ============================================================

import json
import logging
import os
import signal
import threading
import time
import subprocess
from functools import partial

import config
from data import DataCache
from display_manager import DisplayManager, Screen, UIMode
from button_handler import ButtonHandler, ButtonEvent
from version import __version__

# ── Logging ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger('main')

# `pihole -up` compiles FTL on slow hardware; the BBB needs room.
UPDATE_TIMEOUT = 1800


# ── Application ──────────────────────────────────────────────

class App:  # pylint: disable=too-few-public-methods
    """Wire data, display, and button components into one application."""

    def __init__(self):
        self._data = DataCache()
        self._display = DisplayManager(self._data)
        self._buttons = ButtonHandler(self._on_button)
        self._running = False
        self._data_lock = threading.Lock()
        # _on_button is called from the GPIO thread and from the web
        # server's request threads, and it mutates display state.
        self._input_lock = threading.Lock()
        self._screen_lock = self._load_state().get('screen_lock', False)
        self._web = self._setup_web()

    def _setup_web(self):
        """Create the web server, or None when it is disabled or broken."""
        if not getattr(config, 'WEB_ENABLED', False):
            return None
        try:
            # Imported here so a disabled web UI costs nothing at all.
            from web_auth import AuthManager      # pylint: disable=C0415
            from web_server import WebServer      # pylint: disable=C0415

            auth = AuthManager(config.WEB_AUTH_FILE)
            if auth.is_default_password():
                log.warning(
                    'Web UI still uses the default password - change it at '
                    'http://<host>:%d/', config.WEB_PORT,
                )
            return WebServer(self._display, self._on_button, auth)
        except Exception as e:  # pylint: disable=broad-except
            log.error('Web server setup failed: %s', e)
            return None

    # ── Persistent state ─────────────────────────────────────

    @staticmethod
    def _load_state() -> dict:
        try:
            with open(config.STATE_FILE, encoding='utf-8') as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def _save_state(self):
        try:
            os.makedirs(os.path.dirname(config.STATE_FILE), exist_ok=True)
            with open(config.STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump({'screen_lock': self._screen_lock}, f)
        except OSError as e:
            log.error('Saving state failed: %s', e)

    # ── Start / Stop ─────────────────────────────────────────

    def run(self):
        """Start the app loop, refresh data, and update display continuously.

        The loop also handles periodic data refresh and clean shutdown.
        """
        log.info('pihole-display v%s starting', __version__)
        self._running = True

        # Initial data fetch
        self._display.show_splash()
        self._data.refresh()

        self._buttons.start()

        if self._web:
            try:
                self._web.start()
            except OSError as e:
                log.error('Web server could not start: %s', e)
                self._web = None

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
        # Stop serving before the display goes away, or an in-flight
        # request could touch a device that is already released.
        if self._web:
            self._web.stop()
        self._display.cleanup()
        log.info('Stopped')

    # ── Button handler ───────────────────────────────────────

    def _on_button(self, event: ButtonEvent):
        """Called from the button thread and from web requests - be fast."""
        with self._input_lock:
            self._dispatch_button(event)

    def _dispatch_button(self, event: ButtonEvent):
        mode = self._display.mode

        # Wake display on every button press, or only on holding * while
        # the screen lock is enabled
        if mode == UIMode.SLEEP:
            if not self._screen_lock or event == ButtonEvent.BACK_HOLD:
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
        elif screen == Screen.SYSTEM:
            self._menu_system()
        # NETWORK has no menu

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
        items = []
        if self._data.pihole.updates:
            # Only offered when something is actually out of date
            items.append(('Update Pi-hole', partial(
                self._confirm, 'Update?', self._pihole_update,
            )))
        items += [
            ('Restart Pi-hole',  self._pihole_restart),
            ('Restart Unbound',  self._unbound_restart),
            ('Restart all',      self._restart_all),
            (
                'Refresh data',
                lambda: self._trigger_refresh('Refreshing...'),
            ),
        ]
        self._display.show_menu(items)

    def _menu_system(self):
        lock = 'on' if self._screen_lock else 'off'
        lock_title = 'Lock off?' if self._screen_lock else 'Lock on?'
        self._display.show_menu([
            ('Reboot', partial(
                self._confirm, 'Reboot?', partial(self._power, 'reboot'),
            )),
            ('Shutdown', partial(
                self._confirm, 'Shutdown?', partial(self._power, 'poweroff'),
            )),
            (f'Screen lock: {lock}', partial(
                self._confirm, lock_title, self._toggle_screen_lock,
            )),
        ])

    def _confirm(self, title: str, action):
        # 'No' comes first so it is preselected
        self._display.show_menu([
            ('No',  lambda: None),
            ('Yes', action),
        ], title=title)

    # ── Actions ──────────────────────────────────────────────

    def _toggle_screen_lock(self):
        self._screen_lock = not self._screen_lock
        self._save_state()
        self._display.show_message(
            'Screen lock\nON\n(hold * 5s)' if self._screen_lock
            else 'Screen lock\nOFF',
        )

    def _power(self, command: str):
        """Reboot or power off the system via systemctl."""
        log.info('System %s requested via buttons', command)
        self._display.show_message(
            'Rebooting...' if command == 'reboot' else 'Shutting\ndown...',
            duration=60,
        )
        result = subprocess.run(
            ['systemctl', command],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if result.returncode != 0:
            log.error('systemctl %s failed: %s', command, result.stderr)
            self._display.show_message('Error!')

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

    def _pihole_update(self):
        """Run `pihole -up`, which stops FTL and interrupts DNS.

        Takes minutes and pulls from the network. The display is held
        awake throughout, because blanking mid-update leaves no sign of
        what is happening, and FTL is checked afterwards whatever the
        outcome: an update that dies between stopping and restarting it
        would otherwise leave the whole network without DNS.
        """
        log.info('Pi-hole update requested via menu')
        with self._display.keep_awake():
            self._run_pihole_update()
            self._ensure_ftl_running()
        self._data.invalidate_update_check()
        self._trigger_refresh()

    def _run_pihole_update(self):
        """Run the updater and report what the versions actually did.

        `pihole -up` exits 0 whether it upgraded anything, found nothing
        to do, or failed partway, so its return code says very little.
        What settles it is comparing the installed versions before and
        after.
        """
        before = self._data.installed_versions()
        self._display.show_message(
            'Updating\nPi-hole...\nDNS is down',
            duration=UPDATE_TIMEOUT,
        )
        try:
            result = subprocess.run(
                ['pihole', '-up'],
                capture_output=True,
                text=True,
                timeout=UPDATE_TIMEOUT,
                check=False,
            )
        except subprocess.TimeoutExpired:
            log.error('pihole -up timed out after %ds', UPDATE_TIMEOUT)
            self._display.show_message('Update\ntimed out!', duration=10)
            return
        except OSError as e:
            log.error('pihole -up failed to start: %s', e)
            self._display.show_message('Update\nfailed!', duration=10)
            return

        output = f'{result.stdout}\n{result.stderr}'
        # The updater rewrites /etc/pihole/versions as its last step, so
        # an interrupted run leaves it stale and the comparison would
        # miss an upgrade that did happen. Refresh it first.
        self._refresh_version_file()
        after = self._data.installed_versions()
        self._report_update(result.returncode, output, before, after)

    @staticmethod
    def _refresh_version_file():
        """Have Pi-hole rewrite /etc/pihole/versions."""
        try:
            subprocess.run(
                ['pihole', 'updatechecker'],
                capture_output=True,
                timeout=120,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as e:
            log.debug('updatechecker failed: %s', e)

    def _report_update(self, returncode, output, before, after):
        """Work out what the update did and say so."""
        changed = sorted(
            key.split('_')[0].title()
            for key in set(before) | set(after)
            if before.get(key) != after.get(key)
        )
        if changed:
            for key in sorted(set(before) | set(after)):
                if before.get(key) != after.get(key):
                    log.info(
                        'Pi-hole %s: %s -> %s', key.split('_')[0].lower(),
                        before.get(key, '?'), after.get(key, '?'),
                    )
            self._display.show_message(
                'Update OK\n' + ' '.join(changed), duration=8,
            )
            return

        # Nothing moved. Either there was nothing to do, or it broke.
        hard_fail = (
            returncode != 0
            or 'unable to open /etc/sudoers' in output
            or 'Operation not permitted' in output
        )
        if hard_fail:
            log.error(
                'pihole -up failed (rc=%d): %s',
                returncode, output.strip()[-300:],
            )
            self._display.show_message('Update\nfailed!', duration=10)
        elif 'Everything is up to date' in output:
            log.info('Pi-hole already up to date')
            self._display.show_message('Already\nup to date', duration=5)
        else:
            # Clean exit, no version moved, no "up to date" either.
            log.warning(
                'pihole -up changed nothing: %s', output.strip()[-300:],
            )
            self._display.show_message('No change', duration=8)

    def _ensure_ftl_running(self):
        """Start pihole-FTL if the update left it stopped.

        Without this a half-finished update takes DNS down for the whole
        network until somebody notices and starts it by hand.
        """
        active = subprocess.run(
            ['systemctl', 'is-active', '--quiet', 'pihole-FTL'],
            timeout=15,
            check=False,
        )
        if active.returncode == 0:
            return

        log.error('pihole-FTL is down after the update - starting it')
        self._display.show_message('Restarting\nPi-hole DNS...', duration=30)
        started = subprocess.run(
            ['systemctl', 'start', 'pihole-FTL'],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if started.returncode == 0:
            log.info('pihole-FTL started')
            self._display.show_message('DNS back up', duration=5)
        else:
            log.error('Starting pihole-FTL failed: %s', started.stderr.strip())
            self._display.show_message('DNS DOWN!\nCheck FTL', duration=60)

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
