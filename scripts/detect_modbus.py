"""Alert when an established Modbus/TCP client is outside the allowlist."""

import ipaddress
import subprocess
import time

ALLOWLIST = {"192.168.1.50"}  # Authorized HMI workstation.
MODBUS_PORT = 502
POLL_INTERVAL_SECONDS = 1


def parse_endpoint(endpoint):
    """Return the IP address and port from an ss endpoint such as [::1]:502."""
    if endpoint.startswith("["):
        host, separator, port = endpoint[1:].partition("]:")
        if not separator:
            raise ValueError(f"Unrecognized ss endpoint: {endpoint}")
    else:
        host, separator, port = endpoint.rpartition(":")
        if not separator:
            raise ValueError(f"Unrecognized ss endpoint: {endpoint}")

    if "%" in host:
        host = host.split("%", 1)[0]

    address = ipaddress.ip_address(host)
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped

    return str(address), int(port)


def parse_connections(output):
    """Extract remote IPs from established sockets whose local port is Modbus."""
    peers = set()
    for line in output.splitlines():
        fields = line.split()
        # `ss -H` omits the header and state, leaving four endpoint/queue fields.
        if len(fields) < 4:
            continue

        # The local and peer endpoints are the final two fields.
        _, local_port = parse_endpoint(fields[-2])
        if local_port != MODBUS_PORT:
            continue

        peer_address, _ = parse_endpoint(fields[-1])
        peers.add(peer_address)

    return peers


def connections():
    """Return remote IPs with established TCP sockets to the local Modbus port."""
    result = subprocess.run(
        [
            "ss",
            "-Htn",
            "state",
            "established",
            f"( sport = :{MODBUS_PORT} )",
        ],
        capture_output=True,
        text=True,
        timeout=5,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or f"exit status {result.returncode}"
        raise RuntimeError(f"Failed to query ss: {detail}")

    return parse_connections(result.stdout)


def main():
    allowlist = {str(ipaddress.ip_address(address)) for address in ALLOWLIST}
    unexpected_previous = set()

    print(f"[DETECT] Monitoring established TCP connections on port {MODBUS_PORT}...")
    try:
        while True:
            unexpected = connections() - allowlist
            for address in sorted(unexpected - unexpected_previous):
                print(f"[ALERT] Unexpected Modbus client: {address}", flush=True)

            for address in sorted(unexpected_previous - unexpected):
                print(f"[INFO] Unexpected Modbus client disconnected: {address}", flush=True)

            unexpected_previous = unexpected
            time.sleep(POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\n[DETECT] Monitoring stopped.")


if __name__ == "__main__":
    main()
