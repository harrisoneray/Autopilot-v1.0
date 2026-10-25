"""Standalone GPS readout; one process owns the GNSS and the LCD."""
import logging
import time
from typing import Optional, Protocol, Sequence

from usv.hal.gnss import UsbGnss
from usv.hal.interfaces import NavigationFix


class Display(Protocol):
    def show(self, lines: Sequence[str]) -> None:
        ...

    def close(self) -> None:
        ...


def screen(fix: Optional[NavigationFix], elapsed: float, tick: int,
           status: str = "GPS: acquiring...") -> tuple[str, ...]:
    seconds = max(0, int(elapsed))
    heartbeat = "|/-\\"[tick % 4]
    footer = f"{heartbeat} Up {seconds // 3600:02}:{seconds // 60 % 60:02}:{seconds % 60:02}"
    if fix is None:
        return ("USV GPS", status, "Waiting for position", footer)
    return (
        "USV GPS: FIX",
        f"Lat {fix.latitude_deg:+.6f}",
        f"Lon {fix.longitude_deg:+.6f}",
        footer,
    )


def run_display(display: Display, port: str, baudrate: int, seconds: float = 0) -> None:
    """Heartbeat follows completed read windows; frozen I/O freezes the marker.

    No old position is retained after an unusable read. Retry serial failures
    every three seconds while continuing display updates. No propulsion exists.
    """
    device = None
    started = time.monotonic()
    retry_at = 0.0
    tick = 0
    try:
        display.show(("USV GPS starting", "LCD: ready", "GPS: initializing", "Please wait..."))
        time.sleep(1)
        while seconds == 0 or time.monotonic() - started < seconds:
            fix = None
            status = "GPS: disconnected"
            if device is None and time.monotonic() >= retry_at:
                try:
                    device = UsbGnss(port, baudrate)
                except OSError as error:
                    logging.warning("GNSS open failed: %s", error)
                    retry_at = time.monotonic() + 3
            if device is not None:
                try:
                    fix = device.read()
                    status = "GPS: acquiring..."
                except OSError as error:
                    logging.warning("GNSS read failed: %s", error)
                    try:
                        device.close()
                    finally:
                        device = None
                        retry_at = time.monotonic() + 3
            display.show(screen(fix, time.monotonic() - started, tick, status))
            tick += 1
            time.sleep(0.2)
    finally:
        try:
            if device is not None:
                device.close()
        finally:
            try:
                display.show(("USV GPS STOPPED", "Readout is inactive", "", "Heartbeat stopped"))
            finally:
                display.close()


def test_display(display: Display, seconds: float = 20) -> None:
    try:
        started = time.monotonic()
        tick = 0
        while time.monotonic() - started < seconds:
            display.show((
                "USV LCD TEST " + "|/-\\"[tick % 4],
                "Row 2: ABCDEFGHIJKLM",
                "Row 3: 0123456789",
                f"Row 4: tick {tick:04d}",
            ))
            tick += 1
            time.sleep(0.5)
    finally:
        try:
            display.show(("LCD TEST COMPLETE", "All four rows shown", "", "Test stopped"))
        finally:
            display.close()
