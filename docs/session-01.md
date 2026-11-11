# Session 1: Installing the OpenPLC v4 Runtime on Raspberry Pi

## Objective

Install the OpenPLC v4 runtime natively on the Raspberry Pi (no Docker), without disturbing the existing Rheomix project running on the same machine, and validate management interface access from the PC.

## Hardware and environment

| Item | Value |
|---|---|
| Target | Raspberry Pi (ARM64, `aarch64`) |
| OS | Debian 13.7 "Trixie" (Raspberry Pi OS) |
| RAM | 3.7 GiB total (2.4 GiB available at test time) |
| Disk | 58 GB total (48 GB free) |
| Runtime | OpenPLC Runtime v4 (repo `Autonomy-Logic/openplc-runtime`, branch `development`) |
| Installation | Native (`install.sh --native`), **without Docker** |
| Client PC | Windows, OpenPLC Editor v4 (desktop application) |

Why no Docker: the Pi already hosts Rheomix, and I wanted to keep its RAM and disk for that project. A native install turned out to be enough for everything that followed.

## Steps performed

### 1. Pre-installation checks (read-only)

```bash
cat /etc/os-release | grep -E 'PRETTY_NAME|VERSION_ID'
uname -m                 # aarch64
free -h                  # 3.7 GiB RAM
df -h /                  # 48 GB free
systemctl list-units --type=service --all | grep -i openplc   # empty → not installed yet
sudo ss -lntp | grep -E ':(8080|502)\b'
```

### 2. Fetching the runtime

```bash
cd ~
git clone https://github.com/Autonomy-Logic/openplc-runtime.git
cd openplc-runtime
git checkout development
ls -l install.sh start_openplc.sh   # verify both files exist
```

Note: the legacy OpenPLC v3 (`thiagoralves/OpenPLC_v3`) is archived/abandoned. v4 is driven by the OpenPLC Editor v4 desktop application; the management port is **8443** (HTTPS), not the historical v3 port 8080. I initially expected 8080 and lost a few minutes on that.

### 3. Native installation

```bash
sudo ./install.sh --native
```

The `--native` flag is essential: without it, the script defaults to the Docker path.

### 4. Validation

```bash
sudo systemctl status openplc-runtime --no-pager
sudo ss -lntp | grep -E ':(8443|502)\b'
```

Result obtained:

```
LISTEN 0 128 0.0.0.0:8443 0.0.0.0:* users:(("python3",pid=65421,fd=11))
```

**Port 502 (Modbus/TCP)** only appears once a program is loaded with the `modbus_slave` plugin enabled (see Session 2).

From the PC:

```powershell
Test-NetConnection <PI_IP> -Port 8443   # TcpTestSucceeded : True
```

Then open `https://<PI_IP>:8443` in a browser. The certificate is self-signed, so the browser warning is expected in a lab setting (verify the IP before accepting).

## Pitfalls encountered and resolutions

- **`PLC State: EMPTY` / `No libplc_*.so file found in ./build`** on first start: normal behavior as long as no program has been compiled and deployed from the editor. The `build/new_libplc.so` file is generated at deployment (see Session 2).
- The v4 runtime has **no web programming interface**: everything is driven from OpenPLC Editor v4 on the PC.
- Docker ruled out to preserve the Pi's resources and its cohabitation with Rheomix.

## Session deliverables

- [x] v4 runtime installed natively, service active
- [x] Port 8443 listening and reachable from the PC
- [x] OpenPLC Editor v4 installed on the PC and connected to the runtime
- [x] Session log/commit in `ot-lab`

## Next step

Session 2: first ST program, enabling the Modbus server (port 502), and reading registers from Python (`pymodbus`).