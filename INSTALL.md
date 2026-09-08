# Installation Guide for Laptop Monitor

## System Dependencies

Laptop Monitor requires the following system dependencies:

1. **Tkinter** - For GUI interface
2. **Python 3.6+** - Core Python interpreter

### Installing Tkinter

#### Arch Linux / Manjaro / Garuda
```bash
sudo pacman -S tk
```

#### Ubuntu / Debian / Linux Mint
```bash
sudo apt-get update
sudo apt-get install python3-tk
```

#### Fedora / CentOS / RHEL
```bash
sudo dnf install python3-tkinter
```

#### openSUSE
```bash
sudo zypper install python3-tk
```

#### Other Distributions
Look for packages named `tk`, `python3-tk`, or `python3-tkinter` in your distribution's repository.

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

1. Install system dependencies (Tkinter)
2. Clone/download this repository
3. Create and activate virtual environment
4. Install Python dependencies
5. Configure fan control sudo access (see below)
6. Run the application

## Fan Control Setup

To enable fan control, you need to set up passwordless sudo for specific commands:

1. Run `sudo visudo`
2. Add the following line (replace `yourusername` with your actual username):
   ```
   yourusername ALL=(ALL) NOPASSWD: /usr/bin/tee /sys/class/hwmon/hwmon5/pwm*
   yourusername ALL=(ALL) NOPASSWD: /usr/bin/tee /sys/class/hwmon/hwmon5/pwm*_enable
   ```
3. Save and exit

### Alternative (Less Secure)
If you prefer broader access (not recommended for security):
```
yourusername ALL=(ALL) NOPASSWD: /usr/bin/tee
```

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

### "ImportError: libtk8.6.so: cannot open shared object file"
This indicates Tkinter is not properly installed. Reinstall the Tkinter package for your distribution.

### Fan control not working
1. Verify your user is in the sudoers file with the correct NOPASSWD entries
2. Test sudo access: `sudo -n echo "test"`
3. Check if the fan control paths exist: `ls /sys/class/hwmon/hwmon5/pwm*`
4. Ensure the hardware monitoring interface is available on your laptop

### Virtual environment activation issues
- On Windows, use `venv\Scripts\activate`
- Ensure you have virtualenv installed: `pip install virtualenv`