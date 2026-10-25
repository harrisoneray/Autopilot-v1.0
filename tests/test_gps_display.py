import unittest
from unittest.mock import Mock, patch

from usv.gps_display import run_display, screen
from usv.hal.interfaces import NavigationFix
from usv.hal.lcd import CharacterLcd


class DisplayTests(unittest.TestCase):
    def test_extreme_coordinates_fit_four_rows(self):
        fix = NavigationFix(-90, -180, None, 0)
        rows = screen(fix, 3661, 0)
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(len(row) <= 20 for row in rows))
        self.assertIn("-180.000000", rows[2])
        self.assertIn("01:01:01", rows[3])

    def test_lost_fix_removes_coordinates_and_heartbeat_advances(self):
        first = screen(NavigationFix(1, 2, None, 0), 0, 0)
        lost = screen(None, 1, 1)
        self.assertNotIn("Lat", " ".join(lost))
        self.assertIn("acquiring", lost[1])
        self.assertNotEqual(first[3][0], lost[3][0])

    def test_lcd_pads_shorter_rows_and_skips_unchanged_rows(self):
        lcd = CharacterLcd.__new__(CharacterLcd)
        lcd._lcd = Mock()
        lcd._previous = [None] * 4
        lcd.show(("long first row", "b", "c", "d"))
        lcd._lcd.write_string.reset_mock()
        lcd.show(("short", "b", "c", "d"))
        lcd._lcd.write_string.assert_called_once_with("short".ljust(20))

    @patch("usv.gps_display.time.sleep")
    @patch("usv.gps_display.UsbGnss")
    def test_disconnect_then_reconnect_and_cleanup(self, factory, sleep):
        display = Mock()
        failed, recovered = Mock(), Mock()
        failed.read.side_effect = OSError("unplugged")
        recovered.read.return_value = NavigationFix(1, 2, None, 0)
        factory.side_effect = [failed, recovered]
        # Advance deterministically through the reconnect delay.
        with patch("usv.gps_display.time.monotonic", side_effect=range(30)):
            run_display(display, "test", 9600, seconds=12)
        messages = [call.args[0] for call in display.show.call_args_list]
        self.assertTrue(any("GPS: disconnected" in rows for rows in messages))
        self.assertTrue(any(rows[0] == "USV GPS: FIX" for rows in messages))
        self.assertEqual(messages[-1][0], "USV GPS STOPPED")
        failed.close.assert_called_once()
        recovered.close.assert_called_once()
        display.close.assert_called_once()

    @patch("usv.gps_display.time.sleep")
    @patch("usv.gps_display.UsbGnss")
    def test_interrupt_closes_devices_and_marks_stopped(self, factory, sleep):
        display = Mock()
        factory.return_value.read.side_effect = KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            run_display(display, "test", 9600)
        factory.return_value.close.assert_called_once()
        display.close.assert_called_once()
        self.assertEqual(display.show.call_args.args[0][0], "USV GPS STOPPED")
