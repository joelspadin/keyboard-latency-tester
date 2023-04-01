import argparse
from contextlib import contextmanager
from pathlib import Path
import sys
import time
from typing import Iterable, Optional
from gpiozero import LED
from tabulate import tabulate

from . import get_keyboards, learn_trigger_key, run_test
from .event import BUS_BLUETOOTH, BUS_USB, EventDevice

DEFAULT_PIN = "GPIO21"
DEFAULT_N = 100
DEFAULT_TMIN = 50
DEFAULT_TMAX = 1000


@contextmanager
def outfile(path: Optional[Path]):
    if path is None:
        yield sys.stdout
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            yield f


def get_interface(device: EventDevice):
    if device.bus == BUS_USB:
        return f"USB ({1000 // device.get_interval()} Hz)"

    if device.bus == BUS_BLUETOOTH:
        return "Bluetooth"

    return ""


def list_keyboards(devices: Iterable[EventDevice]):
    headers = ["Name", "ID", "Path", "Interface"]
    table = [(dev.name, dev.id, dev.path, get_interface(dev)) for dev in devices]

    print(tabulate(table, headers, showindex=True))


def scan_keyboards(gpio: LED, devices: Iterable[EventDevice]):
    for i, dev in enumerate(devices):
        print(f"Testing {dev.name}...")

        gpio.off()
        time.sleep(0.5)

        try:
            key_code = learn_trigger_key(gpio, dev, timeout=1)
            print(f"Keyboard responded with key code {key_code}. Run test with")
            print(f"--index={i}")
            return
        except TimeoutError:
            pass

    print("Timed out waiting for triggered key")


def select_keyboard(devices: list[EventDevice], args: argparse.Namespace):
    def iequals(a, b):
        return a.casefold() == b.casefold()

    if args.index is not None:
        try:
            return devices[args.index]
        except IndexError:
            print("Invalid index", args.index)
            return None

    if args.id:
        try:
            return next(dev for dev in devices if iequals(dev.id, args.id))
        except StopIteration:
            print("No keyboard with ID", args.id)
            return None

    if args.name:
        try:
            return next(dev for dev in devices if iequals(dev.name, args.name))
        except StopIteration:
            print("No keyboard with name", args.name)
            return None

    return devices[0]


def main():
    parser = argparse.ArgumentParser(description="Test keyboard latency")
    parser.add_argument("--list", action="store_true", help="list attached keyboards")
    parser.add_argument(
        "--scan",
        action="store_true",
        help="scan to find which keyboard is instrumented",
    )

    parser.add_argument(
        "--gpio",
        "-g",
        default=DEFAULT_PIN,
        help=f"trigger GPIO (default: {DEFAULT_PIN})",
    )
    parser.add_argument(
        "-n",
        type=int,
        default=DEFAULT_N,
        help=f"number of iterations (default: {DEFAULT_N})",
    )
    parser.add_argument(
        "--tmin",
        type=int,
        default=DEFAULT_TMIN,
        help=f"minimum delay in milliseconds (default: {DEFAULT_TMIN})",
    )
    parser.add_argument(
        "--tmax",
        type=int,
        default=DEFAULT_TMAX,
        help=f"maximum delay in milliseconds (default: {DEFAULT_TMAX})",
    )
    parser.add_argument("--out", "-o", type=Path, help="output CSV path")

    dev_select = parser.add_mutually_exclusive_group()
    dev_select.add_argument(
        "--index", "-i", type=int, help="use device at index from --list"
    )
    dev_select.add_argument(
        "--id", "-d", help="use device with matching ID (vendor:product)"
    )
    dev_select.add_argument("--name", help="use keyboard with matching name")

    args = parser.parse_args()

    devices = get_keyboards()
    gpio = LED(args.gpio)

    if not devices:
        print("No keyboards detected")
        return

    if args.list:
        list_keyboards(devices)
        return

    if args.scan:
        scan_keyboards(gpio, devices)
        return

    device = select_keyboard(devices, args)
    if device is None:
        return

    gpio.off()
    time.sleep(0.5)

    try:
        key_code = learn_trigger_key(gpio, device)
        time.sleep(0.5)

        min_delay = args.tmin / 1000
        max_delay = args.tmax / 1000
        iterations = args.n

        with outfile(args.out) as f:
            print("Running latency test with")
            print(f"  trigger    = {gpio.pin}")
            print(f"  device     = {device.name}")
            print(f"  key code   = {key_code}")
            print(f"  iterations = {iterations}")
            print(f"  min delay  = {min_delay * 1000:.0f} ms")
            print(f"  max delay  = {max_delay * 1000:.0f} ms")

            if f.isatty():
                print()

            print("Latency (ms), +/- (ms)", file=f)

            results = run_test(
                gpio=gpio,
                device=device,
                key_code=key_code,
                min_delay=min_delay,
                max_delay=max_delay,
                iterations=iterations,
            )

            for elapsed, error in results:
                print(
                    f"{elapsed * 1000:3.2f}, {error / 2 * 1000:3.2f}",
                    file=f,
                    flush=True,
                )

    except TimeoutError:
        print("Timed out waiting for triggered key")


if __name__ == "__main__":
    main()
