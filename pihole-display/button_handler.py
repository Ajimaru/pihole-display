"""Handle GPIO button input and map presses to UI button events."""

# ============================================================
# button_handler.py — GPIO buttons via gpiod v2
# BeagleBone Black: gpiochip1, pins 2/3/4/5
# All buttons: active-low (4.7K pull-up on board)
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

    UP_SHORT = auto()   # ^ short
    UP_LONG = auto()   # ^ long
    DOWN_SHORT = auto()   # v short
    DOWN_LONG = auto()   # v long
    OK_SHORT = auto()   # # short
    OK_LONG = auto()   # # long
    BACK_SHORT = auto()   # * short
    BACK_LONG = auto()   # * long -> Home
    BACK_HOLD = auto()   # * held for HOLD_MS -> unlock screen


class ButtonHandler:
    """
    Reads 4 GPIO buttons via gpiod v2 (Debian 13).
    Detects short and long presses.
    Calls callback(event: ButtonEvent).
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
        log.info('Button handler started')

    def stop(self):
        """Stop polling and release any claimed GPIO resources."""
        self._running = False
        # The poll thread releases its lines on exit; releasing them here
        # while it still polls would make it fail on the released request.
        if self._thread:
            self._thread.join(timeout=2)
        if self._request and not (self._thread and self._thread.is_alive()):
            try:
                self._request.release()
            except Exception:  # pylint: disable=broad-except
                pass  # already released
            self._request = None
        log.info('Button handler stopped')

    def _poll_loop(self):
        try:
            self._poll_with_gpiod()
        except (ImportError, OSError, RuntimeError) as e:
            log.error('gpiod error: %s - falling back to sysfs', e)
            self._poll_with_sysfs()

    # ── gpiod v2 ─────────────────────────────────────────────

    def _poll_with_gpiod(self):  # pylint: disable=too-many-locals
        if gpiod is None or Direction is None or Value is None:
            raise ImportError('gpiod not available')

        pins = list(self._PINS.values())
        names = list(self._PINS.keys())

        settings = gpiod.LineSettings(direction=Direction.INPUT)
        config_map = {p: settings for p in pins}

        chip = gpiod.Chip(config.GPIO_CHIP)
        self._request = chip.request_lines(
            consumer='pihole-display',
            config=config_map
        )

        log.info('gpiod polling active on %s, pins %s', config.GPIO_CHIP, pins)

        try:
            self._poll_gpiod_lines(pins, names)
        finally:
            self._request.release()
            self._request = None

    def _poll_gpiod_lines(self, pins, names):
        """Poll the requested gpiod lines until the handler is stopped."""
        # State: {pin: (pressed_since_ts or None)}
        pressed_since = {p: None for p in pins}
        # HIGH = not pressed
        last_state = {p: Value.ACTIVE for p in pins}
        debounce_end = {p: 0.0 for p in pins}
        hold_fired = {p: False for p in pins}

        while self._running:
            now = time.monotonic()
            vals = self._request.get_values(pins)

            for i, pin in enumerate(pins):
                val = vals[i]
                pressed = val == Value.INACTIVE   # LOW = pressed
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
                    hold_fired=hold_fired,
                )
                self._check_hold(pin, names[i], now, pressed_since, hold_fired)

            time.sleep(0.05)   # 50ms polling

    # ── sysfs Fallback ───────────────────────────────────────

    def _poll_with_sysfs(self):
        """Fallback: /sys/class/gpio (deprecated but universal)."""
        # GPIO2_x -> GPIO number = 64 + offset
        gpio_nums = {
            name: 64 + pin
            for name, pin in self._PINS.items()
        }
        self._export_gpios(gpio_nums)

        pressed_since = {n: None for n in gpio_nums}
        last_state = {n: 1 for n in gpio_nums}
        debounce_end = {n: 0.0 for n in gpio_nums}
        hold_fired = {n: False for n in gpio_nums}

        log.info('sysfs GPIO fallback active')

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
                    hold_fired=hold_fired,
                )
                self._check_hold(name, name, now, pressed_since, hold_fired)

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
                    log.warning('GPIO %d export failed: %s', num, e)

    # ── Helper functions ─────────────────────────────────────

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
        hold_fired: dict,
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
        if hold_fired[key]:
            # The hold event already fired while the button was down
            hold_fired[key] = False
            return
        kind = 'long' if held >= config.LONG_PRESS_MS / 1000.0 else 'short'
        event = self._make_event(name, kind)
        if event:
            self._dispatch(event)

    def _check_hold(
        self, key, name: str, now: float, pressed_since: dict,
        hold_fired: dict,
    ):  # pylint: disable=too-many-arguments,too-many-positional-arguments
        """Emit a hold event once a button has been down for HOLD_MS."""
        started = pressed_since.get(key)
        if started is None or hold_fired[key]:
            return
        if now - started >= config.HOLD_MS / 1000.0:
            hold_fired[key] = True
            event = self._make_event(name, 'hold')
            if event:
                self._dispatch(event)

    def _make_event(self, name: str, kind: str) -> Optional[ButtonEvent]:
        mapping = {
            ('up',   'short'): ButtonEvent.UP_SHORT,
            ('up',   'long'):  ButtonEvent.UP_LONG,
            ('down', 'short'): ButtonEvent.DOWN_SHORT,
            ('down', 'long'):  ButtonEvent.DOWN_LONG,
            ('ok',   'short'): ButtonEvent.OK_SHORT,
            ('ok',   'long'):  ButtonEvent.OK_LONG,
            ('back', 'short'): ButtonEvent.BACK_SHORT,
            ('back', 'long'):  ButtonEvent.BACK_LONG,
            ('back', 'hold'):  ButtonEvent.BACK_HOLD,
        }
        return mapping.get((name, kind))

    def _dispatch(self, event: ButtonEvent):
        log.debug('Button-Event: %s', event.name)
        try:
            self._callback(event)
        except RuntimeError as e:
            log.error('Callback error: %s', e)
