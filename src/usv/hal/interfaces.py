"""Contracts shared by application logic and hardware adapters."""
from dataclasses import dataclass
from math import isfinite
from typing import Optional, Protocol


@dataclass(frozen=True)
class NavigationFix:
    """WGS84 degrees; true heading clockwise from north, if available.

    timestamp_s is local time.monotonic() seconds, not UTC.
    """
    latitude_deg: float
    longitude_deg: float
    heading_deg: Optional[float]
    timestamp_s: float

    def __post_init__(self) -> None:
        if not isfinite(self.latitude_deg) or not -90 <= self.latitude_deg <= 90:
            raise ValueError("invalid latitude")
        if not isfinite(self.longitude_deg) or not -180 <= self.longitude_deg <= 180:
            raise ValueError("invalid longitude")
        if self.heading_deg is not None and (
            not isfinite(self.heading_deg) or not 0 <= self.heading_deg < 360
        ):
            raise ValueError("invalid heading")
        if not isfinite(self.timestamp_s) or self.timestamp_s < 0:
            raise ValueError("invalid timestamp")


class NavigationSensor(Protocol):
    def read(self) -> Optional[NavigationFix]:
        """Return latest valid fix or None; raise OSError for I/O failure."""
        ...

    def close(self) -> None:
        """Release resources; safe to repeat."""
        ...


class Propulsion(Protocol):
    """Starts disarmed. Real adapters need bounded I/O and a watchdog."""
    def arm(self) -> None:
        """Explicitly enable output at neutral."""
        ...

    def set_thrust(self, port: float, starboard: float) -> None:
        """Require arming; normalized [-1, 1], zero neutral.

        Invalid commands must neutralize and disarm. I/O errors raise OSError.
        """
        ...

    def stop(self) -> None:
        """Neutralize and disarm; safe to repeat."""
        ...

    def close(self) -> None:
        """Stop and permanently release resources; safe to repeat."""
        ...
