# Session 5: Firewall filtering and modbus connection monitoring

## Objective

Restrict access to the OpenPLC management and Modbus/TCP ports, monitor
established Modbus clients, and verify firewall logging and blocking. Testing
used the isolated lab only. The Raspberry Pi was `192.168.1.120`; the sole PC
client was `192.168.1.50`.

## 1. Baseline firewall rules

The reported `iptables` INPUT chain has the following order:

| # | Port | Rule | Effect |
|---:|---:|---|---|
| 1 | TCP/502 | Accept source `192.168.1.50` | Permit the authorized PC to use Modbus |
| 2 | TCP/502 | Log, limited to 5/minute with burst 5 | Log other matching packets with prefix `MODBUS-DROP:` |
| 3 | TCP/502 | Drop | Block other Modbus traffic |
| 4 | TCP/8443 | Accept source `192.168.1.50` | Permit the authorized PC to reach OpenPLC management |
| 5 | TCP/8443 | Drop | Block other management traffic |

The INPUT chain's default policy is ACCEPT; these rules specifically filter
TCP/502 and TCP/8443. SSH/TCP/22 is not changed by this ruleset. The original
baseline listing and its counters are saved in
[`../captures/session5-rules.txt`](../captures/session5-rules.txt). The
operator later supplied a post-reboot `iptables -L -n` listing with the same
five INPUT rules in the same order, confirming IPv4 rule persistence on this
Pi.

## 2. Established-connection monitor

[`../scripts/detect_modbus.py`](../scripts/detect_modbus.py) polls `ss` once per
second for established sockets whose local/source port is 502. It compares
remote addresses with an allowlist; the authorized PC is
`192.168.1.50`. It alerts when an unexpected client appears and reports when
that client disappears.

The monitor detected the PC while it was running the HMI and temporarily
excluded from the allowlist. It alerted once for that connection; it does not
repeat the alert every polling interval. The parser was corrected to handle
the four-column, headerless `ss -Htn` output observed on the Pi.

This is session-level monitoring, not per-command auditing. A short-lived
connection may begin and end between polls, and an established connection from
an allowed address is not classified as unexpected. Firewall logs complement
the monitor by recording packets dropped before a TCP connection is
established.

## 3. Controlled firewall test

There was only one PC, and it was normally allowlisted. To test the deny/log
path without another client, temporary rules were inserted before the baseline
rules to log and drop that PC's traffic to TCP/502. The temporary rules were
removed after the test; they are not part of the baseline rules file and were
not intended to be saved persistently.

The temporary test rules were:

```bash
sudo iptables -I INPUT 1 -p tcp --dport 502 -s 192.168.1.50 \
  -m limit --limit 5/min --limit-burst 5 \
  -j LOG --log-prefix "MODBUS-TEST-DROP: " --log-level 4
sudo iptables -I INPUT 2 -p tcp --dport 502 -s 192.168.1.50 -j DROP
```

They were removed by matching the rules:

```bash
sudo iptables -D INPUT -p tcp --dport 502 -s 192.168.1.50 \
  -m limit --limit 5/min --limit-burst 5 \
  -j LOG --log-prefix "MODBUS-TEST-DROP: " --log-level 4
sudo iptables -D INPUT -p tcp --dport 502 -s 192.168.1.50 -j DROP
```

The operator observed these kernel log entries at approximately 16:50:58:

```text
MODBUS-TEST-DROP: IN=wlan0 ... SRC=192.168.1.50 DST=192.168.1.120 ... PROTO=TCP SPT=31094 DPT=502 ... SYN
MODBUS-TEST-DROP: IN=wlan0 ... SRC=192.168.1.50 DST=192.168.1.120 ... PROTO=TCP SPT=31094 DPT=502 ... SYN
```

The two logged SYN packets are connection attempts from the PC to the Modbus
port. The operator reported removing the temporary rules afterward and
restoring the baseline access.

## 4. PCAPNG evidence and interpretation

Capture: [`../captures/session5-defense.pcapng`](../captures/session5-defense.pcapng)

Offline parsing found 64,695 Ethernet frames over about 17 minutes 36 seconds.
The capture contains 1,302 FC01 requests and responses, 1,330 FC03 requests
with 1,329 responses, and nine FC06 requests and responses, as well as the
firewall-test TCP SYNs. One FC03 request has no captured response; the capture
alone does not identify the reason.

At approximately **16:50:57.788** and **16:50:58.800**, the capture shows
SYN packets from `192.168.1.50:31094` to `192.168.1.120:502`. No SYN-ACK for
that source port appears in the capture. This agrees with the temporary
firewall DROP test and the corresponding `MODBUS-TEST-DROP` kernel messages.
No Modbus FC06 write is present in that blocked connection attempt. The PCAP
supports a blocked TCP connection attempt; the kernel log provides the
explicit firewall log-prefix evidence.

The capture also includes traffic from periods when the baseline rule allowed
the PC. It contains nine successful FC06 writes of 200 to holding register
1024, each with a response. These writes are not evidence of a bypass: they
came from the allowlisted PC during other parts of the long capture. The
firewall is an IP-based filter, so any program running on the authorized PC
can still write Modbus values.

The capture's holding-register reads show setpoint **200** and level **100**;
coil 0 is ON in most captured responses. Therefore the process was still at
the prior Session 4 test values during this capture. The firewall test does
not itself reset the simulated process. A later setpoint restoration and
state verification are documented below.

A fresh read-only Modbus check on 2026-11-06 also returned setpoint 200, level
100, and coil 0 ON. The original checklist's level-below-60 criterion is not a
valid stable-state expectation for this fill-only model: it has no drain, and
below the setpoint the PLC turns the pump on until the level reaches 60
(setpoint + 10). With the level already at 100, lowering the setpoint leaves
it capped at 100 and turns the pump off. This setpoint-50, level-100, pump-OFF
state was accepted as the safe resting state; the level register was not
written.

The requested setpoint restoration was then performed over Modbus. The write
to holding register 1024 was acknowledged, and a verification read one second
later returned setpoint 50, level 100, and pump OFF. No level-register write
was made. This stops the simulated pump but does not reduce the simulated
level.

## 5. Session 4 vs. session 5

| Test | Session 4: no temporary deny rule | Session 5: temporary deny rule for `.50` |
|---|---|---|
| Modbus access from `.50` | Reads and writes accepted | TCP SYN attempts logged and dropped during the test window |
| Unauthorized established connection | Not monitored | `detect_modbus.py` alerts on an unexpected established client that remains visible to polling |
| Short blocked connection attempt | No firewall deny evidence | SYNs visible in the capture and `MODBUS-TEST-DROP` in the kernel log |
| Process state | Setpoint changed to 200; level capped at 100; pump ON | Capture still shows 200/100; the blocked connection did not reset the prior state |

The deny test used a temporary rule to block the only PC, which was otherwise
the authorized client. It demonstrates the rule and logging path but is not a
test from a second, independently addressed untrusted device. The result should
not be generalized to clients on other networks or interfaces without testing
those paths.

## Limitations and follow-up

- The firewall rule listing is operator-supplied and saved as a transcription;
  it was not queried directly by this repository review. The operator supplied
  the post-reboot output, which is preserved in
  [`../captures/session5-rules.txt`](../captures/session5-rules.txt).
- `iptables-persistent` was already installed; the operator reported saving
  with `netfilter-persistent`, rebooting, and seeing the same IPv4 INPUT rules
  afterward. This confirms persistence for the displayed rules, not behavior
  from an untrusted client or IPv6 filtering.
- After reboot, `Test-NetConnection 192.168.1.120 -Port 502` from the PC at
  `192.168.1.50` returned `TcpTestSucceeded: True`. This confirms permitted
  TCP/502 reachability from the authorized PC; it does not test the deny path
  from another client or TCP/8443.
- The follow-up read-only check first confirmed the Session 4 test values
  (setpoint 200, level 100, pump ON). Afterward, the requested setpoint write
  was made; verification returned setpoint 50, level 100, pump OFF.
- The simulation has no drain. With setpoint 50, the current capped level 100
  remains unchanged and the pump is OFF, which is a stable resting state.
  A level below 60 is not needed for this safe state and would require an
  additional level-register write or a model change; neither was made.
- No second client device was available. The temporary source-specific deny
  rule was used to exercise the block/log path from the existing PC.
- The monitor detects established sessions, not every Modbus operation or
  every SYN. Rate-limited kernel logging and packet capture cover different
  parts of the detection story.
- The PCAP contains accepted writes outside the deny-test window. Analyze the
  timestamp and flow before interpreting any packet as part of the blocked
  attempt.
- No physical Rheomix or pump was controlled. Keep the simulator and physical
  process safely separated.

## Verification

- `session5-defense.pcapng` was parsed offline; no Modbus write or firewall
  rule was applied during PCAP analysis.
- The detector's `ss` parser was tested against the four-column line supplied
  from the Pi, yielding remote peer `192.168.1.50`.
- The operator supplied the firewall log lines and reported removal of the
  temporary test rules.
- The operator supplied the post-reboot IPv4 firewall listing and the
  successful TCP/502 connectivity test from the authorized PC.
- A fresh read-only Modbus check on 2026-11-06 confirmed setpoint 200, level
  100, and pump ON. The explicitly requested setpoint write then returned an
  acknowledged response; after one second the readback was setpoint 50, level
  100, and pump OFF. No level-register write was sent.
- The read-only `hmi.py` display then repeatedly showed level 100, setpoint 50,
  and pump OFF.

## Session deliverables

- [x] Baseline INPUT rules recorded in `captures/session5-rules.txt`
- [x] `scripts/detect_modbus.py` monitors established Modbus client sessions
- [x] Temporary deny test produced kernel log entries and captured SYNs
- [x] `captures/session5-defense.pcapng` reviewed and findings documented
- [x] Before/after comparison documented with single-client limitation
- [x] Confirm IPv4 INPUT rule persistence after reboot from the supplied
      post-reboot listing
- [x] Restore setpoint to 50 and verify the stable simulated resting state:
      level 100, pump OFF; no level-register write