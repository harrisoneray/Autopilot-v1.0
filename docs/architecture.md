# Architecture decisions

## Package and dependencies

Use `src/usv` to make the installable package boundary explicit. `pyproject.toml`
owns package metadata and direct dependencies. Standard `venv` and `pip` avoid
requiring a new environment manager on the Pi. Standard-library `unittest` keeps
hardware-independent tests runnable offline.

## Hardware boundary

The CLI constructs devices and injects them into application functions. Future
navigation and control code consume protocols and immutable measurements from
`hal.interfaces`, without importing vendor or GPIO libraries. Real adapters will
own device imports, channel mapping, physical units, and device resources.
Imports never open devices. Simulation and USB GNSS are implemented backends.

The GNSS adapter uses optional, pinned pySerial and pynmea2 dependencies. It
reads checksum-validated active RMC sentences with autonomous or differential
position mode (or legacy absent mode), rejecting estimated/simulated modes.
Other sentence types are ignored. Position is not cached across read windows.
The adapter buffers partial sentences, bounds line size and read duration, and
propagates serial errors. No writes configure the receiver. The stable USB by-id
path is preferred over enumeration-dependent tty names.

Monotonic timestamps record receipt, not GNSS measurement time. Detecting repeated
receiver epochs and validating measurement age are still required before using
these readings for autonomous control. Satellite count, accuracy, speed, UTC, and
course are not exposed yet. The monitor does not construct propulsion adapters.

The 20x4 LCD now consumes application data; an IMU is the next integration.
One application owns the GNSS port and distributes measurements to displays and
future control logic; each consumer must not reopen the same port.

The PCF8574 LCD adapter uses RPLCD and smbus2, with explicit bus/address selection.
It pads every row to 20 columns and updates only changed rows to avoid leftover
characters and full-screen clearing flicker. Formatting and the GPS lifecycle
live outside the adapter in gps_display. The loop has bounded GNSS reads and a
visible heartbeat, removes positions on unusable reads, retries USB errors, and
releases both devices on ordinary exit or Ctrl-C. It is a foreground application;
no boot service, propulsion, or IMU initialization is included.

Begin synchronously. Real adapters must bound I/O with timeouts. Add scheduling,
control, navigation, configuration, and telemetry modules when concrete behavior
requires them, rather than introducing empty framework layers now.

## Measurements and propulsion

Positions use WGS84 degrees; optional heading uses degrees clockwise from true
north. Adapters must explicitly handle magnetic-to-true conversion. Timestamps
use local monotonic seconds for future freshness checks, not cross-machine or
cross-reboot comparison. No valid fix is represented by None.

Propulsion assumes independent port/starboard commands in [-1, 1]: reverse to
forward, with zero neutral. Unsupported reverse must be rejected by real adapters.
Arming is explicit; invalid commands neutralize and disarm. Close is terminal and
idempotent. The simulator models state transitions, not physical vessel dynamics.

## Before real actuation

Hardware selection precedes concrete adapters. Bench verification must cover
neutral calibration, channel/sign mapping, bounded I/O, stale navigation, device
disconnects, and command expiration. Add a control supervisor that disarms on
faults or stale input. The current simulator has no automatic command timeout.

Python cleanup cannot handle process death, blocked I/O, or power loss. Physical
operation requires an independent watchdog or kill circuit and verified startup
and failure behavior. The scaffold is not a physical safety mechanism.
