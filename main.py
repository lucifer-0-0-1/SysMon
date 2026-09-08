#!/usr/bin/env python3
"""
Laptop Monitor - System monitoring and fan control application
"""

import tkinter as tk
from tkinter import ttk
import sys
import os

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from monitor import Monitor
from fan_control import FanController
from config import Config
from utils import Utils

class LaptopMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Laptop Monitor")
        self.root.geometry("800x600")

        # Initialize components
        self.config = Config()
        self.utils = Utils()
        self.monitor = Monitor()
        self.fan_controller = FanController()

        # Create GUI
        self.create_widgets()

        # Start monitoring updates
        self.update_monitoring()

    def create_widgets(self):
        """Create the main GUI interface"""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        # Create tabs
        self.create_dashboard_tab()
        self.create_fan_control_tab()
        self.create_advanced_tab()
        self.create_plugins_tab()
        self.create_settings_tab()

    def create_dashboard_tab(self):
        """Create dashboard tab with graphs"""
        dashboard_frame = ttk.Frame(self.notebook)
        self.notebook.add(dashboard_frame, text="Dashboard")

        # Placeholder for graphs
        label = ttk.Label(dashboard_frame, text="Dashboard - Graphs will be displayed here")
        label.pack(expand=True)

    def create_fan_control_tab(self):
        """Create fan control tab with sliders"""
        fan_frame = ttk.Frame(self.notebook)
        self.notebook.add(fan_frame, text="Fan Control")

        # CPU Fan Control
        cpu_frame = ttk.LabelFrame(fan_frame, text="CPU Fan Control")
        cpu_frame.pack(fill='x', padx=10, pady=5)

        # CPU Fan controls with value display
        cpu_controls = ttk.Frame(cpu_frame)
        cpu_controls.pack(fill='x', padx=5, pady=2)

        ttk.Label(cpu_controls, text="CPU Fan Speed:").pack(side='left')
        self.cpu_fan_value_label = ttk.Label(cpu_controls, text="0", width=4)
        self.cpu_fan_value_label.pack(side='left', padx=(5, 10))

        self.cpu_fan_scale = ttk.Scale(cpu_frame, from_=0, to=255, orient='horizontal', command=self.on_cpu_fan_slide)
        self.cpu_fan_scale.pack(fill='x', padx=5, pady=2)
        self.cpu_fan_scale.bind("<ButtonRelease-1>", self.on_cpu_fan_change)

        # CPU Fan speed display (RPM)
        self.cpu_fan_rpm_label = ttk.Label(cpu_frame, text="CPU Fan: 0 RPM", foreground="blue")
        self.cpu_fan_rpm_label.pack(anchor='w', padx=5, pady=(0, 5))

        # GPU Fan Control
        gpu_frame = ttk.LabelFrame(fan_frame, text="GPU Fan Control")
        gpu_frame.pack(fill='x', padx=10, pady=5)

        # GPU Fan controls with value display
        gpu_controls = ttk.Frame(gpu_frame)
        gpu_controls.pack(fill='x', padx=5, pady=2)

        ttk.Label(gpu_controls, text="GPU Fan Speed:").pack(side='left')
        self.gpu_fan_value_label = ttk.Label(gpu_controls, text="0", width=4)
        self.gpu_fan_value_label.pack(side='left', padx=(5, 10))

        self.gpu_fan_scale = ttk.Scale(gpu_frame, from_=0, to=255, orient='horizontal', command=self.on_gpu_fan_slide)
        self.gpu_fan_scale.pack(fill='x', padx=5, pady=2)
        self.gpu_fan_scale.bind("<ButtonRelease-1>", self.on_gpu_fan_change)

        # GPU Fan speed display (RPM)
        self.gpu_fan_rpm_label = ttk.Label(gpu_frame, text="GPU Fan: 0 RPM", foreground="blue")
        self.gpu_fan_rpm_label.pack(anchor='w', padx=5, pady=(0, 5))

        # Mode toggle
        mode_frame = ttk.LabelFrame(fan_frame, text="Control Mode")
        mode_frame.pack(fill='x', padx=10, pady=5)

        self.mode_var = tk.StringVar(value="manual")
        ttk.Radiobutton(mode_frame, text="Manual", variable=self.mode_var, value="manual", command=self.on_mode_change).pack(anchor='w')
        ttk.Radiobutton(mode_frame, text="Auto", variable=self.mode_var, value="auto", command=self.on_mode_change).pack(anchor='w')

    def create_advanced_tab(self):
        """Create advanced monitoring tab"""
        advanced_frame = ttk.Frame(self.notebook)
        self.notebook.add(advanced_frame, text="Advanced")

        # Placeholder for advanced metrics
        label = ttk.Label(advanced_frame, text="Advanced Monitoring - Memory, Disk, Network")
        label.pack(expand=True)

    def create_plugins_tab(self):
        """Create plugins management tab"""
        plugins_frame = ttk.Frame(self.notebook)
        self.notebook.add(plugins_frame, text="Plugins")

        # Placeholder for plugins
        label = ttk.Label(plugins_frame, text="Plugins Management")
        label.pack(expand=True)

    def create_settings_tab(self):
        """Create settings tab"""
        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text="Settings")

        # Placeholder for settings
        label = ttk.Label(settings_frame, text="Application Settings")
        label.pack(expand=True)

    def on_cpu_fan_slide(self, value):
        """Handle CPU fan slider movement - update value label"""
        if self.mode_var.get() == "manual":
            speed = int(float(value))
            self.cpu_fan_value_label.config(text=str(speed))
            self.fan_controller.set_cpu_fan_speed(speed)
        else:
            # In auto mode, just update the display without setting
            speed = int(float(value))
            self.cpu_fan_value_label.config(text=str(speed))

    def on_gpu_fan_slide(self, value):
        """Handle GPU fan slider movement - update value label"""
        if self.mode_var.get() == "manual":
            speed = int(float(value))
            self.gpu_fan_value_label.config(text=str(speed))
            self.fan_controller.set_gpu_fan_speed(speed)
        else:
            # In auto mode, just update the display without setting
            speed = int(float(value))
            self.gpu_fan_value_label.config(text=str(speed))

    def on_cpu_fan_change(self, event):
        """Handle CPU fan slider release - final confirmation"""
        # The sliding already handled the setting, this is just for final state
        pass

    def on_gpu_fan_change(self, event):
        """Handle GPU fan slider release - final confirmation"""
        # The sliding already handled the setting, this is just for final state
        pass

    def on_mode_change(self):
        """Handle mode change between manual and auto"""
        if self.mode_var.get() == "manual":
            # Switch to manual mode
            success = self.fan_controller.set_manual_mode()
            if success:
                print("Switched to manual mode")
            else:
                print("Failed to switch to manual mode")
        else:
            # Switch to auto mode
            success = self.fan_controller.set_auto_mode_fixed()
            if success:
                print("Switched to auto mode")
            else:
                print("Failed to switch to auto mode")

    def update_monitoring(self):
        """Update monitoring displays"""
        # Update sensor readings
        cpu_temp = self.monitor.get_cpu_temperature()
        gpu_temp = self.monitor.get_gpu_temperature()
        cpu_usage = self.monitor.get_cpu_usage()
        gpu_usage = self.monitor.get_gpu_usage()

        # Update fan speeds from hardware (PWM values 0-255)
        cpu_fan_pwm = self.fan_controller.get_cpu_fan_speed()
        gpu_fan_pwm = self.fan_controller.get_gpu_fan_speed()

        # Update the value labels to reflect current hardware state (useful if changed by auto mode)
        self.cpu_fan_value_label.config(text=str(cpu_fan_pwm))
        self.gpu_fan_value_label.config(text=str(gpu_fan_pwm))

        # Synchronize slider positions with current hardware state
        self.cpu_fan_scale.set(cpu_fan_pwm)
        self.gpu_fan_scale.set(gpu_fan_pwm)

        # Update fan speed displays (RPM)
        cpu_rpm = self.fan_controller.get_cpu_fan_rpm()
        gpu_rpm = self.fan_controller.get_gpu_fan_rpm()
        self.cpu_fan_rpm_label.config(text=f"CPU Fan: {cpu_rpm} RPM")
        self.gpu_fan_rpm_label.config(text=f"GPU Fan: {gpu_rpm} RPM")

        # Schedule next update
        self.root.after(2000, self.update_monitoring)  # Update every 2 seconds

def main():
    root = tk.Tk()
    app = LaptopMonitorApp(root)  # pyright: ignore[reportUnusedVariable]
    root.mainloop()

if __name__ == "__main__":
    main()