import json
import time
from pathlib import Path
from pymodbus.client import ModbusTcpClient

CONFIG_PATH = Path(__file__).with_name("config.json")


def main():
    if not CONFIG_PATH.is_file():
        raise FileNotFoundError(f"Configuration file not found: {CONFIG_PATH}")

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    host = config.get("host")
    port = config.get("port", 502)

    if not isinstance(host, str) or not host.strip():
        raise ValueError("Set a valid Modbus server address in config.json.")
    if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
        raise ValueError("The Modbus server port must be between 1 and 65535.")

    print(f"Connecting to Modbus server at {host}:{port}...")
    client = ModbusTcpClient(host.strip(), port=port, timeout=3)

    if not client.connect():
        client.close()
        raise ConnectionError(f"Could not connect to Modbus server at {host}:{port}.")

    try:
        while True:
            r_regs = client.read_holding_registers(1024, count=2, device_id=1)
            r_coils = client.read_coils(0, count=1, device_id=1)

            if (
                r_regs.isError()
                or r_coils.isError()
                or len(r_regs.registers) < 2
                or not r_coils.bits
            ):
                print(
                    "\rModbus read failed; retrying...",
                    end="",
                    flush=True,
                )
                time.sleep(0.2)
                continue

            setpoint = r_regs.registers[0]
            level = r_regs.registers[1]
            pump = r_coils.bits[0]

            safe_level = max(0, min(100, level))
            bar_fill = safe_level // 2
            bar = "#" * bar_fill + "." * (70 - bar_fill)

            print(
                f"\rTank: [{bar}] {level:3d}%  |  Setpoint: {setpoint}  |  Pump: {'ON ' if pump else 'OFF'}",
                end="",
                flush=True,
            )
            time.sleep(0.2)

    except KeyboardInterrupt:
        print("\nHMI stopped.")
    finally:
        client.close()


if __name__ == "__main__":
    main()