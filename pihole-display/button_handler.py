"""Handle GPIO button input and map presses to UI button events."""

# ============================================================
# button_handler.py — GPIO Buttons via gpiod v2
# BeagleBone Black: gpiochip2, Pins 2/3/4/5
# Alle Buttons: Active-LOW (4.7K Pull-up auf Platine)
# ============================================================

import threading
import time
import logging
from enum import Enum, auto
from typing import Callable, Optional

try:
    import gpiod  # type: ignore[import-not-found]
    from gpiod.line import Direction, Value  # type: ignore[import-not-found]
except ImportError:
    gpiod = None
    Direction = None
    Value = None

import config

log = logging.getLogger(__name__)


class ButtonEvent(Enum):
    """Logical button events for short and long presses."""

    UP_SHORT = auto()   # ^ kurz
    UP_LONG = auto()   # ^ lang
    DOWN_SHORT = auto()   # v kurz
    DOWN_LONG = auto()   # v lang
    OK_SHORT = auto()   # # kurz
    OK_LONG = auto()   # # lang
    BACK_SHORT = auto()   # * kurz
    BACK_LONG = auto()   # * lang  → Home


class ButtonHandler:
    """
    Liest 4 GPIO-Tasten via gpiod v2 (Debian 13).
    Erkennt kurzen und langen Druck.
    Ruft callback(event: ButtonEvent) auf.
    """

    _PINS = {
        'up':   config.BTN_UP,
        'down': config.BTN_DOWN,
        'ok':   config.BTN_OK,
        'back': config.BTN_BACK,
    }

    def __init__(self, callback: Callable[[ButtonEvent], None]):
        self._callback = callback
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._request = None

    def start(self):
        """Start the polling thread for button events."""
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        log.info('Button-Handler gestartet')

    def stop(self):
        """Stop polling and release any claimed GPIO resources."""
        self._running = False
        if self._request:
            try:
                self._request.release()
            except (AttributeError, OSError, RuntimeError):
                pass
        if self._thread:
            self._thread.join(timeout=2)
        log.info('Button-Handler gestoppt')

    def _poll_loop(self):
        try:
            self._poll_with_gpiod()
        except (ImportError, OSError, RuntimeError) as e:
            log.error('gpiod Fehler: %s — Fallback auf sysfs', e)
            self._poll_with_sysfs()

    # ── gpiod v2 ─────────────────────────────────────────────

    def _poll_with_gpiod(self):  # pylint: disable=too-many-locals
        if gpiod is None or Direction is None or Value is None:
            raise ImportError('gpiod nicht verfügbar')

        pins = list(self._PINS.values())
        names = list(self._PINS.keys())

        settings = gpiod.LineSettings(direction=Direction.INPUT)
        config_map = {p: settings for p in pins}

        chip = gpiod.Chip(config.GPIO_CHIP)
        self._request = chip.request_lines(
            consumer='pihole-display',
            config=config_map
        )

        # Zustand: {pin: (pressed_since_ts or None)}
        pressed_since = {p: None for p in pins}
        # HIGH = nicht gedrückt
        last_state = {p: Value.ACTIVE for p in pins}
        debounce_end = {p: 0.0 for p in pins}

        log.info('gpiod Polling aktiv auf %s, Pins %s', config.GPIO_CHIP, pins)

        while self._running:
            now = time.monotonic()
            vals = self._request.get_values(pins)

            for i, pin in enumerate(pins):
                val = vals[i]
                pressed = val == Value.INACTIVE   # LOW = gedrückt
                was_pressed = last_state[pin] == Value.INACTIVE
                self._process_button_transition(
                    key=pin,
                    name=names[i],
                    pressed=pressed,
                    was_pressed=was_pressed,
                    now=now,
                    debounce_end=debounce_end,
                    last_state=last_state,
                    new_state=val,
                    pressed_since=pressed_since,
                )

            time.sleep(0.05)   # 50ms Polling

        self._request.release()

    # ── sysfs Fallback ───────────────────────────────────────

    def _poll_with_sysfs(self):
        """Fallback: /sys/class/gpio (deprecated aber universell)."""
        # GPIO2_x → GPIO-Nummer = 64 + offset
        gpio_nums = {
            name: 64 + pin
            for name, pin in self._PINS.items()
        }
        self._export_gpios(gpio_nums)

        pressed_since = {n: None for n in gpio_nums}
        last_state = {n: 1 for n in gpio_nums}
        debounce_end = {n: 0.0 for n in gpio_nums}

        log.info('sysfs GPIO Fallback aktiv')

        while self._running:
            now = time.monotonic()
            for name, num in gpio_nums.items():
                try:
                    with open(
                        f'/sys/class/gpio/gpio{num}/value',
                        encoding='utf-8',
                    ) as f:
                        val = int(f.read().strip())
                except (OSError, ValueError):
                    continue

                pressed = val == 0
                was_pressed = last_state[name] == 0
                self._process_button_transition(
                    key=name,
                    name=name,
                    pressed=pressed,
                    was_pressed=was_pressed,
                    now=now,
                    debounce_end=debounce_end,
                    last_state=last_state,
                    new_state=val,
                    pressed_since=pressed_since,
                )

            time.sleep(0.05)

    def _export_gpios(self, gpio_nums: dict):
        for _, num in gpio_nums.items():
            path = f'/sys/class/gpio/gpio{num}'
            if not __import__('os').path.exists(path):
                try:
                    with open(
                        '/sys/class/gpio/export',
                        'w',
                        encoding='utf-8',
                    ) as f:
                        f.write(str(num))
                    time.sleep(0.1)
                    with open(f'{path}/direction', 'w', encoding='utf-8') as f:
                        f.write('in')
                except OSError as e:
                    log.warning('GPIO %d export fehlgeschlagen: %s', num, e)

    # ── Hilfsfunktionen ──────────────────────────────────────

    def _process_button_transition(
        self,
        key,
        name: str,
        pressed: bool,
        was_pressed: bool,
        now: float,
        debounce_end: dict,
        last_state: dict,
        new_state,
        pressed_since: dict,
    ):  # pylint: disable=too-many-arguments,too-many-positional-arguments
        """Apply debounce and emit short/long press events on release edges."""
        if pressed == was_pressed:
            return
        if now < debounce_end[key]:
            return

        debounce_end[key] = now + config.DEBOUNCE_MS / 1000.0
        last_state[key] = new_state

        if pressed:
            pressed_since[key] = now
            return

        started = pressed_since.get(key)
        if started is None:
            return

        held = now - started
        pressed_since[key] = None
        event = self._make_event(name, held >= config.LONG_PRESS_MS / 1000.0)
        if event:
            self._dispatch(event)

    def _make_event(self, name: str, long: bool) -> Optional[ButtonEvent]:
        mapping = {
            ('up',   False): ButtonEvent.UP_SHORT,
            ('up',   True):  ButtonEvent.UP_LONG,
            ('down', False): ButtonEvent.DOWN_SHORT,
            ('down', True):  ButtonEvent.DOWN_LONG,
            ('ok',   False): ButtonEvent.OK_SHORT,
            ('ok',   True):  ButtonEvent.OK_LONG,
            ('back', False): ButtonEvent.BACK_SHORT,
            ('back', True):  ButtonEvent.BACK_LONG,
        }
        return mapping.get((name, long))

    def _dispatch(self, event: ButtonEvent):
        log.debug('Button-Event: %s', event.name)
        try:
            self._callback(event)
        except RuntimeError as e:
            log.error('Callback-Fehler: %s', e)
