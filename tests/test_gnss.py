import unittest
from unittest.mock import Mock, patch

try:
    import pynmea2
    import serial
    HAVE_GNSS = True
except ImportError:
    HAVE_GNSS = False

from usv.hal.gnss import UsbGnss, parse_rmc


def sentence(body):
    checksum = 0
    for value in body.encode("ascii"):
        checksum ^= value
    return f"${body}*{checksum:02X}\r\n".encode("ascii")


@unittest.skipUnless(HAVE_GNSS, "install .[gnss] to run GNSS tests")
class GnssTests(unittest.TestCase):
    def test_valid_position_without_heading(self):
        fix = parse_rmc(sentence("GPRMC,123519,A,4807.038,N,01131.000,E,1,84.4,230394,,,A"))
        self.assertAlmostEqual(fix.latitude_deg, 48.1173)
        self.assertAlmostEqual(fix.longitude_deg, 11.5166667)
        self.assertIsNone(fix.heading_deg)

    def test_southern_western_and_gn_talker(self):
        fix = parse_rmc(sentence("GNRMC,123519,A,4807.038,S,01131.000,W,0,0,230394,,,D"))
        self.assertLess(fix.latitude_deg, 0)
        self.assertLess(fix.longitude_deg, 0)

    def test_reject_invalid_input(self):
        for body in (
            "GPRMC,123519,V,4807.038,N,01131.000,E,0,0,230394,,,A",
            "GPRMC,123519,A,,N,,E,0,0,230394,,,A",
            "GPRMC,123519,A,4867.038,N,01131.000,E,0,0,230394,,,A",
            "GPRMC,123519,A,4807.038,X,01131.000,E,0,0,230394,,,A",
            "GPRMC,123519,A,4807.038,N,01131.000,E,0,0,230394,,,E",
        ):
            with self.subTest(body=body):
                self.assertIsNone(parse_rmc(sentence(body)))
        for line in (b"garbage", b"\xff", b"$GPRMC,broken*00", b"$GPRMC,broken"):
            self.assertIsNone(parse_rmc(line))

    @patch("serial.Serial")
    def test_partial_lines_and_no_cached_fix(self, factory):
        line = sentence("GPRMC,123519,A,4807.038,N,01131.000,E,0,0,230394,,,A")
        stream = factory.return_value
        stream.read_until.side_effect = [line[:10], line[10:]] + [b""] * 64
        device = UsbGnss("test")
        self.assertIsNotNone(device.read())
        self.assertIsNone(device.read())
        device.close()
        device.close()
        stream.close.assert_called_once()
        with self.assertRaises(RuntimeError):
            device.read()

    @patch("serial.Serial")
    def test_disconnect_propagates(self, factory):
        factory.return_value.read_until.side_effect = serial.SerialException("unplugged")
        device = UsbGnss("test")
        with self.assertRaises(OSError):
            device.read()
        device.close()
