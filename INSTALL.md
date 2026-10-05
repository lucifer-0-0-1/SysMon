# Installation Guide for Laptop Monitor

## System Dependencies

Laptop Monitor needs Python 3.9+ and Qt 6 (PySide6).

#### Arch Linux / Manjaro / EndeavourOS / Garuda
```bash
sudo pacman -S python-psutil python-dotenv pyside6
```
Or install the package itself (see README), which pulls these in.

#### Other distributions
`pip install -r requirements.txt` inside a virtualenv (below) brings in PySide6.

## Python Dependencies

After installing system dependencies, install Python packages:

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

## Installation Steps

1. Install system dependencies
2. Clone/download this repository
3. Create and activate virtual environment
4. Install Python dependencies
5. Install the fan control helper (see below)
6. Run the application

## Fan Control Setup

The packaged app (`makepkg -si`, see README) already includes this. When running from source, install the small root helper and its polkit rule once:
```bash
sudo install -Dm755 fanctl /usr/lib/laptop-monitor/fanctl
sudo install -Dm644 packaging/org.laptopmonitor.fanctl.policy /usr/share/polkit-1/actions/
```
The helper only accepts `/sys/class/hwmon/hwmonN/pwmM[_enable]` paths and in-range values.

> Don't use a sudoers rule like `NOPASSWD: /usr/bin/tee /sys/class/hwmon/hwmon5/pwm*`. Sudoers wildcards also match spaces and `/`,
> so it allows `sudo tee /sys/class/hwmon/hwmon5/pwm1 /etc/passwd`. If you added one earlier, remove it with `sudo visudo`.

## Verification

After installation, test the setup:
```bash
source venv/bin/activate
python test_basic.py
```

All tests should pass.

## Running the Application

```bash
source venv/bin/activate
python main.py
```

## Troubleshooting

### "qt.qpa.plugin: Could not load the Qt platform plugin"
Install your distribution's Qt 6 Wayland/X11 platform packages (Arch: `qt6-wayland`).

### Fan control not working
1. Verify the helper is installed: `ls -l /usr/lib/laptop-monitor/fanctl`
2. Test it: `pkexec /usr/lib/laptop-monitor/fanctl /sys/class/hwmon/hwmonN/pwm1_enable 2`
3. Check that a PWM device exists: `ls /sys/class/hwmon/hwmon*/pwm*`
4. Ensure the hardware monitoring interface is available on your laptop

### NVIDIA GPU shows "suspended"
That's expected. The dGPU is asleep to save power, and the app won't wake it. Stats appear while it's in use.