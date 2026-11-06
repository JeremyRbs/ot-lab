"""Read mapped Modbus data from an authorized, isolated lab PLC."""

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
        print("--- Reading holding registers (%MW area) ---")
        for addr in range(1024, 1050):
            rr = client.read_holding_registers(addr, count=1, device_id=1)
            if rr.isError():
                print(f"Register {addr}: read error")
            else:
                print(f"Register {addr}: {rr.registers[0]}")

        print("--- Reading coils ---")
        for addr in range(0, 8):
            rc = client.read_coils(addr, count=1, device_id=1)
            if rc.isError():
                print(f"Coil {addr}: read error")
            else:
                print(f"Coil {addr}: {'ON' if rc.bits[0] else 'OFF'}")
    except KeyboardInterrupt:
        print("\nReconnaissance stopped.")
    finally:
        client.close()

if __name__ == "__main__":
    main()