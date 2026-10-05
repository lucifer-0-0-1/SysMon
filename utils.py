#!/usr/bin/env python3
"""
Utility functions for Laptop Monitor
"""

import subprocess
import os
import sys

class Utils:
    @staticmethod
    def check_sudo_access():
        """Check if we have sudo access without password"""
        try:
            result = subprocess.run(
                ["sudo", "-n", "-v"],
                capture_output=True,
                timeout=2
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False

    @staticmethod
    def run_sudo_command(command):
        """Run a command with sudo"""
        try:
            result = subprocess.run(
                ["sudo", "-n"] + command.split(),
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timeout"
        except Exception as e:
            return False, "", str(e)

    @staticmethod
    def get_system_info():
        """Get basic system information"""
        info = {}
        try:
            # Get OS info
            with open('/etc/os-release', 'r') as f:
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        info[key] = value.strip('"')
        except FileNotFoundError:
            info['PRETTY_NAME'] = 'Unknown Linux'

        try:
            info['hostname'] = subprocess.check_output(['hostname']).decode().strip()
        except:
            info['hostname'] = 'unknown'

        try:
            info['kernel'] = subprocess.check_output(['uname', '-r']).decode().strip()
        except:
            info['kernel'] = 'unknown'

        return info

    @staticmethod
    def bytes_to_human_readable(bytes_value):
        """Convert bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"

    @staticmethod
    def celsius_to_fahrenheit(celsius):
        """Convert Celsius to Fahrenheit"""
        return (celsius * 9/5) + 32

    @staticmethod
    def fahrenheit_to_celsius(fahrenheit):
        """Convert Fahrenheit to Celsius"""
        return (fahrenheit - 32) * 5/9

if __name__ == "__main__":
    # Test utils
    print("System Info:")
    info = Utils.get_system_info()
    for key, value in info.items():
        print(f"  {key}: {value}")

    print(f"\n1024 bytes = {Utils.bytes_to_human_readable(1024)}")
    print(f"1048576 bytes = {Utils.bytes_to_human_readable(1048576)}")
    print(f"25°C = {Utils.celsius_to_fahrenheit(25):.1f}°F")
    print(f"77°F = {Utils.fahrenheit_to_celsius(77):.1f}°C")

    print(f"\nSudo access available: {Utils.check_sudo_access()}")