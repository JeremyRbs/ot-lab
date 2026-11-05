# Session 3 — Autonomous Tank, Modbus Packet Analysis, and CLI HMI

## Objective

Turn the register-level tank example from Session 2 into a running simulated
process, observe Modbus/TCP traffic packet by packet, and display the process
through a lightweight Python HMI.

## 1. Autonomous Tank Simulation

The PLC program in [`../scripts/main.st`](../scripts/main.st) was extended so
the tank level changes inside the controller rather than being continuously
driven by Python:

```iecst
IF pump_output THEN
    level := level + 1;
END_IF;

IF level < setpoint THEN
    pump_output := TRUE;
ELSIF level >= (setpoint + 10) THEN
    pump_output := FALSE;
END_IF;

IF level > 100 THEN
    level := 100;
END_IF;
```

The controller fills while the pump is on, starts the pump below the setpoint,
and stops it at the setpoint plus the 10-unit hysteresis. The level is capped
at 100. The PC can set the target through holding register 1024; the PLC owns
the level and pump behavior.

The exported capture shows the level rising from 0 to 60 with a setpoint of 50,
then shows the pump coil changing from on to off at level 60. This is consistent
with the intended hysteresis behavior for a setpoint of 50.

The `scripts/modbus_read.py` test initializes the setpoint to 50 and the tank
level to 0. The capture's FC06 request writes 50 (`00 32`) to register 1024,
and its FC03 responses read back 50, matching the documented test. A setpoint
of 70 was used in a separate test, not the run represented by this capture.

> **Scan-rate behavior:** The simulation intentionally increments the level
> once per PLC scan; it does not target a fixed fill rate of 5 units per second.
> The actual rate therefore depends on the deployed scan period. Session 2
> records a 20 ms PLC base tick, which would correspond to about 50 level units
> per second if that is the effective cycle period. The capture verifies that
> the level rises, but does not establish the deployed scan period. The original
> “5 units/s” comment was corrected because it did not match scan-based logic.

## 2. Wireshark Capture and Modbus/TCP Dissection

Capture file: [`../captures/session3.pcapng`](../captures/session3.pcapng)

The capture contains request/response pairs between the client
(`192.168.1.50`) and the Modbus server (`192.168.1.120:502`). Decoding the
Modbus/TCP payloads confirmed:

| Function | Meaning | Requests | Responses |
|---|---|---:|---:|
| 01 | Read Coils | 12 | 12 |
| 03 | Read Holding Registers | 24 | 24 |
| 06 | Write Single Register | 2 | 2 |

### FC03 — Read Holding Registers

The captured request for the setpoint is:

```text
00 03 00 00 00 06 01 03 04 00 00 01
```

Byte-by-byte:

| Bytes | Value | Meaning |
|---|---|---|
| 0–1 | `00 03` | Transaction ID `0x0003` |
| 2–3 | `00 00` | Protocol ID 0 (Modbus) |
| 4–5 | `00 06` | MBAP length: 6 bytes follow (Unit ID + PDU) |
| 6 | `01` | Unit ID 1, as used in the capture |
| 7 | `03` | Read Holding Registers |
| 8–9 | `04 00` | Starting address `0x0400` = 1024 (setpoint) |
| 10–11 | `00 01` | Read one register |

The matching response is:

```text
00 03 00 00 00 05 01 03 02 00 32
```

It has the same transaction ID, response length `00 05`, Unit ID `01`, and
function `03`. The byte count is `02`, and the register value is `00 32` =
50 decimal.

### FC06 — Write Single Register

The captured setpoint write is:

```text
00 01 00 00 00 06 01 06 04 00 00 32
```

| Bytes | Value | Meaning |
|---|---|---|
| 0–1 | `00 01` | Transaction ID `0x0001` |
| 2–3 | `00 00` | Protocol ID 0 |
| 4–5 | `00 06` | MBAP length |
| 6 | `01` | Unit ID 1 |
| 7 | `06` | Write Single Register |
| 8–9 | `04 00` | Register address 1024 |
| 10–11 | `00 32` | Value 50 decimal |

For FC06, the normal response echoes the address and value; the capture shows
the request and its matching echo. This write sets the setpoint to 50. The
second FC06 pair writes `0` to address `0x0401` (1025), initializing the level
to an empty tank for the run.

### FC01 — Read Coils

One captured coil read is:

```text
00 05 00 00 00 06 01 01 00 00 00 01
```

It uses transaction ID `0x0005`, Unit ID 1, function `01`, starting coil 0,
and quantity 1. Coil 0 maps to `pump_output` (`%QX0.0`). Its response contains
the packed coil value: `01` means on; `00` means off. The capture contains
responses showing both states.

> **Addressing note:** the Session 2 notes refer to `slave=0`, but this capture
> and the current scripts use Unit ID 1 (`device_id=1`). The dissection above
> records the actual bytes observed rather than assuming a Unit ID from an
> earlier note.

## 3. CLI HMI

[`../scripts/hmi.py`](../scripts/hmi.py) polls the setpoint and level together
using FC03, reads the pump coil using FC01, and refreshes a 70-character tank
bar every 200 ms. It reads the server address and port from
`scripts/config.json`.

The HMI is read-only: it does not change the setpoint on startup. Change the
setpoint separately with the Modbus client when testing the control loop. The
script uses Unit ID 1, consistent with the capture and current pymodbus API.

Run it from the repository root:

```bash
python scripts/hmi.py
```

Press `Ctrl+C` to stop it cleanly.

## Verification and Limitations

- The PCAPNG file was parsed and confirmed to contain FC01, FC03, and FC06
  request/response pairs with matching transaction IDs.
- The decoded register values show a captured setpoint of 50, a level
  increasing to 60, and the pump turning off at 60, consistent with the
  50 + 10 hysteresis threshold.
- Both Python scripts pass Python syntax compilation in this environment.
- A live PLC/HMI connection was not run as part of this repository check.
- The ST source is versioned as `scripts/main.st`; the exact deployed PLC build
  still cannot be independently verified from this repository alone.
- The HMI poll interval (200 ms) is separate from the PLC scan interval.

## Session Deliverables

- [x] Autonomous tank behavior observed in the Modbus capture
- [x] `captures/session3.pcapng` with FC01, FC03, and FC06 traffic
- [x] FC03 and FC06 frames dissected byte by byte
- [x] `scripts/hmi.py` provides a read-only live CLI display
- [x] Keep scan-based filling: increment once per PLC scan; rate depends on the PLC cycle
- [x] ST process logic saved in `scripts/main.st`
