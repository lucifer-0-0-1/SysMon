# Installation Guide for Laptop Monitor

Pick the format for your distro. Downloads are on the [latest release](https://github.com/lucifer-0-0-1/SysMon/releases/latest) page.

| Your distro | Use |
|---|---|
| Ubuntu 25.10+ / 26.04 LTS, Debian 13+ | [.deb package](#ubuntu--debian-deb) |
| Arch, Manjaro, EndeavourOS, Garuda | [PKGBUILD](#arch-based-distros) |
| Ubuntu 22.04 / 24.04, Linux Mint, Pop!_OS, Fedora, openSUSE, any other x86_64 distro from about 2021 on (glibc 2.34+) | [AppImage](#any-distro-appimage) |

The .deb needs Ubuntu 25.10 or newer, because older Ubuntu releases don't package PySide6 (Qt for Python). On Ubuntu 22.04/24.04, use the AppImage.

## Ubuntu / Debian (.deb)

```bash
sudo apt install ./laptop-monitor_*_all.deb
```

Use `apt`, not `dpkg -i`, so dependencies are installed too. Launch **Laptop Monitor** from the app menu, or run `laptop-monitor`. Fan control works right away.

## Arch-based distros

```bash
git clone https://github.com/lucifer-0-0-1/SysMon.git
cd SysMon/packaging
makepkg -si
```

Launch **Laptop Monitor** from the app menu, or run `laptop-monitor`. Fan control works right away.

## Any distro (AppImage)

```bash
chmod +x LaptopMonitor-*-x86_64.AppImage
./LaptopMonitor-*-x86_64.AppImage
```

The AppImage includes Python, Qt and every library it needs, so you install nothing else. It's a single file; keep it wherever you like (for example `~/Applications`).

To enable fan control, open the **Fan Control** page and click **Enable fan control**. You'll get one admin password prompt, which installs the fan helper described below. You only need to do this once per computer.

## Fan control

Changing fan speed requires root. Instead of running the whole app as root, a tiny helper (`/usr/lib/laptop-monitor/fanctl`) does only the writes. It accepts only `/sys/class/hwmon/hwmonN/pwmM[_enable]` paths and in-range values, and it runs through polkit (`pkexec`).

- **.deb and Arch packages:** the helper is included.
- **AppImage:** click **Enable fan control** once, as above.
- **Running from source:** click **Enable fan control**, or install it manually:
  ```bash
  sudo install -Dm755 fanctl /usr/lib/laptop-monitor/fanctl
  sudo install -Dm644 packaging/org.laptopmonitor.fanctl.policy /usr/share/polkit-1/actions/
  ```

The logged-in desktop user can change fan speed without a password. To require one, change `allow_active` to `auth_admin_keep` in `/usr/share/polkit-1/actions/org.laptopmonitor.fanctl.policy`.

> Don't use a sudoers rule like `NOPASSWD: /usr/bin/tee /sys/class/hwmon/hwmon5/pwm*`. Sudoers wildcards also match spaces and `/`,
> so it allows `sudo tee /sys/class/hwmon/hwmon5/pwm1 /etc/passwd`. If you added one earlier, remove it with `sudo visudo`.

## Run from source

1. Install the dependencies:
   - **Arch:** `sudo pacman -S python-psutil python-dotenv pyside6`
   - **Ubuntu 25.10+ / Debian 13+:** `sudo apt install python3-psutil python3-dotenv python3-pyside6.qtwidgets`
   - **Anything else**, using a virtualenv (Ubuntu needs `sudo apt install python3-venv` first):
     ```bash
     python3 -m venv venv
     source venv/bin/activate        # fish: source venv/bin/activate.fish
     pip install -r requirements.txt
     ```
2. Run it:
   ```bash
   python3 main.py
   ```
3. Run the self-checks; all of them should pass:
   ```bash
   python3 test_basic.py
   ```

## Uninstall

| Format | Command |
|---|---|
| .deb | `sudo apt remove laptop-monitor` |
| Arch | `sudo pacman -R laptop-monitor` |
| AppImage | Delete the file. If you enabled fan control, also run `sudo rm /usr/lib/laptop-monitor/fanctl /usr/share/polkit-1/actions/org.laptopmonitor.fanctl.policy` |

Your settings and plugins live in `~/.config/laptop-monitor/`. Delete that folder to remove them too.

## Building the packages yourself

```bash
packaging/build-deb.sh        # needs dpkg-deb (Debian/Ubuntu)
packaging/build-appimage.sh   # needs curl, file and the xcb-util libraries listed in the script
```

Output goes to `dist/`. Pushing a `v*` tag makes GitHub Actions build both and publish a release (see README → Releasing).

## Troubleshooting

### The .deb fails with "unmet dependencies: python3-pyside6..."
Your Ubuntu/Debian release is too old to package PySide6. Use the AppImage instead.

### The AppImage doesn't start
- Make sure it's executable: `chmod +x LaptopMonitor-*.AppImage`.
- If FUSE isn't available (for example inside a container), run it with `--appimage-extract-and-run`.
- If you see a `GLIBC_2.34 not found` error, your distro is older than 2021 and can't run it.

### "qt.qpa.plugin: Could not load the Qt platform plugin"
Install your distro's Qt 6 Wayland/X11 platform packages (Arch: `qt6-wayland`; Ubuntu: `libxcb-cursor0`). This only applies to source runs; the AppImage bundles them.

### Fan control not working
1. Check that the helper is installed: `ls -l /usr/lib/laptop-monitor/fanctl`. If it isn't, click **Enable fan control**.
2. Test it: `pkexec /usr/lib/laptop-monitor/fanctl /sys/class/hwmon/hwmonN/pwm1_enable 2`.
3. Check that your laptop exposes a PWM fan: `ls /sys/class/hwmon/hwmon*/pwm*`. If nothing is listed, your laptop's driver doesn't support software fan control. Fan RPMs are still shown.

### NVIDIA GPU shows "suspended"
That's expected. The dGPU is asleep to save power, and the app won't wake it. Stats appear while it's in use.
