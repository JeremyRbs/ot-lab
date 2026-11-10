# Session 6 — Ignition SCADA: Device Connection, Tags, Perspective HMI, and an Attack Seen from Supervision

> File: `docs/session-06.md` — commit at the root of the `ot-lab` repository.

## Objective

Add a real SCADA layer to the bench: connect Ignition (Maker Edition) to the OpenPLC Modbus server, expose the process variables as OPC UA tags, build a small Perspective HMI, and replay the Session 4 attack while watching it live from supervision. The bench moves from "emulated PLC" to "mini-SCADA".

## 1. Environment

| Item | Value |
|---|---|
| SCADA | Ignition Standard 8.3.10, installed on the client PC (`192.168.1.50`), trial mode (Maker-equivalent limits: 2 device connections, no redundancy — irrelevant for this bench) |
| Gateway | `http://localhost:8088`, web configuration UI |
| Designer | Perspective-enabled project `Supervision_Tank` |
| Device | `Automate_Modbus`, driver Modbus TCP → `192.168.1.120:502` |
| PLC | OpenPLC Runtime v4, unchanged (Unit ID 1 expected — see pitfalls) |

Architecture note: the SCADA runs on the PC, the PLC on the Pi. Supervision and control are separated — the standard OT pattern. Because the Session 5 firewall allowlists the PC's IP, the SCADA inherits legitimate access automatically: the segmentation governs the supervision path too.

## 2. Device Connection (Gateway)

Path (Ignition 8.3 reorganized the menus): Gateway web UI → **Connections → Devices → Create Device Connection → Modbus TCP**.

Key parameters: Name `Automate_Modbus`, Hostname `192.168.1.120`, Port `502`. Status: **CONNECTED**.

The Modbus TCP driver form has no single global Unit ID field; unit routing is done through the device's **Address Mapping** table (see pitfalls).

## 3. Tags (Designer → Tag Browser)

Folder `Tank`, four OPC tags on `Ignition OPC UA Server`:

| Tag | Data Type | OPC Item Path | Modbus target | Access |
|---|---|---|---|---|
| setpoint | Integer | `[Automate_Modbus]1.HR1024` | HR 1024 (`%MW0`) | Read/Write |
| level | Integer | `[Automate_Modbus]1.HR1025` | HR 1025 (`%MW1`) | Read |
| pump | Boolean | `[Automate_Modbus]1.C0` | Coil 0 (`%QX0.0`) | Read/Write |
| sensor_level | Boolean | `[Automate_Modbus]1.DI0` | DI 0 (`%IX0.0`) | Read |

Validation: `setpoint` read back **50** — matching the value written by the initialization script — confirmed the addressing chain end to end. The unit-ID prefix `1.` in the item path is what routes the request to Unit ID 1 (see pitfalls).

## 4. Perspective HMI (`Tank_Overview`)

Coordinate-layout view, four components:

- **Cylindrical Tank** — `value` bound to `Tank/level`, min 0 / max 100. A Label marks the hysteresis threshold ("Seuil (60)").
- **Numeric Entry Field** — bidirectional tag binding to `Tank/setpoint`, min 0 / max 100 enforced **in the HMI only**.
- **Pump symbol** (ISA-style) — `state` bound to `Tank/pump`; colors forced with an expression binding on the style property: `if({[default]Tank/pump}, "#00FF00", "#FF0000")` (the default high-performance HMI gray palette was replaced deliberately for legibility in this lab).
- **Alarm label** — visibility bound to an expression: `{[default]Tank/level} >= 100 && {[default]Tank/pump}` — the Session 4 "pump stuck ON at capped level" state, now detectable from supervision.

Live behavior verified in a browser session: setpoint change → pump ON (green) → level rises → pump OFF (red) at setpoint + 10. The hysteresis loop is visible on a real industrial HMI.

## 5. The Attack, Seen from Supervision

With the Perspective session open, `scripts/attack_overflow.py` was replayed (FC06 write of 200 to register 1024). Observed live on the HMI (screenshot committed with this session):

- Setpoint field displays **200** — the HMI obeys the PLC, not the operator.
- Level saturates at **100**; pump stays **ON** (stop threshold 210 is unreachable).
- The alarm label triggers: overflow condition with pump running.

Two conclusions, both documented with evidence:

1. **HMI-side limits are cosmetic.** The Numeric Entry Field rejects 0–100 outside its range, but a direct Modbus write bypasses the HMI entirely. Security enforced only at the supervision layer is an illusion in OT.
2. **The SCADA detects what the PLC does not.** The alarm expression (level ≥ 100 while pump ON) fired from supervision even though the PLC has no such interlock — the `%IX0.0` high-level sensor input stays FALSE because nothing drives it (see pitfalls). A properly configured SCADA alarm caught the anomaly the control logic could not.

## 6. Pitfalls Encountered and Resolutions

- **Ignition 8.3 menu reorganization**: device connections are under *Connections → Devices*, not the OPC UA *Connections* page (which manages OPC client/server links). Direct URL helped: `/data/config/connections/devices`.
- **Unit ID 0 sent by Ignition** (`requested device id does not exist: 0` on the Pi logs): the 8.3 Modbus driver routes Unit IDs through the device's **Address Mapping** table; a partial/invalid row silently left requests on Unit ID 0, which OpenPLC rejects with exception `0x83 0x0B`. Fix: one complete mapping row (Prefix `1`, Start `0`, End `65535`, Unit ID `1`, Type `HoldingRegister`) + the `1.` prefix in every tag path. OpenPLC was **not** modified — the fix is entirely on the SCADA side.
- **Zero-based addressing**: Ignition's logs showed a request for address 1023 for a `HR1024` tag (zero-based indexing active). The tag paths above work with the indexing setting as deployed; any off-by-one shows up as a plausible-but-wrong value (0), not an error — always validate against a known value (setpoint = 50) before trusting tags.
- **`%MW` volatility**: the `Initial Value` (50) in OpenPLC Editor only applies at program load. After a Pi/runtime restart, `%MW` memory resets to 0 and the setpoint must be re-written by the client (the initialization script does this). Lesson: non-retentive variables need a startup strategy — either a client write, or logic in the PLC. (`setpoint := 50;` on first scan would be the PLC-side fix; deliberately not applied here so the lab keeps its "supervisor injects the setpoint" pattern.)
- **`sensor_level` permanently FALSE**: correct and expected. `%IX0.0` is a physical input; neither the PLC program nor the simulation drives it. It only becomes TRUE if actual hardware does. The alarm was therefore deliberately built on process values (`level`, `pump`), not on the sensor input.

## 7. What This Session Does and Does Not Prove

- The SCADA → PLC → SCADA round trip works over the segmented network, with Unit ID 1 and the documented addressing.
- The alarm demonstrates **detection at the supervision layer** of a state the PLC tolerates. It is not a safety function: Ignition alarms depend on the SCADA being up, connected, and correctly configured.
- The attack screenshot shows an unauthorized write reflected in a professional HMI — impact made visible, not claimed.

## Session Deliverables

- [x] Ignition installed, device `Automate_Modbus` CONNECTED
- [x] 4 tags functional, addressing syntax documented (`[Automate_Modbus]1.HR1024` etc.)
- [x] Perspective HMI: tank, setpoint entry, pump symbol, overflow alarm
- [x] Screenshot: HMI in normal operation
- [x] Screenshot: HMI during the attack (setpoint 200, level 100, pump ON, alarm)
- [x] Unit ID mapping and zero-based indexing pitfalls documented
- [x] Commit: `feat(session-06): Ignition SCADA with Modbus tags and Perspective HMI`

## Next Step

Session 7 — defense in depth: range-check the setpoint **inside the ST program** (the PLC rejects the absurd, not just the firewall), then replay the Session 4/6 attack against the hardened PLC and compare before/after with committed evidence.