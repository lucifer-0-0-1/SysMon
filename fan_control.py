#!/usr/bin/env python3
"""
Fan control module for Laptop Monitor
Handles PWM fan speed control via sysfs
"""

import glob
import os
import subprocess

# Installed by the package; run through pkexec (polkit) to write pwm files as root
HELPER = "/usr/lib/laptop-monitor/fanctl"
POLICY = "org.laptopmonitor.fanctl.policy"


def find_pwm_hwmon(base="/sys/class/hwmon"):
    """First hwmon dir exposing pwm1 (hwmonN numbering changes between boots)"""
    for path in sorted(glob.glob(f"{base}/hwmon*")):
        if os.path.exists(f"{path}/pwm1"):
            return path
    return None


def install_helper():
    """Install fanctl + its polkit policy system-wide with one admin prompt (AppImage and source runs)"""
    here = os.path.dirname(os.path.abspath(__file__))
    # Source-tree layout first, then the installed layout (an AppImage carries usr/ like a package)
    fanctl = next((p for p in (f"{here}/fanctl", f"{here}/../../lib/laptop-monitor/fanctl")
                   if os.path.exists(p)), None)
    policy = next((p for p in (f"{here}/packaging/{POLICY}", f"{here}/../polkit-1/actions/{POLICY}")
                   if os.path.exists(p)), None)
    if not (fanctl and policy):
        return False
    script = f'install -Dm755 "$1" {HELPER} && install -Dm644 "$2" /usr/share/polkit-1/actions/{POLICY}'
    try:
        return subprocess.run(["pkexec", "/bin/sh", "-c", script, "sh", fanctl, policy],
                              timeout=300).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


class FanController:
    def __init__(self, hwmon=None):
        self.hwmon = hwmon or find_pwm_hwmon()
        self.available = self.hwmon is not None
        self.fan_count = len(glob.glob(f"{self.hwmon}/pwm[0-9]")) if self.available else 0

    def needs_helper(self):
        """True when fan writes have no route: no installed helper and pwm files not writable"""
        return self.available and not os.path.exists(HELPER) and not os.access(self._path("pwm1"), os.W_OK)

    def _path(self, name):
        return os.path.join(self.hwmon or "", name)

    def _write(self, name, value):
        """Write value to a pwm file: directly if writable, else pkexec helper, else sudo -n tee"""
        path = self._path(name)
        if not os.path.exists(path):
            return False
        try:
            if os.access(path, os.W_OK):
                with open(path, "w") as f:
                    f.write(f"{value}\n")
                return True
            if os.path.exists(HELPER):
                cmd, data = ["pkexec", HELPER, path, str(value)], None
            else:  # legacy sudoers tee rule; INSTALL.md recommends installing HELPER instead
                cmd, data = ["sudo", "-n", "tee", path], f"{value}\n"
            result = subprocess.run(cmd, input=data, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                print(f"Error writing {path}: {result.stderr.strip()}")
            return result.returncode == 0
        except (OSError, subprocess.TimeoutExpired) as e:
            print(f"Error writing {path}: {e}")
            return False

    def _read_int(self, name):
        try:
            with open(self._path(name)) as f:
                return int(f.read().strip())
        except (OSError, ValueError):
            return 0

    def initialize(self):
        return self.set_manual_mode()

    def set_fan_speed(self, fan, speed):
        """Set fan N (1-based) PWM 0-255"""
        return self._write(f"pwm{fan}", max(0, min(255, int(speed))))

    def get_fan_speed(self, fan):
        return self._read_int(f"pwm{fan}")

    def get_fan_rpm(self, fan):
        return self._read_int(f"fan{fan}_input")

    def get_mode(self):
        """1 = manual, 2 = automatic (firmware) on most drivers"""
        return self._read_int("pwm1_enable")

    def set_cpu_fan_speed(self, speed):
        return self.set_fan_speed(1, speed)

    def set_gpu_fan_speed(self, speed):
        return self.set_fan_speed(2, speed)

    def get_cpu_fan_speed(self):
        return self.get_fan_speed(1)

    def get_gpu_fan_speed(self):
        return self.get_fan_speed(2)

    def get_cpu_fan_rpm(self):
        return self.get_fan_rpm(1)

    def get_gpu_fan_rpm(self):
        return self.get_fan_rpm(2)

    def _set_enable(self, value):
        return all([self._write(f"pwm{n}_enable", value) for n in range(1, self.fan_count + 1)])

    def set_manual_mode(self):
        return self._set_enable(1)

    def set_auto_mode_fixed(self):
        """Hand all fans back to firmware control"""
        return self._set_enable(2)


if __name__ == "__main__":
    controller = FanController()
    print(f"Fan hwmon: {controller.hwmon} ({controller.fan_count} fans)")
    for n in range(1, controller.fan_count + 1):
        print(f"  fan{n}: pwm={controller.get_fan_speed(n)} rpm={controller.get_fan_rpm(n)}")
