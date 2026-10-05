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

## Install (Arch Linux, Manjaro, EndeavourOS, Garuda, Arch Linux ARM)

```bash
git clone https://github.com/lucifer-0-0-1/SysMon.git
cd SysMon/packaging
updpkgsums        # once the v1.0.0 tag exists on GitHub
makepkg -si
```

Then launch **Laptop Monitor** from your app menu, or run `laptop-monitor`. The package is `arch=any`, so it builds on x86_64 and aarch64.

Fan control in the installed app goes through polkit (`pkexec`), with no sudoers editing. The logged-in desktop user can change fan speed without a password. To require one, change `allow_active` to `auth_admin_keep` in `/usr/share/polkit-1/actions/org.laptopmonitor.fanctl.policy`.

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

1. Bump `VERSION` in `main.py` and `pkgver` in `packaging/PKGBUILD`.
2. Tag and push: `git tag v1.0.0 && git push origin v1.0.0`.
3. In `packaging/`, run `updpkgsums && makepkg --printsrcinfo > .SRCINFO`. Then build with `makepkg`, or push `PKGBUILD` + `.SRCINFO` to the AUR.

## License

Apache License 2.0. See [LICENSE](LICENSE).
