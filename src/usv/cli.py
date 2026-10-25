"""Composition root: wire adapters here, outside control logic."""
import argparse
import logging
from usv.hal.interfaces import NavigationSensor, Propulsion
from usv.hal.simulated import SimulatedNavigation, SimulatedPropulsion


def run(navigation: NavigationSensor, propulsion: Propulsion) -> None:
    """One simulation read without arming; release both devices on failure."""
    try:
        logging.getLogger(__name__).info(
            "USV online in simulation; propulsion disarmed; navigation=%s",
            navigation.read(),
        )
    finally:
        try:
            propulsion.close()
        finally:
            navigation.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="USV simulation smoke check")
    commands = parser.add_subparsers(dest="command")
    gnss = commands.add_parser("gnss", help="Monitor the USB GNSS; no actuation")
    from usv.hal.gnss import DEFAULT_PORT
    gnss.add_argument("--port", default=DEFAULT_PORT)
    gnss.add_argument("--baudrate", type=int, default=9600)
    gnss.add_argument("--samples", type=int, default=0, help="Read windows; 0 runs until Ctrl-C")
    for name, help_text in (("lcd-test", "Visible four-row LCD test"),
                            ("gps-lcd", "GPS readout with LCD heartbeat")):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("--bus", type=int, default=1)
        command.add_argument("--address", type=lambda value: int(value, 0), default=0x27)
        command.add_argument("--seconds", type=float, default=20 if name == "lcd-test" else 0,
                             help="Duration; 0 runs continuously")
        if name == "gps-lcd":
            command.add_argument("--port", default=DEFAULT_PORT)
            command.add_argument("--baudrate", type=int, default=9600)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if args.command in ("lcd-test", "gps-lcd"):
        import math
        if not math.isfinite(args.seconds) or args.seconds < 0:
            parser.error("seconds must be finite and nonnegative")
        if args.bus < 0 or not 0x08 <= args.address <= 0x77:
            parser.error("invalid I2C bus or address")
        if args.command == "gps-lcd" and args.baudrate <= 0:
            parser.error("baudrate must be positive")
        try:
            from usv.hal.lcd import CharacterLcd
            from usv.gps_display import run_display, test_display
            display = CharacterLcd(args.bus, args.address)
            if args.command == "lcd-test":
                test_display(display, args.seconds or float("inf"))
            else:
                run_display(display, args.port, args.baudrate, args.seconds)
            return 0
        except ImportError:
            logging.error("Install extras: .venv/bin/python -m pip install -e '.[gnss,lcd]'")
            return 1
        except OSError as error:
            logging.error("LCD/GPS error: %s", error)
            return 1
        except KeyboardInterrupt:
            return 0
    if args.command == "gnss":
        if args.samples < 0 or args.baudrate <= 0:
            parser.error("samples must be nonnegative and baudrate positive")
        return monitor_gnss(args.port, args.baudrate, args.samples)
    run(SimulatedNavigation(), SimulatedPropulsion())
    return 0


def monitor_gnss(port: str, baudrate: int, samples: int) -> int:
    from usv.hal.gnss import UsbGnss

    device = None
    try:
        device = UsbGnss(port, baudrate)
        count = 0
        while samples == 0 or count < samples:
            fix = device.read()
            if fix is None:
                print("GNSS: no usable fix (no fix, timeout, or invalid data)", flush=True)
            else:
                print(
                    f"GNSS: lat={fix.latitude_deg:.6f} lon={fix.longitude_deg:.6f} "
                    "heading=unavailable", flush=True,
                )
            count += 1
        return 0
    except ImportError:
        logging.error("Install GNSS dependencies: .venv/bin/python -m pip install -e '.[gnss]'")
        return 1
    except OSError as error:
        logging.error("GNSS serial error on %s: %s", port, error)
        return 1
    except KeyboardInterrupt:
        return 0
    finally:
        if device is not None:
            device.close()
