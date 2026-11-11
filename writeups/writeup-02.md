# Write-up #2 - Defense in depth on a personal OT bench

## TL;DR

Write-up #1 ended on an open problem: my firewall filters hosts, but any accepted client could still write anything to the process. The Session 5 capture itself contains nine successful malicious writes from the authorized PC. This write-up covers how I worked on that. First I added a commercial SCADA (Ignition) and checked whether it improved security. It did not, but it improved detection. Then I moved input validation into the PLC program itself, which neutralized the same attack that previously kept a pump stuck ON. Finally I mapped the bench to IEC 62443 (Purdue model, zones and conduits) to name what is protected and what still is not.

Scope: personal, isolated lab, simulated process. No third-party system, no physical equipment controlled.

## 1. Where write-up #1 left us

The bench: OpenPLC v4 on a Raspberry Pi, Structured Text tank program, Modbus/TCP on 502, attacker workstation on the same LAN. In Session 4, a single FC06 request (value 200 to register 1024) was enough to keep the simulated pump ON indefinitely, because the stop threshold became unreachable. Session 5 added perimeter defenses: iptables allowlist, connection monitoring, kernel logging. That worked against other hosts. It also showed its own limit, with committed evidence: a malicious program running on the trusted PC writes freely.

I had three questions to work through:

1. Does adding a SCADA layer improve security?
2. Can the PLC itself reject invalid values?
3. How does the result map to IEC 62443, the standard the industry actually uses?

## 2. Session 6 - Trying a SCADA

I connected Ignition (trial edition) to the PLC over Modbus/TCP, exposed the process variables as OPC UA tags, and built a small Perspective HMI: live tank level, bidirectional setpoint entry (limited 0-100 in the HMI), pump indicator, overflow alarm.

Then I replayed the Session 4 attack with the SCADA open. Screenshots are committed: the setpoint field displayed 200, the tank saturated at 100, the pump stayed ON, and the alarm triggered.

The HMI's own 0-100 limit did nothing. In hindsight that makes sense: the attack never goes through the HMI, it writes the PLC directly. So the SCADA did not improve prevention at all. What it did improve was detection. My alarm expression (`level >= 100 && pump ON`) fired from supervision, even though the control program has no such check. The simulated high-level sensor input (`%IX0.0`) stays FALSE because nothing drives it in the simulation. I had not planned that contrast, it came out of the test, and it is probably the most useful thing I learned in this session: detection and prevention are different jobs, and I now have evidence of both on the same attack.

One configuration fight is worth documenting because I lost time on it. Ignition 8.3 routes Modbus Unit IDs through a device-level Address Mapping table. My first mapping row was incomplete, and every request left with Unit ID 0, which OpenPLC rejects: `requested device id does not exist: 0`, exception `0x83 0x0B` (visible in the runtime logs on the Pi). The fix is entirely on the SCADA side, I did not touch OpenPLC. Related trap: the "zero-based addressing" setting does not produce an error when it is wrong. It produces a plausible wrong value (0 instead of 50). My rule now: no tag is trusted until it has been validated against a known value. Full details in [session-06](../docs/session-06.md).

## 3. Session 7 - Validation inside the PLC

The fix for the actual vulnerability had to live where the commands are executed. The hardened program now validates the setpoint at the top of every scan, before any control logic uses it:

```iecst
(* Session 7 *)
IF setpoint > 100 THEN
    setpoint := 100;
ELSIF setpoint < 0 THEN
    setpoint := 0;
END_IF;
```

Two choices I made deliberately.

First, clamp instead of reject. The process always runs with a defined setpoint, there is no undefined state. The cost is that attacker input is silently accepted, then corrected. The alternative (reject the write, raise an alarm, keep the last valid setpoint) gives better auditability but needs more machinery in a simple ST program. I chose the clamp for the bench and documented the trade-off. On a real machine this choice would come from the safety review, not from preference.

Second, validate every scan, not once at startup. A value corrupted after boot gets re-validated within 20 ms.

Then I replayed the exact same attack, same 12-byte FC06 request with value 200, with the HMI open. Committed before/after:

| | Unhardened PLC (S4/S6) | Hardened PLC (S7) |
|---|---|---|
| FC06 write of 200 | Accepted; setpoint reads 200 | Accepted by the protocol, **neutralized by the PLC**: reads 100 |
| Setpoint on HMI | 200 | 100 |
| Pump | Stuck ON indefinitely | Normal behavior |
| Overflow alarm | Triggered | Not triggered |

What surprised me: the traffic is byte-identical before and after. Wireshark cannot tell the difference. The defense is invisible at the protocol layer and decisive at the process layer, which is why packet captures alone would never show my own defense working.

What this does not cover, stated plainly: a malicious write of a valid value (setpoint 100 when the operator wants 20) passes the clamp, the firewall, and the HMI. Only authentication and authorization can address that, and Modbus has never had them. That is the remaining gap on this bench, documented rather than hidden.

## 4. Session 8 - Naming things with IEC 62443

I mapped the bench onto the Purdue model ([annotated diagram](../captures/session8-purdue.png)) and formalized it per IEC 62443-3-2:

| Zone / Conduit | Assets | Safeguards | Residual risk |
|---|---|---|---|
| Z1 - Control | Pi, OpenPLC runtime, ST program | ST clamp (S7); hardened runtime; no IT connectivity | No auth; physical process simulated |
| Z2 - Operations | PC: HMI, clients, attack tooling | Host hygiene (assumed) | Proven writable-by-malware (S5) |
| C1 - Modbus conduit | TCP/502 control traffic | iptables allowlist + LOG + session monitor (S5) | IP spoofing untested; no crypto |
| C2 - Engineering conduit | TCP/8443 deployment | iptables allowlist; HTTPS self-signed | No mTLS. Worst-case path: program replacement |

I also did a Security Level self-assessment, kept honest: SL 1 achieved (casual misuse blocked), SL 2 partial (no authentication anywhere, ARP/IP spoofing untested), SL 3+ out of scope for a home bench.

Doing this changed how I talk about the project. "Is it secure?" is a question I can no longer answer seriously. "What security level does each zone and conduit achieve, and what is the residual risk?" is one I can. The exercise also produced a reusable [62443-4-1 mini-checklist](../docs/session-08.md): ten practices, from threat modeling to lifecycle patching, each tied to something I actually tested on the bench.

## 5. The defense stack, end to end

| Layer | Mechanism | Covers | Proven by |
|---|---|---|---|
| Network | iptables allowlist 502/8443, kernel LOG, persisted across reboot | Unauthorized hosts | Session 5 (SYNs logged and dropped) |
| Monitoring | `ss`-based allowlist detector + SCADA alarm expressions | Unexpected sessions and states | Sessions 5-6 |
| Application | ST range clamp, every scan | Invalid values from any source | Session 7 (before/after) |
| Protocol | nothing. Modbus has no authentication, by design | Unauthorized valid writes | Documented gap |
| Safety | would be: hardware interlock + E-stop. Not implemented, simulated process | Physical consequences | Rule stated in README; deferred with the physical-process phase |

Each layer covers a failure mode the previous one does not. None is sufficient alone, and the stack is only as good as my assessment of what it does not cover.

## 6. Lessons learned

- Validate at the point of use. The firewall and the HMI both proved necessary and both proved insufficient. The layer that commands the process is the one that has to check its inputs.
- Packet captures do not show my defenses working. The attack traffic is identical before and after hardening, so I need process-level evidence (values, states, timelines), not only network-level evidence.
- The SCADA added detection, not prevention. Its alarm caught a state the PLC tolerated. Both facts belong in the same sentence.
- Mapping the lab to Purdue/62443 took one evening and gave me the vocabulary (zones, conduits, SL targets, residual risk) to discuss someone else's architecture in their own terms. I did not expect the documentation work to teach as much as the attack work did.
- Writing down the gaps ("SL 2 partial: no authentication") was more useful than I expected. It turns a vague worry into the next concrete work item.

## 7. Reproduction and scope

- All scripts read their target from `scripts/config.json` (template provided, git-ignored). Point it only at your own isolated lab.
- The attack path is a single Modbus write on a simulated process. Re-running it against anything you do not own is unethical and illegal in most jurisdictions.
- Ignition ran on a trial license and is no longer active; the supervision slot is held by the CLI HMI. The zone architecture is unchanged. Free alternatives (Scada-LTS, FUXA) can refill the SCADA slot if a live demo is ever needed.

## Evidence index

| Evidence | File |
|---|---|
| Perimeter defense, monitoring, replay | [docs/session-05.md](../docs/session-05.md), [captures/session5-rules.txt](../captures/session5-rules.txt), [captures/session5-defense.pcapng](../captures/session5-defense.pcapng) |
| SCADA connection, tags, HMI, attack seen from supervision | [docs/session-06.md](../docs/session-06.md) + committed screenshots |
| PLC-side clamp, hardened attack replay | [docs/session-07.md](../docs/session-07.md) + committed screenshots |
| Purdue diagram, zones/conduits, SL assessment, 4-1 checklist | [docs/session-08.md](../docs/session-08.md), [captures/session8-purdue.png](../captures/session8-purdue.png) |
| Baseline (attack and first defense) | [writeups/writeup-01.md](./writeup-01.md) |