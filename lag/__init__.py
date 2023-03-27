from contextlib import contextmanager
import random
import time
from typing import Optional
from gpiozero import LED

from .event import EventDevice, get_devices


@contextmanager
def trigger(gpio: LED):
    """
    Context manager which set a GPIO on for context and then back off when it
    finishes.

    Returns (start, error) where "start" is the timestamp in seconds at which
    the GPIO was set to on, and "error" is the time in seconds that it took to
    enable the GPIO.
    """
    start1 = time.time()
    gpio.on()
    start2 = time.time()

    start = (start1 + start2) / 2
    error = start2 - start1

    try:
        yield start, error
    finally:
        gpio.off()


def get_keyboards() -> list[EventDevice]:
    """
    Get all connected keyboard devices
    """
    return [dev for dev in get_devices() if dev.vendor != "0000"]


def get_delays(min_delay: float, max_delay: float, count: int):
    """
    Get list of "count" values evenly distributed over [min_delay, max_delay]
    and then randomly shuffled.
    """
    if count <= 1:
        return [min_delay]

    delta = max_delay - min_delay

    def rescale(x: int):
        return min_delay + delta * (x / (count - 1))

    delays = [rescale(x) for x in range(count)]
    random.shuffle(delays)
    return delays


def learn_trigger_key(gpio: LED, device: EventDevice, timeout=3) -> int:
    """
    Trigger a key press and return the resulting key code.
    """
    with device.open() as f, trigger(gpio):
        while True:
            event = f.read_event(timeout)
            if event.is_key_press:
                return event.code


def run_test(
    gpio: LED,
    device: EventDevice,
    key_code: Optional[int] = None,
    min_delay=0.05,
    max_delay=1,
    iterations=100,
    timeout=3,
):
    """
    Run a latency test. Returns an iterable of (latency, error) values, where
    "latency" is the time in seconds it took the keyboard to respond, and
    "error" is the possible error in that value due to uncertainty about when
    the trigger GPIO was enabled.

    :param gpio: Trigger GPIO
    :param device: Input device to test
    :param key_code: Key code to watch for. If None, this will trigger a key once
        before starting tests to learn the triggered key code.
    :param min_delay: Minimum delay between tests in seconds
    :param max_delay: Maximum delay between tests in seconds
    :param iterations: Number of tests
    :param timeout: TimeoutError is thrown if the device does not respond within
        this time in seconds
    """

    if key_code is None:
        key_code = learn_trigger_key(gpio, device)
        time.sleep(0.5)

    with device.open() as f:
        for delay in get_delays(min_delay, max_delay, iterations):
            time.sleep(delay)

            with trigger(gpio) as (start, error):
                while True:
                    event = f.read_event(timeout)
                    if event.is_key_press and event.code == key_code:
                        break

                elapsed = event.timestamp - start
                if elapsed < 0:
                    raise Exception(
                        "Keyboard sent a key before it was triggered. "
                        "Is your trigger set up properly?"
                    )

                yield elapsed, error
