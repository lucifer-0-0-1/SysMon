#!/bin/sh
# Build dist/laptop-monitor_<version>_all.deb for Ubuntu 25.10+ / 26.04 LTS and Debian 13+
# (the first releases that package PySide6). Needs dpkg-deb: run on Debian/Ubuntu.
set -eu
cd "$(dirname "$0")/.."
version=$(sed -n 's/^VERSION = "\(.*\)"/\1/p' main.py)
root=build/deb
rm -rf "$root"
mkdir -p "$root/DEBIAN" dist
packaging/install-files.sh "$root"
install -Dm644 LICENSE "$root/usr/share/doc/laptop-monitor/copyright"
cat > "$root/DEBIAN/control" <<CONTROL
Package: laptop-monitor
Version: $version
Architecture: all
Section: utils
Priority: optional
Maintainer: lucifer-0-0-1 <amritam.leon@gmail.com>
Homepage: https://github.com/lucifer-0-0-1/SysMon
Installed-Size: $(du -sk "$root" | cut -f1)
Depends: python3 (>= 3.9), python3-psutil, python3-dotenv, python3-pyside6.qtwidgets, python3-pyside6.qtgui, python3-pyside6.qtcore, pkexec | policykit-1
Recommends: libnotify-bin
Description: Laptop monitor with temperatures, usage, GPU, battery, processes and fan control
 Live graphs and details for CPU, GPU, memory, disks, network, battery and
 every hardware sensor, plus a process manager and PWM fan control through
 a polkit helper.
CONTROL
dpkg-deb --root-owner-group --build "$root" "dist/laptop-monitor_${version}_all.deb"
