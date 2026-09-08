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

def main():
    """Run all tests"""
    print("Running basic tests for Laptop Monitor...\n")

    tests = [
        test_imports,
        test_monitor,
        test_config,
        test_utils
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