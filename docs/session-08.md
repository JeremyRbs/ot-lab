# Session 8 — IEC 62443 Applied to the Bench: Zones, Conduits, and a Purdue Diagram

> File: `docs/session-08.md` — commit at the root of the `ot-lab` repository.

## Objective

Formalize the bench's security architecture the way the industry does it: map the lab onto the Purdue reference model, define IEC 62443 zones and conduits, and produce a reusable 62443-4-1 mini-checklist. Everything below is derived from the *actual* bench built in Sessions 1–7 — this is not a textbook diagram, it is the lab's own architecture, annotated.

Note: the Ignition SCADA (Session 6) ran on a trial license and is no longer active. The supervision layer is currently the CLI HMI (`scripts/hmi.py`). The architecture below documents both the as-built state and the SCADA slot it occupied — the zone structure does not change.

## 1. The Bench on the Purdue Model

```mermaid
flowchart TB
  subgraph L5["Level 5 — Enterprise Network"]
    INTERNET["Internet / updates"]
  end

  subgraph L4["Level 4 — Site Business (not present on this bench)"]
    IT["IT systems — none deployed"]
  end

  subgraph L3["Level 3 — Site Operations"]
    PC["Operator / engineering workstation<br/>192.168.1.50<br/>pymodbus clients · Wireshark · Nmap · OpenPLC Editor<br/>(former slot: Ignition SCADA)"]
  end

  subgraph L2["Level 2 — Supervision (embedded in L3 host here)"]
    HMI["CLI HMI — scripts/hmi.py<br/>read-only FC01/FC03"]
  end

  subgraph L1["Level 1 — Basic Control"]
    PLC["OpenPLC Runtime v4 on Raspberry Pi<br/>192.168.1.120 · ST tank program · 20 ms scan<br/>Modbus/TCP server :502 · mgmt API :8443"]
  end

  subgraph L0["Level 0 — Process (simulated)"]
    TANK["Tank + pump<br/>%MW1 level · %QX0.0 pump · %IX0.0 sensor"]
  end

  PC -->|"Conduit C1 — Modbus/TCP :502 (FC01/03/06)<br/>+ HTTPS :8443 (engineering)"| PLC
  HMI -.->|"runs on PC"| PC
  PLC -->|"process image"| TANK
  INTERNET -.->|"no path — bench isolated from IT"| L4
```

Reading of the diagram:

- **Levels 5 and 4 are empty by design.** The bench has no enterprise network and no IT systems — it is isolated, which is itself a 62443 posture (no unnecessary connectivity).
- **Levels 3 and 2 collapse onto one machine.** The operator workstation hosts both engineering tools (Editor, scripts, Wireshark) and the supervision HMI. In a real plant these are separated; on a one-person bench, documenting the collapse honestly is better than drawing a fiction.
- **Level 0 is simulated.** The tank/pump exist as PLC memory. Sessions 9–10 (Rheomix) will make Level 0 physical.

## 2. Zones and Conduits (62443-3-2 Reading)

| Zone | Assets | Criticality / rationale | Current safeguards |
|---|---|---|---|
| **Z1 — Control zone** | Raspberry Pi: OpenPLC runtime, ST program, Modbus server | Highest — it commands the (future) physical process | ST setpoint clamp (S7); hardened runtime; no inbound IT connectivity |
| **Z2 — Operations zone** | PC: HMI, pymodbus clients, Wireshark, OpenPLC Editor | Medium — trusted host, but proven writable-by-malware (S5: nine FC06 from this host) | Host firewall hygiene assumed; no malware controls (documented gap) |
| **C1 — Modbus conduit** | TCP/502 traffic PC ↔ Pi | Carries control writes — the attack path of Sessions 4–7 | iptables allowlist (S5) + connection monitor (S5) + kernel LOG |
| **C2 — Engineering conduit** | TCP/8443 traffic PC ↔ Pi | Carries program deployment — worst-case path (program replacement) | iptables allowlist (S5); HTTPS with self-signed cert (no mTLS) |
| **C3 — Process conduit** | PLC internal: process image ↔ simulated I/O | Internal to Z1 | ST logic; (future: hardware interlock with Rheomix) |

Key 62443 insight the bench demonstrates: **a conduit is secured, not trusted.** C1 is allowlisted, yet Sessions 4–7 proved that a compromised Z2 host attacks through it anyway — hence the S7 application-layer defense inside Z1. Zones contain; conduits filter; neither replaces validation at the point of use.

## 3. Security Levels — Where the Bench Stands

IEC 62443 defines SL 1–4 per zone/conduit. Honest self-assessment:

| Target | Status |
|---|---|
| SL 1 (protection against casual misuse) | **Achieved** on C1/C2 (allowlist) and Z1 (input validation) |
| SL 2 (intentional violation by low capability) | **Partial** — no authentication anywhere; a motivated attacker on the LAN with the PC's IP (spoofing) bypasses the allowlist; ARP spoofing untested |
| SL 3+ (sophisticated actor) | **Not targeted** — out of scope for a home bench; the gap is documented, not hidden |

The SL framing is the interview answer: *not* "is it secure?" but "what security level does each zone/conduit achieve, and what is the residual risk?" 

## 4. IEC 62443-4-1 Mini-Checklist (Reusable Artifact)

62443-4-1 defines the *secure development lifecycle* a product maker must run. Condensed to the questions a machine-builder's BE can act on — this is the "mini-outil open source" format of the public-proof plan:

| # | 62443-4-1 practice | Question for a machine builder | Evidence to ask for |
|---|---|---|---|
| 1 | Security requirements (SR) | Are security requirements derived from a threat model, or copied from a datasheet? | Threat model doc; SR traceability |
| 2 | Secure architecture | Are zones/conduits designed into the product, or is security a firewall sold alongside? | Architecture doc with zones; SL targets |
| 3 | Input validation | Does the PLC/controller reject out-of-range or malformed commands? (Bench proof: S7 clamp) | Range-check code; fuzz/abuse test results |
| 4 | Authentication | Can any network client write control values? (Bench: yes — documented gap) | Auth design (per-user, per-role); no shared passwords |
| 5 | Access control / RBAC | Are engineering vs operator rights separated? | Role matrix; default-deny evidence |
| 6 | Update mechanism | Is there a signed, authenticated firmware/software update path? | Update spec; signing keys handling |
| 7 | Vulnerability handling | Is there a PSIRT/contact and a disclosure policy? | Policy URL; SBOM availability |
| 8 | Cryptography | Are crypto choices documented and updatable (post-quantum inventory)? | Crypto inventory |
| 9 | Logging / detection | Does the product log security events (failed logins, unexpected writes)? | Log spec; bench analog: S5 kernel LOG + monitor |
| 10 | Lifecycle | Are patches promised for the machine's 10–20 year life? | Support policy per product line |

Usage: this table is the CRA-adjacent conversation starter with a fabricant type Pinette PEI — ten questions that map a supplier's maturity without reading the standard.

## 5. What This Session Does and Does Not Prove

- The Purdue mapping and zone/conduit split are **documentation of the real bench**, each box traceable to a session's evidence — not an idealized design.
- The SL self-assessment is the author's, on a simulator; it is a learning artifact, not an assessment of any commercial product.
- The 62443-4-1 checklist is a study summary for engineering conversations, not the standard itself (the full text is copyrighted; the practices above are paraphrased).

## Session Deliverables

- [x] Purdue diagram of the bench, annotated with real IPs, ports, and session references
- [x] Zones and conduits table with current safeguards and known gaps
- [x] Security Level self-assessment (SL 1 achieved, SL 2 partial, gaps named)
- [x] 62443-4-1 mini-checklist (10 practices, reusable format)
- [x] Commit: `docs(session-08): IEC 62443 zones/conduits, Purdue diagram and 4-1 mini-checklist`

## Next Step

Sessions 9–10 — Rheomix as the physical process: ADS1115 + clamp sensor acquisition into the PLC image, relay command with hardware interlock and emergency stop, then the physical-impact attack scenario for write-up #2.