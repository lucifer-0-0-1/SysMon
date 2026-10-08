#!/usr/bin/env python3
"""
System monitoring module for Laptop Monitor
"""

import functools
import glob
import os
import re
import subprocess
import time

import psutil


def _read(path, default=None):
    """Read a sysfs file, returning default on any failure"""
    try:
        with open(path) as f:
            return f.read().strip()
    except (OSError, ValueError):
        return default


def find_hwmon(name):
    """Return the hwmon dir whose 'name' matches; hwmonN numbering changes between boots"""
    for path in sorted(glob.glob("/sys/class/hwmon/hwmon*")):
        if _read(os.path.join(path, "name")) == name:
            return path
    return None


class Monitor:
    # Sensor chips in the order we trust them for "the CPU temperature"
    CPU_CHIPS = ("coretemp", "k10temp", "zenpower", "cpu_thermal", "acpitz")
    GPU_CHIPS = ("amdgpu", "nouveau", "radeon")

    def __init__(self, gpu_poll_seconds=10):
        self.gpu_poll_seconds = gpu_poll_seconds
        self._last_net = self._last_disk = self._last_pio = None
        self._smi = None
        self._smi_time = 0
        self._gpu_cache = {}
        psutil.cpu_percent(percpu=True)  # prime: first non-blocking call always returns 0

    # ---- CPU -------------------------------------------------------------
    def get_cpu_temperature(self):
        """CPU package temperature in Celsius (0.0 if unknown)"""
        temps = psutil.sensors_temperatures()
        for chip in self.CPU_CHIPS:
            entries = temps.get(chip)
            if entries:
                # Prefer the package/Tctl reading over individual cores
                for e in entries:
                    if e.label.startswith(("Package", "Tctl", "Tdie")):
                        return round(e.current, 1)
                return round(entries[0].current, 1)
        return 0.0

    def get_cpu_usage(self):
        """CPU usage % since the previous call (non-blocking)"""
        return psutil.cpu_percent(interval=None)

    def get_per_cpu_usage(self):
        return psutil.cpu_percent(interval=None, percpu=True)

    def get_cpu_info(self):
        freq = psutil.cpu_freq()
        return {
            'cores': psutil.cpu_count(logical=False),
            'threads': psutil.cpu_count(),
            'freq_mhz': round(freq.current) if freq else 0,
            'freq_max_mhz': round(freq.max) if freq else 0,
            'load_avg': os.getloadavg(),
            'uptime_s': time.time() - psutil.boot_time(),
        }

    # ---- GPU -------------------------------------------------------------
    def get_gpu_temperature(self):
        """GPU temperature in Celsius (0.0 if unknown)"""
        temps = psutil.sensors_temperatures()
        for chip in self.GPU_CHIPS:
            if temps.get(chip):
                return round(temps[chip][0].current, 1)
        gpu = self.get_gpu_info()
        if gpu.get('temp'):
            return float(gpu['temp'])
        # acer-wmi exposes the dGPU sensor as temp3 on Nitro/Predator laptops
        acer = find_hwmon("acer")
        raw = _read(f"{acer}/temp3_input") if acer else None
        return round(int(raw) / 1000, 1) if raw and raw.isdigit() else 0.0

    def get_gpu_usage(self):
        return float(self.get_gpu_info().get('util', 0))

    def get_gpu_info(self):
        """Discrete GPU stats. Never wakes a runtime-suspended NVIDIA GPU."""
        for dev in glob.glob("/sys/bus/pci/devices/*"):
            if not (_read(f"{dev}/class") or "").startswith("0x03"):
                continue
            vendor = _read(f"{dev}/vendor")
            if vendor == "0x1002":  # AMD: plain sysfs reads, cheap
                busy = _read(f"{dev}/gpu_busy_percent")
                if busy is None:
                    continue
                return {
                    'name': 'AMD GPU', 'state': 'active', 'util': int(busy),
                    'mem_used': int(_read(f"{dev}/mem_info_vram_used", 0)) // 2**20,
                    'mem_total': int(_read(f"{dev}/mem_info_vram_total", 0)) // 2**20,
                }
            if vendor == "0x10de":
                if _read(f"{dev}/power/runtime_status") == "suspended":
                    return {'name': 'NVIDIA GPU', 'state': 'suspended (power saving)'}
                return self._poll_nvidia_smi()
        return {}

    def _poll_nvidia_smi(self):
        """Run nvidia-smi asynchronously so the GUI never blocks on it"""
        if self._smi and self._smi.poll() is not None:
            out = self._smi.stdout.read()
            self._smi = None
            parts = [p.strip() for p in out.split(",")]
            if len(parts) == 7:
                keys = ('name', 'temp', 'util', 'mem_used', 'mem_total', 'power', 'clock')
                self._gpu_cache = dict(zip(keys, parts), state='active')
        # ponytail: fixed poll period; must exceed the driver's autosuspend delay or the dGPU never sleeps
        if self._smi is None and time.time() - self._smi_time >= self.gpu_poll_seconds:
            self._smi_time = time.time()
            try:
                self._smi = subprocess.Popen(
                    ["nvidia-smi", "--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,"
                     "memory.total,power.draw,clocks.gr", "--format=csv,noheader,nounits"],
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            except OSError:
                return {'name': 'NVIDIA GPU', 'state': 'nvidia-smi not installed'}
        return self._gpu_cache or {'name': 'NVIDIA GPU', 'state': 'active'}

    # ---- Memory / disk / network ----------------------------------------
    def get_memory_usage(self):
        return psutil.virtual_memory().percent

    def get_memory_info(self):
        return psutil.virtual_memory(), psutil.swap_memory()

    def get_disk_usage(self):
        return psutil.disk_usage('/').percent

    def get_partitions(self):
        result = []
        for p in psutil.disk_partitions():
            try:
                result.append((p, psutil.disk_usage(p.mountpoint)))
            except OSError:
                pass
        return result

    def get_network_stats(self):
        n = psutil.net_io_counters()
        return {'bytes_sent': n.bytes_sent, 'bytes_recv': n.bytes_recv,
                'packets_sent': n.packets_sent, 'packets_recv': n.packets_recv}

    def get_network_rates(self):
        """Per-interface (down, up) bytes/s since the previous call"""
        now, counters = time.time(), psutil.net_io_counters(pernic=True)
        rates = _rates(self._last_net, (now, counters), lambda c: (c.bytes_recv, c.bytes_sent))
        self._last_net = (now, counters)
        return rates

    def get_disk_rates(self):
        """Per-disk (read, write) bytes/s since the previous call"""
        now, counters = time.time(), psutil.disk_io_counters(perdisk=True) or {}
        rates = _rates(self._last_disk, (now, counters), lambda c: (c.read_bytes, c.write_bytes))
        self._last_disk = (now, counters)
        return rates

    # ---- Fans / battery / processes -------------------------------------
    def get_fan_speeds(self):
        """{'chip fanN': rpm} for every fan the kernel exposes"""
        return {f"{chip} {f.label or i + 1}": f.current
                for chip, fans in psutil.sensors_fans().items()
                for i, f in enumerate(fans)}

    def get_all_temperatures(self):
        return psutil.sensors_temperatures()

    def get_battery(self):
        bat = psutil.sensors_battery()
        if bat is None:
            return None
        info = {'percent': round(bat.percent, 1), 'plugged': bat.power_plugged,
                'secsleft': bat.secsleft if bat.secsleft >= 0 else None}
        for path in glob.glob("/sys/class/power_supply/BAT*"):
            info['status'] = _read(f"{path}/status", "Unknown")
            info['cycles'] = _read(f"{path}/cycle_count")
            # Drivers report either energy (µWh/µW) or charge (µAh/µA) — handle both
            power = _read(f"{path}/power_now")
            cur, volt = _read(f"{path}/current_now"), _read(f"{path}/voltage_now")
            if power:
                info['watts'] = int(power) / 1e6
            elif cur and volt:
                info['watts'] = int(cur) * int(volt) / 1e12
            for kind in ("energy", "charge"):
                full, design = _read(f"{path}/{kind}_full"), _read(f"{path}/{kind}_full_design")
                if full and design and int(design):
                    info['health'] = round(100 * int(full) / int(design), 1)
                    break
            break
        return info

    def get_processes(self):
        """Process info dicts; 'read'/'write' are disk bytes/s since the previous call (None if unreadable)"""
        attrs = ['pid', 'ppid', 'name', 'username', 'uids', 'cpu_percent', 'memory_info', 'num_threads',
                 'nice', 'status', 'cmdline', 'io_counters']
        now, procs = time.time(), [p.info for p in psutil.process_iter(attrs, ad_value=None)]
        counters = {p['pid']: c for p in procs if (c := p.pop('io_counters'))}
        rates = _rates(self._last_pio, (now, counters), lambda c: (c.read_bytes, c.write_bytes))
        self._last_pio = (now, counters)
        for p in procs:
            p['read'], p['write'] = rates.get(p['pid'], (None, None))
        return procs


def app_id(pid):
    """Desktop app a process belongs to, from its systemd unit (app-<id>[@x|-N].scope/.service), else None"""
    path = (_read(f"/proc/{pid}/cgroup") or "").rpartition("::")[2]
    for unit in reversed(path.split("/")):
        m = re.fullmatch(r"app-(.+?)(?:@[^.]*|-\d+)?\.(?:scope|service)", unit)
        if m:
            return re.sub(r"\\x([0-9a-fA-F]{2})", lambda x: chr(int(x[1], 16)), m[1])
    return None


@functools.lru_cache(maxsize=None)
def desktop_entry(app):
    """(Name, Icon) from the app's .desktop file; falls back to the id (also tried without a launcher prefix)"""
    home = os.environ.get('XDG_DATA_HOME', os.path.expanduser('~/.local/share'))
    dirs = [home] + os.environ.get('XDG_DATA_DIRS', '/usr/local/share:/usr/share').split(':')
    for candidate in filter(None, (app, app.partition('-')[2])):
        for d in dirs:
            text = _read(f"{d}/applications/{candidate}.desktop")
            if text:
                fields = dict(line.split('=', 1) for line in text.split('\n[', 1)[0].splitlines() if '=' in line)
                return fields.get('Name', app), fields.get('Icon', '')
    return app, ''


def _rates(prev, cur, pick):
    if prev is None:
        return {}
    dt = (cur[0] - prev[0]) or 1
    return {k: tuple(max(0, (a - b) / dt) for a, b in zip(pick(c), pick(prev[1][k])))
            for k, c in cur[1].items() if k in prev[1]}


if __name__ == "__main__":
    m = Monitor()
    time.sleep(0.5)
    print(f"CPU Temp: {m.get_cpu_temperature()}°C  GPU Temp: {m.get_gpu_temperature()}°C")
    print(f"CPU Usage: {m.get_cpu_usage()}%  Memory: {m.get_memory_usage()}%  Disk: {m.get_disk_usage()}%")
    print(f"CPU: {m.get_cpu_info()}")
    print(f"GPU: {m.get_gpu_info()}")
    print(f"Battery: {m.get_battery()}")
    print(f"Fans: {m.get_fan_speeds()}")
