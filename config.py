#!/usr/bin/env fccython3
"""
Configuration management for Laptop Monitor
Handles environment variables and application settings
"""

import os
from dotenv import load_dotenv

class Config:
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()

        # Application settings
        self.update_interval = int(os.getenv('UPDATE_INTERVAL', '500'))  # milliseconds (faster polling)
        self.max_history_points = int(os.getenv('MAX_HISTORY_POINTS', '50'))

        # Fan control settings
        self.auto_mode_enabled = os.getenv('AUTO_MODE_ENABLED', 'false').lower() == 'true'
        self.cpu_temp_threshold = float(os.getenv('CPU_TEMP_THRESHOLD', '75.0'))  # Celsius
        self.gpu_temp_threshold = float(os.getenv('GPU_TEMP_THRESHOLD', '80.0'))  # Celsius
        self.fan_min_speed = int(os.getenv('FAN_MIN_SPEED', '30'))
        self.fan_max_speed = int(os.getenv('FAN_MAX_SPEED', '255'))

        # Monitoring settings
        self.show_gpu_monitoring = os.getenv('SHOW_GPU_MONITORING', 'true').lower() == 'true'
        self.show_memory_monitoring = os.getenv('SHOW_MEMORY_MONITORING', 'true').lower() == 'true'
        self.show_disk_monitoring = os.getenv('SHOW_DISK_MONITORING', 'true').lower() == 'true'
        self.show_network_monitoring = os.getenv('SHOW_NETWORK_MONITORING', 'false').lower() == 'true'

        # GUI settings
        self.window_width = int(os.getenv('WINDOW_WIDTH', '800'))
        self.window_height = int(os.getenv('WINDOW_HEIGHT', '600'))
        self.theme = os.getenv('THEME', 'default')

        # Plugin settings
        self.plugins_enabled = os.getenv('PLUGINS_ENABLED', 'true').lower() == 'true'
        self.plugins_directory = os.getenv('PLUGINS_DIRECTORY', './plugins')

        # Paths
        self.app_dir = os.path.dirname(os.path.abspath(__file__))
        self.env_file = os.path.join(self.app_dir, '.env')

    def get(self, key, default=None):
        """Get configuration value by key"""
        return getattr(self, key, default)

    def set(self, key, value):
        """Set configuration value by key"""
        setattr(self, key, value)
        # Update environment variable
        os.environ[key] = str(value)

    def save_to_env(self):
        """Save current configuration to .env file"""
        env_lines = []
        for key in dir(self):
            if not key.startswith('_') and not callable(getattr(self, key)):
                value = getattr(self, key)
                env_lines.append(f"{key}={value}")

        with open(self.env_file, 'w') as f:
            f.write('\n'.join(env_lines))

    def load_from_env(self):
        """Load configuration from .env file"""
        if os.path.exists(self.env_file):
            load_dotenv(self.env_file)
            # Reload attributes from environment
            self.__init__()

if __name__ == "__main__":
    # Test the config
    config = Config()
    print(f"Update interval: {config.update_interval}ms")
    print(f"CPU temp threshold: {config.cpu_temp_threshold}°C")
    print(f"GPU temp threshold: {config.gpu_temp_threshold}°C")
    print(f"Window size: {config.window_width}x{config.window_height}")