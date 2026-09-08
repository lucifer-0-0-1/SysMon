# Laptop Monitor

A lightweight system monitoring and fan control application for Linux laptops.

## Features

- **System Monitoring**: CPU/GPU temperature, usage, memory, disk, and network stats
- **Fan Control**: Manual slider control and automatic temperature-based modes
- **Lightweight**: Built with Tkinter for minimal RAM usage
- **Extensible**: Plugin system for custom metrics
- **Cross-platform**: Works on most Linux distributions
- **Open Source**: MIT License

## Installation

### Prerequisites

- Python 3.6+
- pip (Python package installer)

### Setup

1. Clone or download this repository
2. Create a virtual environment (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
5. Edit `.env` to configure settings as needed

### Fan Control Setup

To enable fan control, you need to set up passwordless sudo for the tee command:

1. Run `sudo visudo`
2. Add the following line (replace `yourusername` with your actual username):
   ```
   yourusername ALL=(ALL) NOPASSWD: /usr/bin/tee /sys/class/hwmon/hwmon5/pwm*
   yourusername ALL=(ALL) NOPASSWD: /usr/bin/tee /sys/class/hwmon/hwmon5/pwm*_enable
   ```
3. Save and exit

## Usage

Run the application:
```bash
python main.py
```

### GUI Tabs

1. **Dashboard**: Real-time graphs of temperatures, usage, and fan speeds
2. **Fan Control**: Manual sliders for CPU/GPU fan speed, auto/manual mode toggle
3. **Advanced**: Detailed memory, disk, and network monitoring
4. **Plugins**: Manage and configure additional metric collectors
5. **Settings**: Application configuration options

## Configuration

All settings can be configured via the `.env` file or through the Settings tab in the GUI.

Key environment variables:
- `UPDATE_INTERVAL`: Monitoring update interval in milliseconds (default: 2000)
- `CPU_TEMP_THRESHOLD`: Temperature threshold for auto fan control (default: 75.0)
- `GPU_TEMP_THRESHOLD`: GPU temperature threshold for auto fan control (default: 80.0)
- `FAN_MIN_SPEED`: Minimum fan speed (0-255, default: 30)
- `FAN_MAX_SPEED`: Maximum fan speed (0-255, default: 255)

## Development

### Adding Plugins

Create a new Python file in the `plugins/` directory to add custom metrics.
Each plugin should follow the basic structure:
```python
def get_data():
    """Return data to be displayed"""
    return {"metric_name": value}
```

### Testing

Run unit tests:
```bash
python -m pytest tests/
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Inspired by the need for lightweight system monitoring on Linux laptops
- Uses psutil for system monitoring
- Built with Tkinter for minimal dependencies