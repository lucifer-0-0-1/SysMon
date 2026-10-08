#!/usr/bin/env python3
"""
DNS switching for Laptop Monitor via NetworkManager (nmcli)
Changes are runtime-only (nmcli device modify): the saved connection profile is never edited.
"""

import re
import shutil
import subprocess


def nmcli(*args):
    """Run nmcli; returns (ok, stdout or error text)"""
    if not shutil.which("nmcli"):
        return False, "nmcli not found (NetworkManager is required)"
    try:
        r = subprocess.run(["nmcli", *args], capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)
    return r.returncode == 0, (r.stdout if r.returncode == 0 else r.stderr.strip())


def devices():
    """Connected NetworkManager devices -> connection name (skips loopback/externally managed)"""
    ok, out = nmcli("-t", "-f", "DEVICE,STATE,CONNECTION", "device")
    if not ok:
        return {}
    result = {}
    for line in out.splitlines():
        dev, state, conn = re.split(r"(?<!\\):", line, maxsplit=2)
        if state == "connected":
            result[dev] = conn.replace("\\:", ":")
    return result


def dns_info(device):
    """(DNS servers in use, DNS servers offered by DHCP) for a device"""
    ok, out = nmcli("-t", "-f", "IP4,IP6,DHCP4", "device", "show", device)
    active, offered = [], []
    for line in out.splitlines() if ok else ():
        key, _, value = line.partition(":")
        if key.startswith(("IP4.DNS", "IP6.DNS")):
            active.append(value.replace("\\:", ":"))
        elif key.startswith("DHCP4.OPTION") and value.startswith("domain_name_servers ="):
            offered += value.split("=", 1)[1].split()
    return active, offered


def use_network_dns(device):
    """Use the DNS the network hands out (DHCP), e.g. campus DNS for internal hosts"""
    return nmcli("device", "modify", device, "ipv4.ignore-auto-dns", "no", "ipv6.ignore-auto-dns", "no",
                 "ipv4.dns", "", "ipv6.dns", "")


def use_profile_dns(device):
    """Drop runtime changes and go back to the connection profile's DNS"""
    return nmcli("device", "reapply", device)


if __name__ == "__main__":
    line = r"enp44s0:connected:Wired\: lab"
    assert re.split(r"(?<!\\):", line, maxsplit=2) == ["enp44s0", "connected", r"Wired\: lab"]
    for dev, conn in devices().items():
        print(dev, conn, dns_info(dev))
