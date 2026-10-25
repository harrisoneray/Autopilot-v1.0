import unittest
from unittest.mock import Mock
from usv.cli import run
from usv.hal.interfaces import NavigationFix
from usv.hal.simulated import SimulatedNavigation, SimulatedPropulsion


class HardwareTests(unittest.TestCase):
    def test_requires_arming(self):
        motor = SimulatedPropulsion()
        self.assertFalse(motor.armed)
        with self.assertRaises(RuntimeError):
            motor.set_thrust(0.5, 0.5)
        self.assertEqual(motor.thrust, (0, 0))

    def test_invalid_commands_disarm(self):
        for value in (1.1, -1.1, float("nan"), float("inf"), "bad"):
            with self.subTest(value=value):
                motor = SimulatedPropulsion()
                motor.arm()
                motor.set_thrust(0.5, -0.5)
                with self.assertRaises(ValueError):
                    motor.set_thrust(0.5, value)
                self.assertFalse(motor.armed)
                self.assertEqual(motor.thrust, (0, 0))

    def test_close_is_terminal_and_idempotent(self):
        motor = SimulatedPropulsion()
        motor.arm()
        motor.set_thrust(-1, 1)
        self.assertEqual(motor.thrust, (-1, 1))
        motor.close()
        motor.close()
        self.assertFalse(motor.armed)
        self.assertEqual(motor.thrust, (0, 0))
        with self.assertRaises(RuntimeError):
            motor.arm()

    def test_cleanup_after_read_failure(self):
        navigation = Mock()
        navigation.read.side_effect = OSError("disconnected")
        motor = SimulatedPropulsion()
        motor.arm()
        motor.set_thrust(1, 1)
        with self.assertRaises(OSError):
            run(navigation, motor)
        self.assertFalse(motor.armed)
        self.assertEqual(motor.thrust, (0, 0))
        navigation.close.assert_called_once()

    def test_cleanup_after_output_failure(self):
        navigation, motor = Mock(), Mock()
        motor.close.side_effect = OSError("bus failed")
        with self.assertRaises(OSError):
            run(navigation, motor)
        navigation.close.assert_called_once()

    def test_no_fabricated_fix(self):
        self.assertIsNone(SimulatedNavigation().read())

    def test_invalid_fix(self):
        for args in ((91, 0, None, 0), (0, 181, None, 0),
                     (0, 0, float("nan"), 0), (0, 0, None, -1)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                NavigationFix(*args)


if __name__ == "__main__":
    unittest.main()
