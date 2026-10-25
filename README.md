# USV autopilot

Python foundations for a Raspberry Pi surface vessel, with simulation and a USB
GNSS monitor. No autonomous controller or real propulsion driver is implemented.

## Structure

```text
pyproject.toml             Package metadata and direct dependencies
src/usv/cli.py            Application entry point and adapter construction
src/usv/hal/interfaces.py Hardware contracts and navigation measurements
src/usv/hal/simulated.py  In-memory hardware implementations
tests/                   Hardware-independent behavior tests
docs/architecture.md      Decisions and hardware integration path
```

## Development

Supports Python 3.9+ for compatibility with the existing Pi environment. An OS or
interpreter upgrade is a separate decision. Use the existing `.venv`, or create
it if missing:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade 'pip<26'
.venv/bin/python -m pip install -e .
.venv/bin/python -m usv
.venv/bin/usv
.venv/bin/python -m unittest discover -s tests -v
```

Installation changes only the project environment and downloads build dependencies.
The setuptools bound retains Python 3.9 compatibility. To run without installation
or downloads from the project root:

```sh
PYTHONPATH=src python3 -m usv
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

The CLI reads once, stays disarmed, and closes both adapters. `src/main.py` remains
as a compatibility launcher.

Declare runtime dependencies in `project.dependencies` in `pyproject.toml`.
Device libraries live in optional extras; the GNSS extra pins its two dependencies.
The base simulation uses only the standard library. Build dependencies have version
bounds, not a lock. Before deployment, resolve and commit a full pinned dependency
set for the target interpreter and architecture; do not freeze an unrelated env.

## Git

Git is already initialized. `.gitignore` excludes virtual environments, secrets,
build outputs, and runtime data. `.gitattributes` standardizes source line endings.
Track source, tests, dependency declarations, future deployment locks, and example
configuration. Review `git diff` and run tests before committing. Git identity,
remotes, hooks, and global configuration are unchanged.

## Hardware integration

### HiLetgo VK172 USB GNSS

The connected receiver identifies as USB `1546:01a7` (u-blox 7), available through
`/dev/ttyACM0`. Prefer its stable by-id path, used as the CLI default:

```sh
.venv/bin/python -m pip install -e '.[gnss]'
.venv/bin/usv gnss
.venv/bin/usv gnss --samples 10
.venv/bin/usv gnss --port /dev/ttyACM0 --baudrate 9600
```

Ctrl-C stops monitoring and closes the port. `--samples` limits read windows,
not valid fixes. Each window takes up to about 1.2 seconds. No usable fix means
no active RMC position was received: the receiver may be acquiring satellites,
silent, or sending invalid data. Give it a clear view of the sky. Serial errors
are reported separately and return a nonzero exit code. No receiver configuration
commands are sent. The serial port is opened exclusively against other cooperating
readers; do not run a second monitor or gpsd against the same device.

The current user is already in `dialout`, so no permission change was needed.
GNSS tests require the extra; otherwise they are skipped. Coordinates may disclose
location, so the monitor prints live values without saving them to files.

### GPS and 20x4 LCD

The LCD is an HD44780-compatible 20x4 with a PCF8574 backpack on GPIO I2C
(physical SDA pin 3, SCL pin 5). GPIO I2C must be enabled separately in the OS.
After reboot, check `/dev/i2c-1` and identify the backpack address (commonly 0x27
or 0x3f). Do not scan HDMI I2C buses 20/21. Use the detected address below:

```sh
.venv/bin/python -m pip install -e '.[gnss,lcd]'
.venv/bin/usv lcd-test --address 0x27 --seconds 20
.venv/bin/usv gps-lcd --address 0x27
```

The visible test exercises all four rows with a rotating marker and counter.
The GPS readout shows initialization, acquisition, and signed latitude/longitude
in decimal degrees once a valid RMC position arrives. Its bottom row rotates
`| / - \\` and shows uptime, normally updating about once per second. The marker
means the application loop is advancing, including while acquiring or disconnected;
it does not certify GPS validity. A frozen marker indicates the display is no
longer updating. Unusable read windows immediately remove displayed coordinates.
USB failures trigger reconnection attempts every three seconds. Ctrl-C closes
devices and leaves an explicit STOPPED message. Abrupt power/process loss cannot
update that final message; watch the heartbeat. No propulsion code runs.

Use `--seconds 30` for a bounded GPS display run. Boot autostart is not configured;
run it manually until the hardware readout is verified.

### IMU later

The LCD consumes navigation data from the same application; next add an IMU adapter.
Confirm the IMU model before choosing its library. GNSS course over ground
is not hull heading; this driver intentionally leaves heading unavailable.

Identify the Pi model/OS, IMU model, bus types (UART, USB, I2C, SPI),
propulsion layout, ESC protocol, neutral settings, and emergency stop mechanism.
The initial port/starboard interface assumes differential thrust; rudder steering
needs a different contract. No GPIO, bus, service, or system settings are modified.
