"""USB NMEA receiver adapter. Dependencies load only when explicitly selected."""
import time
from typing import Optional

from usv.hal.interfaces import NavigationFix

DEFAULT_PORT = (
    "/dev/serial/by-id/"
    "usb-u-blox_AG_-_www.u-blox.com_u-blox_7_-_GPS_GNSS_Receiver-if00"
)


def parse_rmc(line: bytes) -> Optional[NavigationFix]:
    """Accept checksum-valid, active RMC positions; never infer hull heading."""
    import pynmea2

    try:
        message = pynmea2.parse(line.decode("ascii").strip(), check=True)
        if message.sentence_type != "RMC" or message.status != "A":
            return None
        if getattr(message, "mode_indicator", "") not in ("", "A", "D"):
            return None
        if not message.lat or not message.lon:
            return None
        if message.lat_dir not in ("N", "S") or message.lon_dir not in ("E", "W"):
            return None
        # Some parsers normalize out-of-range minutes; reject them first.
        for value in (message.lat, message.lon):
            if not 0 <= float(value) % 100 < 60 or float(value) < 0:
                return None
        return NavigationFix(message.latitude, message.longitude, None, time.monotonic())
    except (pynmea2.ParseError, UnicodeError, ValueError, TypeError, AttributeError):
        return None


class UsbGnss:
    """Bounded reads with no cached fix and no receiver configuration writes.

    read() consumes up to one second of input looking for RMC. None means no
    usable position during that interval, including silence or corrupt input.
    Receipt timestamps do not prove receiver measurement freshness.
    """

    def __init__(self, port: str = DEFAULT_PORT, baudrate: int = 9600) -> None:
        import serial

        self._serial = serial.Serial(
            port, baudrate=baudrate, timeout=0.2, exclusive=True
        )
        try:
            self._serial.reset_input_buffer()
        except BaseException:
            self._serial.close()
            raise
        self._pending = bytearray()
        self._closed = False

    def read(self) -> Optional[NavigationFix]:
        if self._closed:
            raise RuntimeError("GNSS is closed")
        deadline = time.monotonic() + 1.0
        for _ in range(64):
            if time.monotonic() >= deadline:
                break
            chunk = self._serial.read_until(b"\n", size=256)
            self._pending.extend(chunk)
            if len(self._pending) > 256:
                self._pending.clear()
                continue
            if not self._pending.endswith(b"\n"):
                continue
            line = bytes(self._pending)
            self._pending.clear()
            # Other sentence types do not represent a new RMC position.
            if line[:1] == b"$" and line[3:7] == b"RMC,":
                return parse_rmc(line)
        return None

    def close(self) -> None:
        if not self._closed:
            self._serial.close()
            self._closed = True
