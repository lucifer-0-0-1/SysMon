#!/usr/bin/env python3
"""
Plugins package for Laptop Monitor
"""

# This file makes the plugins directory a Python package
# Individual plugin modules can be added here

__all__ = []

def discover_plugins():
    """Discover available plugins in the plugins directory"""
    plugins = []
    plugins_dir = os.path.dirname(__file__)

    for file in os.listdir(plugins_dir):
        if file.endswith('.py') and file != '__init__.py':
            plugin_name = file[:-3]  # Remove .py extension
            plugins.append(plugin_name)

    return plugins

def load_plugin(plugin_name):
    """Load a specific plugin by name"""
    try:
        plugin_module = __import__(f'.{plugin_name}', package='plugins')
        return plugin_module
    except ImportError as e:
        print(f"Error loading plugin {plugin_name}: {e}")
        return None