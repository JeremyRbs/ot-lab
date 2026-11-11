# Session 2: First ST program and Modbus/TCP communication

## Objective

Write a first Structured Text program (tank level control), deploy it to the v4 runtime, enable the Modbus/TCP server, and read the variables from a PC using Python/pymodbus.

## 1. ST Program: Tank level control

Simulated process: a pump fills a tank up to a setpoint, with a 10-unit hysteresis to prevent short-cycling (constant on/off toggling).

**Important (OpenPLC Editor specificity)**: you do not declare `PROGRAM PLC_PRG` inside the ST file. The program name and variables are declared in the editor's variable table; the ST body only contains the logic.

Variable table:

| Name | Class | Type | Location | Initial Value |
|---|---|---|---|---|
| sensor_level | Local | BOOL | %IX0.0 | (none) |
| pump_output | Local | BOOL | %QX0.0 | (none) |
| setpoint | Local | INT | %MW0 | 50 |
| level | Local | INT | %MW1 | (none) |

Program body (ST block of `PLC_PRG`):

```iecst
IF level < setpoint THEN
    pump_output := TRUE;
ELSIF level >= (setpoint + 10) THEN
    pump_output := FALSE;
END_IF;
```

> Lesson learned: I wrote `pump_output := TRUE` in the `ELSIF` branch at first, which left the pump permanently on. A beginner mistake, corrected during the session. I now re-read the stop logic before compiling.

> Lesson #2: `level` was initially on `%IW0` (Input Register). A `%IW` is a **physical input**: the runtime overwrites it with 0 on every cycle, so only manual forcing in debug could change it. To simulate the sensor from Python, I moved it to `%MW1` (Holding Register, readable **and** writable via Modbus).

Compile + deploy from OpenPLC Editor v4 to the runtime → the runtime generates `build/new_libplc.so`, loads the program, and switches to `PLC State: RUNNING`. Scan cycle: 20 ms (`PLC base tick: 20000000 ns`).

## 2. Enabling the modbus server

`modbus_slave` plugin enabled (the others, modbus_master / opcua / s7comm / ethercat, remain disabled). Verification on the Pi:

```bash
sudo ss -lntp | grep ':502'
```

```
LISTEN 0 100 0.0.0.0:502 0.0.0.0:* users:(("plc_main",pid=1474,fd=9))
```

Port 502 only opens after deploying the program with the plugin enabled, so do not worry if it is absent beforehand.

## 3. v4 runtime modbus map ("Segmented" format)

The `modbus_slave` plugin addressing plan in segmented mode:

| Zone | Modbus Functions | Addresses (0-based) | Our Variables |
|---|---|---|---|
| Coils (`%QX`) | 01 read / 05 write | 0–7 | `pump_output` → **0** |
| Discrete Inputs (`%IX`) | 02 read | 0–7 | `sensor_level` → **0** |
| Input Registers (`%IW`) | 04 read | 0–1023 | (free) |
| Holding Registers `%QW` | 03 / 06 | 0–1023 | (none) |
| Holding Registers `%MW` | 03 / 06 | **1024–2047** | `setpoint` → **1024**, `level` → **1025** |
| Holding Registers `%MD` | 03 / 06 | 2048–4095 | (double words) |
| Holding Registers `%ML` | 03 / 06 | 4096–8191 | (long words) |

Word order: `high_word_first`. The current scripts and packet captures use
Modbus Unit ID 1. Some earlier ad-hoc examples used Unit ID 0; that did not
match the Unit ID observed in the captures.

## 4. Reading/Writing from Python (pymodbus)

Script: `scripts/modbus_read.py` (host/port config in `scripts/config.json`).

Reads:

```python
r_setpoint = client.read_holding_registers(1024, count=1, device_id=1)  # setpoint (%MW0)
r_level    = client.read_holding_registers(1025, count=1, device_id=1)  # level (%MW1)
r_pump     = client.read_coils(0, count=1, device_id=1)                 # pump_output (%QX0.0)
```

Writes (simulating the level sensor from the PC):

```python
client.write_register(1024, 50, device_id=1)  # setpoint := 50
client.write_register(1025, 20, device_id=1)  # level := 20 (low tank)
client.write_register(1025, 65, device_id=1)  # level := 65 (high tank, setpoint + 15)
```

## 5. Functional test results

| Test | Write | Expected Read | Result |
|---|---|---|---|
| Low tank | `level := 20`, `setpoint := 50` | `pump_output` = True (20 < 50 → pump ON) | ✅ |
| High tank | `level := 65` (≥ 50 + 10) | `pump_output` = False (hysteresis → pump OFF) | ✅ |

The complete loop works: **Modbus write → PLC logic (20 ms cycle) → output readable on the coil → read back from the PC**.

Security observation (setting up Session 4): a client that can reach TCP/502
can attempt to write the setpoint or measurement. Classic Modbus/TCP has no
built-in authentication; network filtering determines which clients can reach
the server.

## Pitfalls encountered and resolutions

- `PROGRAM` flagged as an error in the ST file → declarations belong in the editor's variable table, not in the code.
- `PLC State: EMPTY` before the first deployment → normal; the `libplc` file is generated at project compile time.
- Values read as 0 despite initialization to 50 → check the Unit ID (`device_id=1`) and the address (`%MW` is offset by +1024 in the segmented map).
- `%IW0` could not be driven from Python → Input Registers are read-only; move the simulated variable to `%MW`.

## Session deliverables

- [x] ST program deployed, PLC in `RUNNING`, 20 ms cycle
- [x] Modbus/TCP server active on port 502
- [x] Variables ↔ Modbus addresses mapping table documented
- [x] `modbus_read.py` script working: read + write + hysteresis test
- [x] Session commit in `ot-lab`

## Next step

Session 3: HMI/Supervision + capturing Modbus traffic with Wireshark (reading functions 01/03/06 frame by frame), then integrating Rheomix as the physical process.