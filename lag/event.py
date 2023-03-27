from dataclasses import dataclass, field
import os
from pathlib import Path
import time
from typing import BinaryIO, Optional
import re
import struct
import subprocess


PROC_DEVICES = Path("/proc/bus/input/devices")

DEVICE_PATTERN = re.compile(
    r"""
    I:\s+Bus=([0-9a-f]{4})\s+Vendor=([0-9a-f]{4})\s+Product=([0-9a-f]{4}).+?
    N:\s+Name="([^"]+?)".+?
    H:\s+Handlers=([^\n]+)
    """,
    re.DOTALL | re.VERBOSE | re.IGNORECASE,
)

EVENT_STRUCT = struct.Struct("llHHI")

# https://www.kernel.org/doc/Documentation/input/event-codes.txt
EV_SYN = 0x00
EV_KEY = 0x01
EV_REL = 0x02
EV_ABS = 0x03
EV_MSC = 0x04

# include/uapi/linux/input.h
BUS_USB = 0x03
BUS_BLUETOOTH = 0x05


@dataclass
class Event:
    source: str
    timestamp: float
    event_type: int
    code: int
    value: int

    @property
    def is_key_press(self):
        return self.event_type == EV_KEY and self.value


class EventFile:
    def __init__(self, name: str, event_file: BinaryIO):
        self.name = name
        self._file = event_file

        os.set_blocking(self._file.fileno(), False)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._file.close()

    def read_event(self, timeout=3) -> Event:
        start = time.time()

        while time.time() - start <= timeout:
            data = self._file.read(EVENT_STRUCT.size)
            if data:
                tv_sec, tv_usec, event_type, code, value = EVENT_STRUCT.unpack(data)

                return Event(
                    source=self.name,
                    timestamp=tv_sec + tv_usec / 1e6,
                    event_type=event_type,
                    code=code,
                    value=value,
                )

        raise TimeoutError()


@dataclass
class EventDevice:
    bus: int = 0
    vendor: str = ""
    product: str = ""
    name: str = ""
    unique_id: str = ""
    handlers: list[str] = field(default_factory=list)

    @property
    def path(self) -> Optional[Path]:
        try:
            event = next(x for x in self.handlers if x.startswith("event"))
            return Path("/dev/input") / event
        except StopIteration:
            return None

    @property
    def id(self) -> str:
        return f"{self.vendor}:{self.product}"

    def open(self) -> EventFile:
        return EventFile(self.name, self.path.open("rb"))

    def get_interval(self) -> Optional[int]:
        if self.bus == BUS_USB:
            return self._get_usb_interval()
        if self.bus == BUS_BLUETOOTH:
            return self._get_bluetooth_interval()
        return None

    def _get_usb_interval(self):
        try:
            text = subprocess.check_output(
                ["lsusb", "-vd", self.id], encoding="utf-8", stderr=subprocess.STDOUT
            )

            for line in text.splitlines():
                key, _, value = line.strip().partition(" ")
                if key == "bInterval":
                    return int(value)

        except subprocess.CalledProcessError:
            return None

    def _get_bluetooth_interval(self):
        return None


def get_devices(device_type="kbd"):
    try:
        devices = PROC_DEVICES.read_text()
    except FileNotFoundError:
        return

    def split_devices():
        lines = []
        for line in devices.splitlines():
            if line:
                lines.append(line)
            else:
                yield lines
                lines.clear()

    def parse_device(lines: list[str]):
        device = EventDevice()

        for line in lines:
            key, _, data = line.partition(": ")

            if key == "I":
                match = re.search("Bus=([0-9a-f]{4})", data)
                if match:
                    device.bus = int(match.group(1), 16)

                match = re.search("Vendor=([0-9a-f]{4})", data)
                if match:
                    device.vendor = match.group(1)

                match = re.search("Product=([0-9a-f]{4})", data)
                if match:
                    device.product = match.group(1)

            elif key == "N":
                match = re.search('Name="([^"]+?)"', data)
                if match:
                    device.name = match.group(1).strip()

            elif key == "U":
                match = re.search("Uniq=(.+)", data)
                if match:
                    device.unique_id = match.group(1).strip()

            elif key == "H":
                match = re.search("Handlers=(.+)", data)
                if match:
                    device.handlers = match.group(1).strip().split()

        return device

    for lines in split_devices():
        device = parse_device(lines)
        if device_type in device.handlers:
            yield device
