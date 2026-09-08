#!/usr/bin/env python3
"""
System monitoring module for Laptop Monitor
"""

import psutil
import subprocess
import os
import re

class Monitor:
    def __init__(self):
        self.psutil_available = self._check_psutil()

    def _check_psutil(self):
        """Check if psutil is available"""
        try:
            import psutil
            return True
        except ImportError:
            return False

    def get_cpu_temperature(self):
        """Get CPU temperature from sysfs"""
        try:
            # Try common paths for temperature sensors
            temp_paths = [
                "/sys/class/hwmon/hwmon5/temp1_input",  # Original from user code
                "/sys/class/thermal/thermal_zone0/temp",
                "/sys/class/hwmon/hwmon0/temp1_input",
                "/sys/class/hwmon/hwmon1/temp1_input"
            ]

            for path in temp_paths:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        temp_raw = f.read().strip()
                        # Convert from millidegrees to Celsius if needed
                        temp = float(temp_raw)
                        if temp > 1000:  # Likely in millidegrees
                            temp = temp / 1000.0
                        return round(temp, 1)
        except (FileNotFoundError, ValueError, PermissionError):
            pass

        # Fallback to psutil if available
        if self.psutil_available:
            try:
                temps = psutil.sensors_temperatures()
                if 'coretemp' in temps:
                    return round(temps['coretemp'][0].current, 1)
                elif 'cpu_thermal' in temps:
                    return round(temps['cpu_thermal'][0].current, 1)
            except (AttributeError, KeyError):
                pass

        return 0.0

    def get_gpu_temperature(self):
        """Get GPU temperature from sysfs"""
        try:
            # Try common paths for GPU temperature
            temp_paths = [
                "/sys/class/hwmon/hwmon5/temp3_input",  # Original from user code
                "/sys/class/drm/card0/device/hwmon/hwmon0/temp1_input",
                "/sys/class/hwmon/hwmon2/temp1_input"
            ]

            for path in temp_paths:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        temp_raw = f.read().strip()
                        temp = float(temp_raw)
                        if temp > 1000:  # Likely in millidegrees
                            temp = temp / 1000.0
                        return round(temp, 1)
        except (FileNotFoundError, ValueError, PermissionError):
            pass

        return 0.0

    def get_cpu_usage(self):
        """Get CPU usage percentage"""
        if self.psutil_available:
            try:
                return psutil.cpu_percent(interval=0.1)
            except:
                pass
        return 0.0

    def get_gpu_usage(self):
        """Get GPU usage percentage (if available)"""
        # This is platform-specific and may require additional tools
        # For now, return placeholder
        return 0.0

    def get_memory_usage(self):
        """Get memory usage percentage"""
        if self.psutil_available:
            try:
                memory = psutil.virtual_memory()
                return memory.percent
            except:
                pass
        return 0.0

    def get_disk_usage(self):
        """Get disk usage percentage for root partition"""
        if self.psutil_available:
            try:
                disk = psutil.disk_usage('/')
                return (disk.used / disk.total) * 100
            except:
                pass
        return 0.0

    def get_network_stats(self):
        """Get network I/O statistics"""
        if self.psutil_available:
            try:
                net_io = psutil.net_io_counters()
                return {
                    'bytes_sent': net_io.bytes_sent,
                    'bytes_recv': net_io.bytes_recv,
                    'packets_sent': net_io.packets_sent,
                    'packets_recv': net_io.packets_recv
                }
            except:
                pass
        return {'bytes_sent': 0, 'bytes_recv': 0, 'packets_sent': 0, 'packets_recv': 0}

    def get_fan_speeds(self):
        """Get fan speeds from sysfs (if available)"""
        fan_data = {}
        try:
            # Look for fan speed sensors
            hwmon_path = "/sys/class/hwmon/"
            if os.path.exists(hwmon_path):
                for hwmon in os.listdir(hwmon_path):
                    hwmon_full = os.path.join(hwmon_path, hwmon)
                    if os.path.isdir(hwmon_full):
                        # Look for fan input files
                        for file in os.listdir(hwmon_full):
                            if 'fan' in file and 'input' in file:
                                fan_path = os.path.join(hwmon_full, file)
                                try:
                                    with open(fan_path, 'r') as f:
                                        speed = f.read().strip()
                                        fan_data[file] = int(speed)
                                except (ValueError, PermissionError):
                                    pass
        except (FileNotFoundError, PermissionError):
            pass
        return fan_data

if __name__ == "__main__":
    # Test the monitor
    monitor = Monitor()
    print(f"CPU Temp: {monitor.get_cpu_temperature()}°C")
    print(f"GPU Temp: {monitor.get_gpu_temperature()}°C")
    print(f"CPU Usage: {monitor.get_cpu_usage()}%")
    print(f"Memory Usage: {monitor.get_memory_usage()}%")
    print(f"Disk Usage: {monitor.get_disk_usage()}%")