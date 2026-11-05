
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

        r_setpoint = client.read_holding_registers(1024, count=1, device_id=1)
        r_level = client.read_input_registers(0, count=1, device_id=1)
        r_sensor = client.read_discrete_inputs(0, count=1, device_id=1)
        r_pump = client.read_coils(0, count=1, device_id=1)

        print("--- OPENPLC DATA VALUES ---")
        print("setpoint (%MW0)      :", read_value(r_setpoint, "registers"))
        print("level (%IW0)         :", read_value(r_level, "registers"))
        print("sensor_level (%IX0.0):", read_value(r_sensor, "bits"))
        print("pump_output (%QX0.0) :", read_value(r_pump, "bits"))

    finally:
        client.close()


if __name__ == "__main__":
    main()