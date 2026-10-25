"""20x4 HD44780 display via a PCF8574 I2C backpack."""
from typing import Sequence


class CharacterLcd:
    def __init__(self, bus: int = 1, address: int = 0x27) -> None:
        from RPLCD.i2c import CharLCD

        self._lcd = CharLCD(
            "PCF8574", address=address, port=bus, cols=20, rows=4,
            auto_linebreaks=False,
        )
        self._previous = [None] * 4

    def show(self, lines: Sequence[str]) -> None:
        if len(lines) != 4:
            raise ValueError("LCD requires exactly four rows")
        for row, text in enumerate(lines):
            line = text[:20].ljust(20)
            if line != self._previous[row]:
                self._lcd.cursor_pos = (row, 0)
                self._lcd.write_string(line)
                self._previous[row] = line

    def close(self) -> None:
        # Retain the final STOPPED/error message instead of a stale live screen.
        self._lcd.close(clear=False)
