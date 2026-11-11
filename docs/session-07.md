# Session 7: Defense in depth, PLC-Side setpoint validation

## Objective

Harden the PLC itself: the controller now rejects physically invalid setpoints instead of executing them. The Session 4/6 attack (FC06 write of 200 to the setpoint register) is then replayed against the hardened program, with the Ignition HMI as the live witness. This closes the gap that Sessions 4–6 exposed: the firewall filters *who* connects, but any accepted client could still push the process out of bounds.

## 1. The hardened ST program

Range validation added at the top of the scan cycle, *before* any control logic uses the value ([screenshot](../captures/session7-OpenPLC_code_hardened.png)):

```iecst
(* (Session 7) *)
IF setpoint > 100 THEN
    setpoint := 100;
ELSIF setpoint < 0 THEN
    setpoint := 0;
END_IF;
```

Design points:

- **Clamp, not reject**: an out-of-range value is corrected to the nearest valid bound rather than discarded. The process always runs with a defined setpoint; there is no undefined state.
- **Executed every scan (20 ms)**: even if a valid value is later corrupted in memory, the next scan re-validates it. The check is part of the control loop, not a one-shot filter at startup.
- **Layer position**: this is the innermost defense. The Session 5 firewall is the outermost. An attacker who crosses the network layer still hits the PLC's own validation.

After deploy: `PLC State: RUNNING`, 20 ms base tick, plugin map unchanged (`%MW=1024-2047`, coils `%QX=8`).

## 2. Attack replay against the hardened PLC

`scripts/attack_overflow.py` (unchanged: same 12-byte FC06 request, value 200 to register 1024) was replayed with the Ignition Perspective session open.

Observed on the HMI ([screenshot](../captures/session7-IHM_blocked_attack.png)):

| | Session 4/6 (unhardened PLC) | Session 7 (hardened PLC) |
|---|---|---|
| FC06 write of 200 | Accepted; setpoint reads 200 | **Accepted by the protocol** (echoed), but **neutralized by the PLC**: setpoint reads **100** |
| Setpoint displayed on HMI | 200 | **100** |
| Level | Saturates at 100, capped | 0 (tank empty; pump never started) |
| Pump | Stuck ON indefinitely | **OFF** |
| Overflow alarm | Triggered | **Not triggered** |

Interpretation, important to state precisely:

- **Modbus still accepted the write.** The protocol layer has no validation and never will: the FC06 request and its echo are byte-identical to the Session 4 attack. Range checking does not exist in classic Modbus/TCP.
- **The PLC neutralized it.** The value 200 reached `%MW0`, and the ST clamp corrected it to 100 within one scan. The *process* never saw the invalid value.
- **The impact disappeared.** With setpoint 100 and level 0, the pump legitimately starts and fills toward the (now valid) target. In the captured screenshot the pump is OFF because the level had not yet risen / the run had just started. No stuck-ON state, no overflow condition, no alarm.

This is the "before/after" pair for the write-up: same attack, same wire bytes, completely different process outcome.

## 3. Defense layers now on the bench

| Layer | Mechanism | Blocks |
|---|---|---|
| Network (Session 5) | iptables allowlist on 502/8443 + connection monitor | Unauthorized *hosts* |
| Protocol | (nothing; Modbus has no auth/validation, by design) | (n/a) |
| Application (Session 7) | ST range clamp on every scan | Physically invalid *values* from any source, including trusted hosts |

The third layer closes the exact hole documented in Session 5: a malicious program running on the *authorized* PC could write anything. It still can, but a setpoint of 200 no longer produces a stuck pump. What it *cannot* yet stop: a malicious write of a *valid* value (e.g., setpoint 100 when the operator wants 20). That requires authentication and authorization, i.e., the protocol layer: the known next step (mTLS gateway / RBAC), not implemented in this session.

## 4. What this session does and does not prove

- Proven with committed evidence: the hardened ST neutralizes an out-of-range setpoint write within one scan; the same attack produces no process impact; the HMI reflects the sanitized value (100), not the injected one (200).
- Not proven: protection against in-range malicious values (no authentication exists at the Modbus layer); behavior under other attack vectors (e.g., writing `level` directly; `%MW1` is still writable, which is a simulation artifact and would be a read-only physical input on real hardware); the mTLS/RBAC gateway option (documented as follow-up, not implemented).
- The clamp bounds are hardcoded (0–100) because the process is simulated. On a real machine, valid ranges come from the process specification and safety analysis, and clamping limits belong in the safety review: a wrong bound in code is itself a defect.

## 5. Lessons learned

- **Validate at the point of use.** The only layer that can reliably protect the process is the one that commands it. HMI limits (Session 6) and network rules (Session 5) are necessary; neither is sufficient alone.
- **Defense in depth is a topology, not a slogan.** Each layer covers the failure mode of the previous one. Firewall → covers untrusted hosts. PLC clamp → covers trusted hosts sending garbage. Authentication (missing) → would cover trusted hosts sending valid-but-unauthorized values.
- **The wire does not change; the outcome does.** Byte-identical attack traffic before and after hardening: the difference is invisible to Wireshark and decisive for the process. Detection and prevention live at different layers.
- **Clamping is a design decision, not a patch.** Clamp-to-nearest keeps the process defined; it also silently accepts attacker input. An alternative (reject + alarm + hold last valid setpoint) trades availability for auditability. I had to make that trade-off explicitly for a simulated tank; on a real product it belongs to the safety review.

## Session deliverables

- [x] ST program hardened: setpoint clamped to [0, 100] every scan (screenshot committed)
- [x] Attack replayed against hardened PLC; HMI screenshot committed (setpoint 100, pump OFF, no alarm)
- [x] Before/after comparison table (Sessions 4/6 vs 7)
- [x] Defense-layer inventory with the remaining gap (in-range writes) explicitly stated
- [x] Commit: `feat(session-07): PLC-side setpoint validation neutralizes out-of-range writes`

## Next step

Session 8: IEC 62443 applied to the bench, zones and conduits (operator PC / Modbus conduit / PLC zone), an annotated Purdue-model diagram of this own lab, plus a reusable 62443-4-1 mini-checklist. Follow-ups carried over: mTLS/RBAC gateway experiment (protocol-layer defense), and Rheomix as the physical process (Sessions 9–10).