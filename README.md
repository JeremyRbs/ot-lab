# ot-lab

Personal test bench for industrial (OT) cybersecurity.
Goal: understand, attack and defend a realistic control system — 100% on my own hardware and software, fully legal.

## Architecture
- **PLC**: OpenPLC runtime (Raspberry Pi / Docker)
- **HMI**: supervision dashboard
- **Protocol**: Modbus/TCP
- **Attack tooling**: Wireshark, scapy, pymodbus
- **Defense**: network segmentation, filtering, monitoring

## Roadmap
- [ ] Bench setup (OpenPLC + HMI + Modbus/TCP)
- [ ] Simulate a simple process (temperature control)
- [ ] Capture and dissect Modbus traffic
- [ ] Replay and alter commands (attack phase)
- [ ] Implement defenses (segmentation, filtering, monitoring)
- [ ] Write-up #1: recon → attack → defense

## Lab journal
- **Day 1**: repo created, hardware ordered.

## Why this lab
Industrial products are becoming connected, and their security can't be learned
from slides only. This lab is my way of building hands-on experience with the
protocols, devices and threat patterns of real OT environments — one experiment
at a time, documented openly.

## Disclaimer
All experiments are conducted exclusively on hardware and software I own,
in an isolated lab network. No third-party systems are ever targeted.
