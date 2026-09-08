#!/usr/bin/env python3
"""
Example plugin: Battery monitor for laptops
"""

import psutil
import os

def get_data():
    """Get battery information"""
    try:
        battery = psutil.sensors_battery()
        if battery:
            return {
                'battery_percent': battery.percent,
                'battery_power_plugged': battery.power_plugged,
                'battery_secsleft': battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else -1
            }
    except (AttributeError, NotImplementedError):
        pass

    # Fallback for systems without psutil battery support
    try:
        # Try to read from sysfs
        bat_path = "/sys/class/power_supply/BAT0/"
        if os.path.exists(bat_path):
            with open(os.path.join(bat_path, "capacity"), 'r') as f:
                percent = int(f.read().strip())

            with open(os.path.join(bat_path, "status"), 'r') as f:
                status = f.read().strip()
                power_plugged = status == "Charging" or status == "Full"

            return {
                'battery_percent': percent,
                'battery_power_plugged': power_plugged,
                'battery_secsleft': -1  # Unknown
            }
    except (FileNotFoundError, ValueError, PermissionError):
        pass

    return {}

def get_plugin_info():
    """Get plugin metadata"""
    return {
        'name': 'Battery Monitor',
        'description': 'Monitors laptop battery status',
        'version': '1.0.0',
        'author': 'Laptop Monitor Community'
    }