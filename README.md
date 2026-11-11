# ot-lab

Personal test bench for industrial (OT) cybersecurity. Start here: [Write-up #1](writeups/writeup-01.md).

Goal: understand, attack and defend a realistic control system, 100% on my own hardware and software, fully legal.

## Architecture

- **PLC**: OpenPLC v4 runtime installed natively on a Raspberry Pi
- **HMI**: Python command-line supervision dashboard (Ignition SCADA was integrated in session 6; its trial license has expired, the CLI HMI is the current supervision layer)
- **Protocol**: Modbus/TCP
- **Lab tooling**: Wireshark, Nmap, pymodbus
- **Defense**: host firewall filtering, connection monitoring, and PLC-side input validation

## Roadmap

- [x] Bench setup (OpenPLC + Python HMI + Modbus/TCP)
- [x] Simulate a tank-level process
- [x] Capture and dissect Modbus traffic
- [x] Test Modbus reads and setpoint writes against the simulated process
- [x] Apply and test firewall filtering and connection monitoring
- [x] Consolidate the lab findings into write-up #1 (recon → attack → defense)
- [x] Integrate an Ignition SCADA layer and observe the attack from supervision
- [x] Harden the PLC itself: setpoint clamped to a valid range on every scan
- [x] Map the bench onto the Purdue model and IEC 62443 zones/conduits, with an honest SL self-assessment
- [ ] Next: authentication/authorization at the protocol layer (mTLS gateway / RBAC), then write-up #2

## Lab journal

- **Session 1**: OpenPLC v4 runtime installed natively on the Pi (no Docker, port 8443).
- **Session 2**: first ST program (tank level control with hysteresis), Modbus/TCP server enabled, variables mapped and read/written from Python.
- **Session 3**: autonomous tank simulation, Modbus traffic captured and dissected frame by frame (FC01/03/06), CLI HMI.
- **Session 4**: reconnaissance (Nmap + register enumeration) and unauthorized setpoint write: pump stuck ON, documented with packet captures.
- **Session 5**: iptables allowlist on ports 502/8443, connection monitor, attack replay blocked, evidence reviewed offline.
- **Session 6**: Ignition SCADA connected, OPC tags, Perspective HMI; the session 4 attack replayed and observed live from supervision.
- **Session 7**: PLC-side setpoint validation; the same attack now produces no process impact.
- **Session 8**: Purdue model mapping, IEC 62443 zones and conduits, SL self-assessment, reusable 62443-4-1 mini-checklist.

## Modbus reader configuration

Copy `scripts/config.example.json` to `scripts/config.json` and set host to the Raspberry Pi's address. The local config.json is ignored by Git, so the address is not committed with the source code. Set port if the Modbus server does not use the default port 502. Only connect to your own isolated lab.

## Modbus connection monitor

Before running `scripts/detect_modbus.py` on the Raspberry Pi, edit its ALLOWLIST with the IP address(es) of authorized Modbus clients. The monitor reports newly established connections to the Pi's local TCP port 502 from addresses outside that list. It does not detect connection attempts dropped before TCP establishment; use firewall/kernel logs for those.

## Why this lab

Industrial products are becoming connected, and their security can't be learned from slides only. This lab is my way of building hands-on experience with the protocols, devices and threat patterns of real OT environments, one experiment at a time, documented openly.

A note on scope: this bench simulates the physical process. Any future physical integration (the separate Rheomix project) follows one non-negotiable rule: hardware interlock and emergency stop on the actuator, and never a network write as a safety function.

## Disclaimer

All experiments are conducted exclusively on hardware and software I own, in an isolated lab network. No third-party systems are ever targeted.