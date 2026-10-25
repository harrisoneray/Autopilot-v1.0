"""In-memory adapters; no GPIO or device access."""
from math import isfinite
from typing import Optional
from usv.hal.interfaces import NavigationFix


class SimulatedNavigation:
    def __init__(self, fix: Optional[NavigationFix] = None) -> None:
        self.fix = fix
        self._closed = False

    def read(self) -> Optional[NavigationFix]:
        if self._closed:
            raise RuntimeError("sensor is closed")
        return self.fix

    def close(self) -> None:
        self._closed = True


class SimulatedPropulsion:
    def __init__(self) -> None:
        self._armed = False
        self._closed = False
        self._thrust = (0.0, 0.0)

    @property
    def armed(self) -> bool:
        return self._armed

    @property
    def thrust(self) -> tuple[float, float]:
        return self._thrust

    def arm(self) -> None:
        if self._closed:
            raise RuntimeError("propulsion is closed")
        self._thrust = (0.0, 0.0)
        self._armed = True

    def set_thrust(self, port: float, starboard: float) -> None:
        try:
            valid = all(isfinite(v) and -1 <= v <= 1 for v in (port, starboard))
        except (TypeError, ValueError, OverflowError):
            valid = False
        if not valid:
            self.stop()
            raise ValueError("thrust must be finite and within [-1, 1]")
        if not self._armed or self._closed:
            raise RuntimeError("propulsion must be open and armed")
        self._thrust = (float(port), float(starboard))

    def stop(self) -> None:
        self._thrust = (0.0, 0.0)
        self._armed = False

    def close(self) -> None:
        self.stop()
        self._closed = True
