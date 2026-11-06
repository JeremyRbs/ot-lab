# Session 4 — Modbus Reconnaissance and Simulated Unauthorized Write

> Scope: this exercise used the author's isolated lab and a simulated tank.
> It does not demonstrate control of a physical pump or any third-party
> system.

## Objective

Observe what a Modbus/TCP client can learn by reading the PLC's mapped data,
then document the effect of an unauthorized setpoint write on the simulated
process. The PLC logic itself was not changed during the write: it continued to
execute its control rules using the new setpoint.

## 1. Reconnaissance

[`../scripts/attack_recon.py`](../scripts/attack_recon.py) reads holding
registers 1024–1049 and coils 0–7 from the Modbus server configured in
`scripts/config.json`. In the OpenPLC mapping documented in Session 2, the
known process points are:

| Modbus point | PLC variable | Meaning |
|---|---|---|
| Holding register 1024 | `%MW0` / `setpoint` | Requested tank level |
| Holding register 1025 | `%MW1` / `level` | Simulated tank level |
| Coil 0 | `%QX0.0` / `pump_output` | Pump command |

This is a fixed, targeted read of the lab's known address range; it is not a
network-wide scan. The script is configured for Unit ID 1.

### Nmap service discovery

The supplied Nmap output for `192.168.1.120` reports the host up and these
services:

| Port | State | Detected service |
|---|---|---|
| 502/tcp | Open | Modbus TCP (gateway) |
| 8443/tcp | Open | HTTPS; Werkzeug httpd 3.1.9 (Python 3.13.5) |

Nmap also identified the host as `nexus.home` and the device as a Raspberry Pi.
The scan took about 92 seconds. Service/version detection is an observation
from this scan, not proof that the service is vulnerable.

### Register and coil enumeration

The supplied `attack_recon.py` terminal output shows the following normal
process state:

| Address range | Observed values | Interpretation |
|---|---|---|
| Holding register 1024 | 50 | Setpoint |
| Holding register 1025 | 60 | Tank level |
| Holding registers 1026–1049 | 0 | No other non-zero values in the scanned range |
| Coils 0–7 | All OFF | Pump output at coil 0 was OFF; other scanned coils were OFF |

At level 60 with setpoint 50, the pump being off is consistent with the
setpoint + 10 hysteresis threshold. This enumeration is a point-in-time
snapshot; observing a changing level requires repeated reads.

The supplied PCAPNG does not show the full register/coil enumeration from
`attack_recon.py`: its reads are predominantly holding-register reads starting
at 1024 with a quantity of two, plus reads of coil 0. Because multiple scripts
use the same client machine, those captured reads cannot be attributed
specifically to the reconnaissance script. The raw Nmap output is saved in
[`../captures/session4-nmap.txt`](../captures/session4-nmap.txt). The
reconnaissance output above was supplied in the original session conversation.
To preserve raw output, the read-only script was run again on 2026-11-06 and
saved as [`../captures/session4-recon.txt`](../captures/session4-recon.txt).
This is a fresh follow-up snapshot, not the original Session 4 terminal output:
it reports setpoint 200, level 100, and coil 0 ON. Do not conflate it with the
earlier Session 4 state above.

## 2. Captured Modbus/TCP Traffic

Capture: [`../captures/session4-attack.pcapng`](../captures/session4-attack.pcapng)

Offline parsing found these Modbus/TCP messages:

| Function | Operation | Requests | Responses |
|---|---|---:|---:|
| 01 | Read Coils | 715 | 715 |
| 03 | Read Holding Registers | 729 | 728 |
| 06 | Write Single Register | 3 | 3 |

The capture contains one fewer FC03 response than requests; this does not by
itself establish a server-side failure. The FC06 attack request has a matching
response. The capture spans about 165 seconds. Times below are relative to the
attack write in the capture, not wall-clock times.

## 3. Setpoint Write and Simulated Process Effect

[`../scripts/attack_overflow.py`](../scripts/attack_overflow.py) writes 200 to
holding register 1024, which maps to the setpoint. The relevant captured FC06
request is:

```text
00 01 00 00 00 06 01 06 04 00 00 C8
```

| Bytes | Value | Meaning |
|---|---|---|
| 0–1 | `00 01` | Transaction ID `0x0001` |
| 2–3 | `00 00` | Protocol ID 0 (Modbus) |
| 4–5 | `00 06` | MBAP length: Unit ID plus PDU |
| 6 | `01` | Unit ID 1 |
| 7 | `06` | Write Single Register |
| 8–9 | `04 00` | Holding-register address `0x0400` = 1024 |
| 10–11 | `00 C8` | Value `0x00C8` = 200 decimal |

The response echoes the address and value. The capture records it about
5.2 ms after the request; this is the measured response time in this capture,
not a general latency guarantee.

### Captured chronology

| Relative time | Setpoint | Level | Pump coil | Observation |
|---|---:|---:|---|---|
| About 0.17 s before write | 50 | 60 | OFF | Normal state at the setpoint + 10 threshold |
| About 0.17 s after write | 200 | 67 | ON | New setpoint is read back; pump is on |
| About 0.51 s after write | 200 | 84 | ON | Simulated level continues to rise |
| About 0.85 s after write | 200 | 100 | ON | Level reaches the ST upper limit |
| Remainder of capture | 200 | 100 | ON | Repeated reads show the capped level and pump on |

This is a simulated process impact, not a physical overflow. The ST program
clamps `level` at 100, but with a setpoint of 200 the stop threshold is 210.
The level can never reach that threshold, so the PLC keeps `pump_output` on
while the simulated value remains capped at 100.

## 4. What the Capture Does and Does Not Prove

- The server accepted the captured FC06 write and echoed it; later FC03
  responses show setpoint 200.
- Modbus/TCP has no built-in authentication or encryption in its classic form.
  The successful write demonstrates that this client could write to this
  server in this lab. It does not prove that every network client can reach the
  PLC; firewall rules and network segmentation still matter.
- No Modbus-level rejection or alarm is visible in the captured exchange.
  Runtime logs and alerting configuration were not supplied, so the capture
  cannot prove that no logs or alerts were generated elsewhere.
- The ST control logic kept running and acted on the changed setpoint. The
  observed issue is unauthorized access to a writable process value, not
  evidence that the PLC program was replaced or compromised.
- `attack_overflow.py` leaves the test setpoint at 200. After the exercise,
  restore a safe test state in the isolated lab and confirm the pump output is
  off before ending the session.

## 5. Code and Repository Notes

- Both session 4 scripts now use English output and comments. The JSON
  configuration is read with Python's standard library; Flask is not needed.
- The setpoint-write script checks the Modbus write response and readback
  before reporting success.
- `scripts/config.example.json` provides the template referenced by the
  README. The real `scripts/config.json` remains local and ignored by Git.
- The attack scripts use the configured host and do not enforce an allowlist.
  They can connect to any host entered in the configuration. Verify that it
  points only to the authorized, isolated lab before running them.
- The PCAPNG supports the write and process-state timeline above. It does not
  include the Nmap output, the complete register-enumeration run, or runtime
  logs. The raw Nmap output is saved separately; the register-enumeration
  results came from terminal output supplied separately.

## Verification

- The session 4 PCAPNG was parsed offline.
- The raw follow-up reconnaissance output was captured from the configured
  lab PLC on 2026-11-06; it performed reads only.
- All Python scripts pass syntax compilation in the current environment.
- The later Session 5 setpoint restoration write and its verification are
  documented in [`session-05.md`](./session-05.md).

## Session Deliverables

- [x] `scripts/attack_recon.py` read the configured lab PLC's mapped points
      (terminal output supplied; not present in the PCAPNG)
- [x] Nmap identified Modbus/TCP on port 502 and HTTPS on port 8443
- [x] `scripts/attack_overflow.py` contains the controlled setpoint-write test
- [x] `captures/session4-attack.pcapng` contains the FC06 write and subsequent
  process reads
- [x] FC06 request decoded byte by byte
- [x] Simulated impact documented without claiming a physical overflow
- [x] Save the Nmap output in `captures/session4-nmap.txt`
- [x] Save a fresh raw `attack_recon.py` output as
      `captures/session4-recon.txt` (follow-up snapshot, not original-session
      output)
