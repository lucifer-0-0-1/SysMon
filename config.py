#!/usr/bin/env python3
"""
Configuration management for Laptop Monitor
Settings come from (later wins): defaults, ./.env, ~/.config/laptop-monitor/config.env, environment
"""

import os
from dotenv import dotenv_values

CONFIG_DIR = os.path.join(os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config')),
                          'laptop-monitor')

# key -> default; the default's type is the value's type
DEFAULTS = {
    'update_interval': 1000,        # milliseconds
    'max_history_points': 120,      # samples kept for dashboard graphs
    'cpu_temp_threshold': 90.0,     # Celsius, desktop notification above this
    'gpu_temp_threshold': 85.0,
    'battery_low_percent': 15,
    'notifications': True,
    'gpu_poll_seconds': 10,         # nvidia-smi period; keep above the driver's autosuspend delay
    'window_width': 1000,
    'window_height': 700,
    'plugins_enabled': True,
}


class Config:
    def __init__(self):
        self.config_dir = CONFIG_DIR
        self.env_file = os.path.join(CONFIG_DIR, 'config.env')
        self.plugins_directory = os.path.join(CONFIG_DIR, 'plugins')
        app_dir = os.path.dirname(os.path.abspath(__file__))
        values = {**dotenv_values(os.path.join(app_dir, '.env')), **dotenv_values(self.env_file), **os.environ}
        for key, default in DEFAULTS.items():
            setattr(self, key, default)
            raw = values.get(key.upper())
            if raw is not None:
                try:
                    self.set(key, raw)
                except ValueError:
                    print(f"Ignoring invalid {key.upper()}={raw!r}")

    def get(self, key, default=None):
        return getattr(self, key, default)

    def set(self, key, value):
        """Set a known key, converting to the default's type. Raises ValueError on bad input."""
        kind = type(DEFAULTS[key])
        if kind is bool and isinstance(value, str):
            value = value.strip().lower() in ('1', 'true', 'yes', 'on')
        setattr(self, key, kind(value))

    def save(self):
        os.makedirs(self.config_dir, exist_ok=True)
        with open(self.env_file, 'w') as f:
            f.writelines(f"{k.upper()}={getattr(self, k)}\n" for k in DEFAULTS)


if __name__ == "__main__":
    config = Config()
    for key in DEFAULTS:
        print(f"{key} = {config.get(key)}")
    print(f"config file: {config.env_file}")
