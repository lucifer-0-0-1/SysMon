#!/bin/sh
# Install the app into a root directory, as a distro package lays it out.
# usage: packaging/install-files.sh DESTDIR
set -eu
cd "$(dirname "$0")/.."
dest=$1
share="$dest/usr/share/laptop-monitor"
install -Dm644 -t "$share" main.py monitor.py fan_control.py config.py utils.py laptop-monitor.svg
install -Dm644 -t "$share/plugins" plugins/*.py
install -Dm755 fanctl "$dest/usr/lib/laptop-monitor/fanctl"
install -Dm755 packaging/laptop-monitor "$dest/usr/bin/laptop-monitor"
install -Dm644 packaging/laptop-monitor.desktop "$dest/usr/share/applications/laptop-monitor.desktop"
install -Dm644 laptop-monitor.svg "$dest/usr/share/icons/hicolor/scalable/apps/laptop-monitor.svg"
install -Dm644 packaging/org.laptopmonitor.fanctl.policy "$dest/usr/share/polkit-1/actions/org.laptopmonitor.fanctl.policy"
