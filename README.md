# ot-lab

[Start here: Write-up #1](writeups/writeup-01.md)

Personal test bench for industrial (OT) cybersecurity.
Goal: understand, attack and defend a realistic control system — 100% on my own hardware and software, fully legal.

## Architecture
- **PLC**: OpenPLC v4 runtime installed natively on a Raspberry Pi
- **HMI**: Python command-line supervision dashboard
- **Protocol**: Modbus/TCP
- **Lab tooling**: Wireshark, Nmap, pymodbus
- **Defense**: host firewall filtering and connection monitoring

## Roadmap
- [x] Bench setup (OpenPLC + Python HMI + Modbus/TCP)
- [x] Simulate a tank-level process
- [x] Capture and dissect Modbus traffic
- [x] Test Modbus reads and setpoint writes against the simulated process
- [x] Apply and test firewall filtering and connection monitoring
- [x] Consolidate the lab findings into [write-up #1](writeups/writeup-01.md)
      (recon → attack → defense)

## Lab journal
- **Day 1**: repo created, hardware ordered.

## Modbus reader configuration
Copy `scripts/config.example.json` to `scripts/config.json` and set `host` to
the Raspberry Pi's address. The local `config.json` is ignored by Git, so the
address is not committed with the source code. Set `port` if the Modbus server
does not use the default port `502`. Only connect to your own isolated lab.

## Modbus connection monitor
Before running `scripts/detect_modbus.py` on the Raspberry Pi, edit its
`ALLOWLIST` with the IP address(es) of authorized Modbus clients. The monitor
reports newly established connections to the Pi's local TCP port `502` from
addresses outside that list. It does not detect connection attempts dropped
before TCP establishment; use firewall/kernel logs for those.

## Why this lab
Industrial products are becoming connected, and their security can't be learned
from slides only. This lab is my way of building hands-on experience with the
protocols, devices and threat patterns of real OT environments — one experiment
at a time, documented openly.

## Disclaimer
All experiments are conducted exclusively on hardware and software I own,
in an isolated lab network. No third-party systems are ever targeted.
