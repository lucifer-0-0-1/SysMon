#!/usr/bin/env python3
"""
Basic test for Laptop Monitor components
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all modules can be imported"""
    try:
        from monitor import Monitor
        from fan_control import FanController
        from config import Config
        from utils import Utils
        print("✓ All modules imported successfully")
        return True
    except Exception as e:
        print(f"✗ Import error: {e}")
        return False

def test_monitor():
    """Test monitor functionality"""
    try:
        from monitor import Monitor
        monitor = Monitor()

        cpu_temp = monitor.get_cpu_temperature()
        gpu_temp = monitor.get_gpu_temperature()
        cpu_usage = monitor.get_cpu_usage()
        memory_usage = monitor.get_memory_usage()

        print(f"✓ Monitor test - CPU Temp: {cpu_temp}°C, GPU Temp: {gpu_temp}°C")
        print(f"  CPU Usage: {cpu_usage}%, Memory Usage: {memory_usage}%")
        return True
    except Exception as e:
        print(f"✗ Monitor test error: {e}")
        return False

def test_config():
    """Test config functionality"""
    try:
        from config import Config
        config = Config()

        update_interval = config.get('update_interval')
        cpu_threshold = config.get('cpu_temp_threshold')

        print(f"✓ Config test - Update interval: {update_interval}ms")
        print(f"  CPU threshold: {cpu_threshold}°C")
        return True
    except Exception as e:
        print(f"✗ Config test error: {e}")
        return False

def test_utils():
    """Test utils functionality"""
    try:
        from utils import Utils

        # Test byte conversion
        bytes_str = Utils.bytes_to_human_readable(1048576)
        temp_f = Utils.celsius_to_fahrenheit(25)

        print(f"✓ Utils test - 1MB = {bytes_str}")
        print(f"  25°C = {temp_f:.1f}°F")
        return True
    except Exception as e:
        print(f"✗ Utils test error: {e}")
        return False

def test_fan_control():
    """FanController discovers a pwm hwmon by content, not by hwmonN index"""
    import tempfile
    from fan_control import FanController, find_pwm_hwmon
    try:
        with tempfile.TemporaryDirectory() as base:
            os.makedirs(f"{base}/hwmon0")
            os.makedirs(f"{base}/hwmon3")
            for name, value in (("pwm1", "100"), ("pwm2", "50"), ("pwm1_enable", "1"), ("fan1_input", "2500")):
                with open(f"{base}/hwmon3/{name}", "w") as f:
                    f.write(value)
            assert find_pwm_hwmon(base) == f"{base}/hwmon3"
            fc = FanController(f"{base}/hwmon3")
            assert fc.fan_count == 2 and fc.get_mode() == 1
            assert fc.get_fan_speed(1) == 100 and fc.get_fan_rpm(1) == 2500
            assert fc.set_fan_speed(2, 999) and fc.get_fan_speed(2) == 255  # clamped
        print("✓ Fan control test")
        return True
    except Exception as e:
        print(f"✗ Fan control test error: {e!r}")
        return False

def test_fanctl_validation():
    """The root helper only accepts hwmon pwm paths and in-range values"""
    from importlib.machinery import SourceFileLoader
    validate = SourceFileLoader("fanctl", os.path.join(os.path.dirname(os.path.abspath(__file__)), "fanctl")).load_module().validate
    ok = [("/sys/class/hwmon/hwmon5/pwm1", "128", 128), ("/sys/class/hwmon/hwmon12/pwm2_enable", "2", 2)]
    bad = [("/sys/class/hwmon/hwmon5/pwm1", "256"), ("/sys/class/hwmon/hwmon5/pwm1_enable", "3"),
           ("/sys/class/hwmon/hwmon5/pwm1", "-1"), ("/sys/class/hwmon/hwmon5/../../../../etc/pwm1", "1"),
           ("/etc/shadow", "1"), ("/sys/class/hwmon/hwmon5/pwm1\n", "1")]
    try:
        for path, value, expected in ok:
            assert validate(path, value) == expected, path
        for path, value in bad:
            try:
                validate(path, value)
            except ValueError:
                continue
            raise AssertionError(f"accepted {path} {value}")
        print("✓ fanctl validation test")
        return True
    except Exception as e:
        print(f"✗ fanctl validation error: {e!r}")
        return False

def main():
    """Run all tests"""
    print("Running basic tests for Laptop Monitor...\n")

    tests = [
        test_imports,
        test_monitor,
        test_config,
        test_utils,
        test_fan_control,
        test_fanctl_validation,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())