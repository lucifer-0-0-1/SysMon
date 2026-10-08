# Laptop Monitor

A system monitor and fan controller for Linux laptops, built with Qt (PySide6) and psutil. It follows your desktop theme, including dark mode, and uses about 100 MB of RAM.

## Features

- **Dashboard**: live graphs of CPU usage, CPU/GPU temperature, RAM/swap and network throughput, plus tiles for CPU, GPU, memory, battery and fans
- **Processes**: sortable, filterable process list; end (SIGTERM) or kill (SIGKILL) a process
- **Details**: per-core usage and clock, every temperature sensor with high/critical limits, all fans, battery power draw / health / cycles, memory breakdown, disk usage and I/O rates, per-interface network rates and IPs
- **GPU**: NVIDIA (via `nvidia-smi`) and AMD (sysfs). A runtime-suspended NVIDIA dGPU is never woken, so monitoring doesn't drain your battery
- **Fan control**: manual PWM sliders or firmware auto mode. The fan device is auto-detected (no hard-coded `hwmon5`), and fans return to auto when the app closes
- **Alerts**: desktop notifications for high CPU/GPU temperature and low battery
- **Plugins**: drop a `.py` file with `get_data()` into `~/.config/laptop-monitor/plugins/`
- **Settings tab**: saved to `~/.config/laptop-monitor/config.env`

## Install

Download from the [latest release](https://github.com/lucifer-0-0-1/SysMon/releases/latest):

| Distro | Download | Install |
|---|---|---|
| Ubuntu 25.10+ / 26.04 LTS, Debian 13+ | `laptop-monitor_<version>_all.deb` | `sudo apt install ./laptop-monitor_*_all.deb` |
| Arch, Manjaro, EndeavourOS, Garuda | `PKGBUILD` (below) | `makepkg -si` |
| Anything else: Ubuntu 22.04/24.04, Fedora, openSUSE, Mint, Pop!_OS… (x86_64, glibc 2.34+: Ubuntu 22.04+, Debian 12+, Fedora 35+) | `LaptopMonitor-<version>-x86_64.AppImage` | `chmod +x LaptopMonitor-*.AppImage` and run it |

Arch-based distros:
```bash
git clone https://github.com/lucifer-0-0-1/SysMon.git
cd SysMon/packaging
makepkg -si
```

Then launch **Laptop Monitor** from your app menu, or run `laptop-monitor`.

[INSTALL.md](INSTALL.md) has step-by-step instructions for each distro, plus uninstalling and troubleshooting.

### Fan control

The .deb and Arch packages include a small root helper (`fanctl`) and a polkit rule, so fan control works right away. The logged-in desktop user can change fan speed without a password. To require one, change `allow_active` to `auth_admin_keep` in `/usr/share/polkit-1/actions/org.laptopmonitor.fanctl.policy`.

The AppImage can't install system files on its own. On the Fan Control page, click **Enable fan control** once, and enter your admin password to install the helper.

If the AppImage won't start because FUSE is unavailable (for example in a container), run it with `--appimage-extract-and-run`.

## Run from source

See [INSTALL.md](INSTALL.md).

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py
python test_basic.py   # self-checks
```

## Plugins

```python
# ~/.config/laptop-monitor/plugins/my_metric.py
def get_data():
    return {"metric_name": 42}

def get_plugin_info():          # optional
    return {"name": "My Metric", "version": "1.0"}
```

## Releasing

1. Bump `VERSION` in `main.py` and `pkgver` in `packaging/PKGBUILD`, then commit.
2. Tag and push: `git tag v1.2.0 && git push origin main v1.2.0`.
   GitHub Actions (`.github/workflows/release.yml`) builds the .deb and AppImage and publishes them as a GitHub Release.
3. In `packaging/`, run `updpkgsums && makepkg --printsrcinfo > .SRCINFO` and commit. Optionally, push `PKGBUILD` + `.SRCINFO` to the AUR.

To build locally: `packaging/build-deb.sh` (needs `dpkg-deb`) and `packaging/build-appimage.sh`. Output goes to `dist/`.

## License

Apache License 2.0. See [LICENSE](LICENSE).
