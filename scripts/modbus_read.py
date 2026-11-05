
import json
from pathlib import Path

from pymodbus.client import ModbusTcpClient

CONFIG_PATH = Path(__file__).with_name("config.json")


def load_config():
    if not CONFIG_PATH.is_file():
        raise FileNotFoundError(
            "Configuration file not found. Copy scripts/config.example.json "
            "to scripts/config.json and enter the Raspberry Pi's address."
        )

    with CONFIG_PATH.open(encoding="utf-8") as config_file:
        config = json.load(config_file)

    host = config.get("host")
    port = config.get("port", 502)

    if not isinstance(host, str) or not host.strip() or host == "CHANGE_ME":
        raise ValueError("Enter a valid address in scripts/config.json.")

    if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
        raise ValueError("The port in scripts/config.json must be between 1 and 65535.")

    return host.strip(), port


def read_value(response, attribute, count=1):
    """Return the requested Modbus value, or a readable error."""
    if response is None:
        return "No response"

    if response.isError():
        return f"Modbus error: {response}"

    values = getattr(response, attribute, None)
    if values is None:
        return "Unexpected response"

    return values[:count]


def main():
    host, port = load_config()
    client = ModbusTcpClient(host, port=port, timeout=3)

    try:
        if not client.connect():
            raise ConnectionError(
                f"Could not connect to Modbus server at {host}:{port}."
            )

        # Initialize the process: setpoint := 50, tank empty
        client.write_register(1024, 50, device_id=1)   # setpoint (%MW0)
        client.write_register(1025, 0, device_id=1)     # level (%MW1) — tank empty

        print("Filling... watch the level climb (pump adds 1 unit per PLC scan)")

        import time
        for _ in range(12):
            r_setpoint = client.read_holding_registers(1024, count=1, device_id=1)
            r_level    = client.read_holding_registers(1025, count=1, device_id=1)
            r_pump     = client.read_coils(0, count=1, device_id=1)
            print(
                "setpoint:", read_value(r_setpoint, "registers"),
                "| level:", read_value(r_level, "registers"),
                "| pump:", read_value(r_pump, "bits"),
            )
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        client.close()


if __name__ == "__main__":
    main()