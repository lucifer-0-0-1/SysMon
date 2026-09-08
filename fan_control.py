#!/usr/bin/env python3
"""
Fan control module for Laptop Monitor
Handles PWM fan speed control via sysfs
"""

import subprocess
import os
import time

class FanController:
    def __init__(self):
        self.cpu_fan_path = "/sys/class/hwmon/hwmon5/pwm1"
        self.gpu_fan_path = "/sys/class/hwmon/hwmon5/pwm2"
        self.enable_cpu_path = "/sys/class/hwmon/hwmon5/pwm1_enable"
        self.enable_gpu_path = "/sys/class/hwmon/hwmon5/pwm2_enable"
        self.initialized = False

    def _run_sudo_command(self, command, input_data=None):
        """Run a command with sudo using subprocess"""
        try:
            # We are going to run: sudo -n <command>
            # We split the command into a list to avoid using the shell
            # This assumes the command is a simple command without shell operators (like pipes, redirects)
            # because we are handling the input separately via the input_data parameter.
            cmd_parts = command.split()
            # Now we run: sudo -n <cmd_parts[0]> <cmd_parts[1]> ... with the input data
            result = subprocess.run(
                ["sudo", "-n"] + cmd_parts,
                input=input_data,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timeout"
        except Exception as e:
            return False, "", str(e)

    def _check_sudo_access(self):
        """Check if we have sudo access for fan control"""
        success, _, _ = self._run_sudo_command("tee /dev/null", input_data="testing sudo\n")
        return success

    def initialize(self):
        """Initialize fan control by enabling PWM"""
        if self.initialized:
            return True

        # Check if the paths exist
        if not (os.path.exists(self.cpu_fan_path) and os.path.exists(self.gpu_fan_path)):
            # Try to find alternative paths
            self._find_fan_paths()

        # Enable PWM control
        try:
            # Enable CPU fan
            if os.path.exists(self.enable_cpu_path):
                success, _, err = self._run_sudo_command(f"tee {self.enable_cpu_path}", input_data="1\n")
                if not success:
                    print(f"Warning: Could not enable CPU fan: {err}")

            # Enable GPU fan
            if os.path.exists(self.enable_gpu_path):
                success, _, err = self._run_sudo_command(f"tee {self.enable_gpu_path}", input_data="1\n")
                if not success:
                    print(f"Warning: Could not enable GPU fan: {err}")

            self.initialized = True
            return True
        except Exception as e:
            print(f"Error initializing fan control: {e}")
            return False

    def _find_fan_paths(self):
        """Try to find fan control paths if defaults don't exist"""
        # Search for pwm files in hwmon directories
        hwmon_base = "/sys/class/hwmon/"
        if os.path.exists(hwmon_base):
            for hwmon in os.listdir(hwmon_base):
                hwmon_path = os.path.join(hwmon_base, hwmon)
                if os.path.isdir(hwmon_path):
                    # Look for pwm files
                    for file in os.listdir(hwmon_path):
                        if file.startswith("pwm") and file.endswith("_enable"):
                            pwm_num = file[3:-7]  # Extract number from pwmX_enable
                            enable_path = os.path.join(hwmon_path, file)
                            pwm_path = os.path.join(hwmon_path, f"pwm{pwm_num}")

                            if pwm_num == "1" and os.path.exists(pwm_path):
                                self.enable_cpu_path = enable_path
                                self.cpu_fan_path = pwm_path
                            elif pwm_num == "2" and os.path.exists(pwm_path):
                                self.enable_gpu_path = enable_path
                                self.gpu_fan_path = pwm_path

    def set_cpu_fan_speed(self, speed):
        """Set CPU fan speed (0-255)"""
        if not self.initialized:
            self.initialize()

        speed = max(0, min(255, int(speed)))  # Clamp to valid range

        try:
            success, _, err = self._run_sudo_command(f"tee {self.cpu_fan_path}", input_data=f"{speed}\n")
            if not success:
                print(f"Error setting CPU fan speed: {err}")
                return False
            return True
        except Exception as e:
            print(f"Exception setting CPU fan speed: {e}")
            return False

    def set_gpu_fan_speed(self, speed):
        """Set GPU fan speed (0-255)"""
        if not self.initialized:
            self.initialize()

        speed = max(0, min(255, int(speed)))  # Clamp to valid range

        try:
            success, _, err = self._run_sudo_command(f"tee {self.gpu_fan_path}", input_data=f"{speed}\n")
            if not success:
                print(f"Error setting GPU fan speed: {err}")
                return False
            return True
        except Exception as e:
            print(f"Exception setting GPU fan speed: {e}")
            return False

    def get_cpu_fan_speed(self):
        """Get current CPU fan speed"""
        try:
            if os.path.exists(self.cpu_fan_path):
                with open(self.cpu_fan_path, 'r') as f:
                    speed = f.read().strip()
                    return int(speed)
        except (FileNotFoundError, ValueError, PermissionError):
            pass
        return 0

    def get_gpu_fan_speed(self):
        """Get current GPU fan speed"""
        try:
            if os.path.exists(self.gpu_fan_path):
                with open(self.gpu_fan_path, 'r') as f:
                    speed = f.read().strip()
                    return int(speed)
        except (FileNotFoundError, ValueError, PermissionError):
            pass
        return 0

    def get_cpu_fan_rpm(self):
        """Get current CPU fan speed in RPM"""
        try:
            cpu_fan_path = "/sys/class/hwmon/hwmon5/fan1_input"
            if os.path.exists(cpu_fan_path):
                with open(cpu_fan_path, 'r') as f:
                    rpm = f.read().strip()
                    return int(rpm)
        except (FileNotFoundError, ValueError, PermissionError):
            pass
        return 0

    def get_gpu_fan_rpm(self):
        """Get current GPU fan speed in RPM"""
        try:
            gpu_fan_path = "/sys/class/hwmon/hwmon5/fan2_input"
            if os.path.exists(gpu_fan_path):
                with open(gpu_fan_path, 'r') as f:
                    rpm = f.read().strip()
                    return int(rpm)
        except (FileNotFoundError, ValueError, PermissionError):
            pass
        return 0

    def set_auto_mode(self, enable=True):
        """Set fan control to auto mode (if supported by hardware)"""
        # This would typically involve writing to specific auto mode registers
        # Implementation depends on specific hardware
        pass

    def set_manual_mode(self):
        """Set fan control to manual mode"""
        try:
            # Set both CPU and GPU fans to manual mode (value 1)
            success1, _, _err1 = self._run_sudo_command(f"tee {self.enable_cpu_path}", input_data="1\n")
            success2, _, _err2 = self._run_sudo_command(f"tee {self.enable_gpu_path}", input_data="1\n")
            # For debugging - uncomment if needed
            # print(f"Manual mode: CPU={success1}, GPU={success2}")
            return success1 and success2
        except Exception as e:
            print(f"Exception setting manual mode: {e}")
            return False

    def set_auto_mode_fixed(self):
        """Set CPU fan to auto mode and keep GPU fan in manual mode"""
        try:
            # Set CPU fan to auto mode (value 2)
            success1, _, _err1 = self._run_sudo_command(f"tee {self.enable_cpu_path}", input_data="2\n")
            # Set GPU fan to manual mode (value 1)
            success2, _, _err2 = self._run_sudo_command(f"tee {self.enable_gpu_path}", input_data="2\n")
            # For debugging - uncomment if needed
            # print(f"Auto mode: CPU={success1}, GPU={success2}")
            return success1 and success2
        except Exception as e:
            print(f"Exception setting auto mode: {e}")
            return False

if __name__ == "__main__":
    # Test the fan controller
    controller = FanController()
    print("Initializing fan control...")
    if controller.initialize():
        print("Fan control initialized")
        print(f"Current CPU fan speed: {controller.get_cpu_fan_speed()}")
        print(f"Current GPU fan speed: {controller.get_gpu_fan_speed()}")

        # Test setting speeds
        print("Setting CPU fan to 128...")
        controller.set_cpu_fan_speed(128)
        print(f"CPU fan speed after setting: {controller.get_cpu_fan_speed()}")

        print("Setting GPU fan to 64...")
        controller.set_gpu_fan_speed(64)
        print(f"GPU fan speed after setting: {controller.get_gpu_fan_speed()}")
    else:
        print("Failed to initialize fan control")