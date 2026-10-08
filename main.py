#!/usr/bin/env python3
"""
Laptop Monitor - System monitoring and fan control application
"""

import glob
import importlib.util
import os
import shutil
import signal
import socket
import subprocess
import sys
from collections import deque

import psutil
from PySide6.QtCore import QPointF, QSortFilterProxyModel, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout,
                               QFrame, QGridLayout, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox, QPushButton,
                               QRadioButton, QSlider, QSpinBox, QStackedWidget, QTreeView, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget)

# Add the current directory to Python path for imports
APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)

from config import DEFAULTS, Config
from fan_control import FanController, install_helper
from monitor import Monitor, app_id, desktop_entry
import network as net
from utils import Utils

VERSION = "1.2.0"
human = Utils.bytes_to_human_readable
STYLE = """
QFrame#card { background: palette(base); border: 1px solid palette(midlight); border-radius: 10px; }
QLabel#big { font-size: 22pt; font-weight: 600; }
QLabel#muted, QLabel#cardTitle { color: palette(placeholder-text); }
QListWidget#nav { border: none; background: transparent; font-size: 11pt; outline: 0; }
QListWidget#nav::item { padding: 9px 10px; border-radius: 6px; }
QListWidget#nav::item:selected { background: palette(highlight); color: palette(highlighted-text); }
"""


def fmt_duration(seconds):
    if seconds is None:
        return "—"
    h, m = divmod(int(seconds) // 60, 60)
    return f"{h // 24}d {h % 24}h {m}m" if h >= 24 else f"{h}h {m}m"


def muted(text=""):
    label = QLabel(text)
    label.setObjectName("muted")
    label.setWordWrap(True)
    return label


class Chart(QWidget):
    """Live area chart drawn with QPainter. ymax=None autoscales."""
    COLORS = ("#3daee9", "#f67400", "#27ae60", "#9b59b6")  # Breeze accents, readable on light and dark

    def __init__(self, title, labels, points, ymax=None, fmt="{:.0f}"):
        super().__init__()
        self.title, self.labels, self.ymax, self.fmt = title, labels, ymax, fmt
        self.series = [deque(maxlen=points) for _ in labels]
        self.setMinimumHeight(160)

    def push(self, *values):
        for s, v in zip(self.series, values):
            s.append(v)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        pal = self.palette()
        w, h = self.width(), self.height()
        p.setPen(QPen(pal.midlight().color(), 1))
        p.setBrush(pal.base())
        p.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 10, 10)

        left, top_px, bottom = 44, 34, h - 12
        top = self.ymax or max([max(s, default=0) for s in self.series] + [1]) * 1.15
        small = QFont(self.font())
        small.setPointSizeF(small.pointSizeF() * 0.85)
        p.setFont(small)
        for frac in (0, 0.5, 1):
            y = bottom - (bottom - top_px) * frac
            p.setPen(QPen(pal.midlight().color(), 1, Qt.DashLine))
            p.drawLine(QPointF(left, y), QPointF(w - 10, y))
            p.setPen(pal.placeholderText().color())
            p.drawText(0, int(y) - 8, left - 6, 16, Qt.AlignRight | Qt.AlignVCenter, self.fmt.format(top * frac))

        bold = QFont(self.font())
        bold.setBold(True)
        p.setFont(bold)
        p.setPen(pal.text().color())
        p.drawText(12, 8, w, 20, Qt.AlignLeft | Qt.AlignVCenter, self.title)

        p.setFont(self.font())
        x = w - 12
        for label, s, color in reversed(list(zip(self.labels, self.series, self.COLORS))):
            text = f"{label} {self.fmt.format(s[-1])}" if s else label
            width = p.fontMetrics().horizontalAdvance(text)
            p.setPen(QColor(color))
            p.drawText(x - width, 8, width, 20, Qt.AlignRight | Qt.AlignVCenter, text)
            x -= width + 14
            if len(s) < 2:
                continue
            step = (w - 10 - left) / (s.maxlen - 1)
            x0 = w - 10 - step * (len(s) - 1)
            line = QPainterPath()
            for i, v in enumerate(s):
                pt = QPointF(x0 + i * step, bottom - (bottom - top_px) * min(v, top) / top)
                line.lineTo(pt) if i else line.moveTo(pt)
            area = QPainterPath(line)
            area.lineTo(x0 + (len(s) - 1) * step, bottom)
            area.lineTo(x0, bottom)
            fill = QColor(color)
            fill.setAlpha(45)
            p.fillPath(area, fill)
            p.strokePath(line, QPen(QColor(color), 2))


class Tree(QTreeWidget):
    """Tree whose rows are keyed by stable ids, so refreshes keep scroll/selection/expansion"""

    def __init__(self, headers):
        super().__init__()
        self.setHeaderLabels(headers)
        self.setAlternatingRowColors(True)
        self.header().setSectionResizeMode(QHeaderView.Stretch)
        self.items, self.seen = {}, set()

    def row(self, iid, text, values=(), parent=None):
        item = self.items.get(iid)
        if item is None:
            item = QTreeWidgetItem(self.items[parent] if parent else self)
            item.setExpanded(True)
            self.items[iid] = item
        for i, value in enumerate((text, *map(str, values))):
            if item.text(i) != value:
                item.setText(i, value)
        self.seen.add(iid)

    def prune(self):
        """Remove rows not touched since the last prune"""
        for iid in [k for k in self.items if k not in self.seen]:
            item = self.items.pop(iid)
            (item.parent() or self.invisibleRootItem()).removeChild(item)
        self.seen = set()


class LiveTree(QTreeView):
    """Sortable, filterable tree of rows keyed by stable ids; refreshes keep scroll/selection/expansion.
    Sorting uses the raw values (UserRole), the display uses formats[column](value)."""
    KEY = Qt.UserRole + 1

    def __init__(self, headers, formats, sort_column, filter_column=0):
        super().__init__(sortingEnabled=True, alternatingRowColors=True, uniformRowHeights=True)
        self.formats, self.expand_new = formats, False
        self.source = QStandardItemModel(0, len(headers))
        self.source.setHorizontalHeaderLabels(headers)
        self.proxy = QSortFilterProxyModel(filterKeyColumn=filter_column, sortRole=Qt.UserRole,
                                           filterCaseSensitivity=Qt.CaseInsensitive, recursiveFilteringEnabled=True)
        self.proxy.setSourceModel(self.source)
        self.setModel(self.proxy)
        self.sortByColumn(sort_column, Qt.DescendingOrder)
        self.items, self.parents = {}, {}

    def clear(self):
        self.source.removeRows(0, self.source.rowCount())
        self.items, self.parents = {}, {}

    def update(self, rows):
        """rows: {key: (parent_key or None, values, icon or None)}; parents missing from rows become roots"""
        root, placed, created = self.source.invisibleRootItem(), set(), []
        self.proxy.setDynamicSortFilter(False)  # one re-sort per refresh, not one per changed cell

        def place(key):
            placed.add(key)
            parent_key, values, icon = rows[key]
            if parent_key not in rows or parent_key == key:
                parent_key = None
            elif parent_key not in placed:
                place(parent_key)
            parent = self.items[parent_key][0] if parent_key is not None else root
            items = self.items.get(key)
            if items is None:
                items = self.items[key] = [QStandardItem() for _ in self.formats]
                items[0].setData(key, self.KEY)
                if icon:
                    items[0].setIcon(icon)
                for item, v in zip(items, values):
                    if isinstance(v, (int, float)):
                        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                parent.appendRow(items)
                created.append(items[0])
            elif self.parents[key] != parent_key:  # reparented (e.g. orphan adopted by init)
                old = self.parents[key]
                (self.items[old][0] if old is not None else root).takeRow(items[0].row())
                parent.appendRow(items)
            self.parents[key] = parent_key
            for item, fmt, v in zip(items, self.formats, values):
                if item.data(Qt.UserRole) != v:
                    item.setData(v, Qt.UserRole)
                    item.setText("" if v is None else fmt(v))

        for key in rows:
            if key not in placed:
                place(key)
        dead = {k for k in self.items if k not in rows}
        for key in dead:
            items, parent_key = self.items.pop(key), self.parents.pop(key)
            if parent_key not in dead:  # rows under a removed parent go with it
                (self.items[parent_key][0] if parent_key is not None else root).removeRow(items[0].row())

        self.proxy.setDynamicSortFilter(True)
        self.proxy.sort(self.header().sortIndicatorSection(), self.header().sortIndicatorOrder())
        if self.expand_new:
            for item in created:
                self.expand(self.proxy.mapFromSource(item.index()))

    def selected_key(self):
        rows = self.selectionModel().selectedRows()
        return rows[0].data(self.KEY) if rows else None

    def text(self, key, column):
        return self.items[key][column].text()


def rate(v):
    return f"{human(v)}/s" if v else ""


class LaptopMonitorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = Config()
        self.monitor = Monitor(self.config.gpu_poll_seconds)
        self.fan_controller = FanController()
        self.system_info = Utils.get_system_info()
        self.plugins = self.load_plugins()
        self.alerted = set()
        self.net_rates = {}

        self.setWindowTitle(f"Laptop Monitor {VERSION}")
        self.resize(self.config.window_width, self.config.window_height)

        self.nav = QListWidget(objectName="nav")
        self.nav.setFixedWidth(170)
        self.stack = QStackedWidget()
        self.nav.currentRowChanged.connect(self.on_page_change)
        body = QWidget()
        layout = QHBoxLayout(body)
        layout.addWidget(self.nav)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(body)
        self.sys_label = muted()
        self.sys_label.setWordWrap(False)
        self.statusBar().addWidget(self.sys_label)

        self.refreshers = []
        self.create_dashboard_page()
        self.create_cores_page()
        self.create_applications_page()
        self.create_processes_page()
        self.create_details_page()
        self.create_fan_control_page()
        self.create_network_page()
        self.create_plugins_page()
        self.create_settings_page()
        self.nav.setCurrentRow(0)

        self.timer = QTimer(self, timeout=self.update_monitoring)
        self.timer.start(max(250, self.config.update_interval))
        self.update_monitoring()

    # ------------------------------------------------------------------ UI
    def add_page(self, title, icons, widget, refresh=None):
        """icons: space-separated theme names, first one the icon theme has wins"""
        icon = next((QIcon.fromTheme(i) for i in icons.split() if QIcon.hasThemeIcon(i)), QIcon())
        self.nav.addItem(QListWidgetItem(icon, title))
        self.stack.addWidget(widget)
        self.refreshers.append(refresh)

    def create_dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        tiles = QGridLayout()
        self.tiles = {}
        for i, name in enumerate(("CPU", "CPU Temp", "GPU", "Memory", "Battery", "Fans")):
            card = QFrame(objectName="card")
            box = QVBoxLayout(card)
            title, big, small = QLabel(name, objectName="cardTitle"), QLabel("—", objectName="big"), muted()
            for widget in (title, big, small):
                box.addWidget(widget)
            box.addStretch()
            tiles.addWidget(card, 0, i)
            self.tiles[name] = (big, small)
        layout.addLayout(tiles)

        n = self.config.max_history_points
        self.charts = {
            'cpu': Chart("CPU usage %", ["CPU"], n, ymax=100),
            'temp': Chart("Temperature °C", ["CPU", "GPU"], n, ymax=100),
            'mem': Chart("Memory %", ["RAM", "Swap"], n, ymax=100),
            'net': Chart("Network KiB/s", ["Down", "Up"], n),
            'gpu': Chart("GPU usage %", ["GPU"], n, ymax=100),
            'disk': Chart("Disk I/O KiB/s", ["Read", "Write"], n),
        }
        grid = QGridLayout()
        for i, chart in enumerate(self.charts.values()):
            grid.addWidget(chart, i // 2, i % 2)
        layout.addLayout(grid, 1)
        self.add_page("Dashboard", "utilities-system-monitor", page)

    def create_cores_page(self):
        page = QWidget()
        grid = QGridLayout(page)
        self.core_charts = []
        for i in range(psutil.cpu_count()):
            chart = Chart(f"Core {i}", [""], self.config.max_history_points, ymax=100)
            chart.setMinimumHeight(90)
            grid.addWidget(chart, i // 4, i % 4)
            self.core_charts.append(chart)
        self.add_page("CPU Cores", "cpu computer", page)

    def create_applications_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        bar = QHBoxLayout()
        search = QLineEdit(placeholderText="Filter by name…", clearButtonEnabled=True)
        self.app_count = muted()
        end_btn = QPushButton(QIcon.fromTheme("process-stop"), "End application")
        end_btn.clicked.connect(self.end_application)
        for widget in (search, self.app_count):
            bar.addWidget(widget)
        bar.addStretch()
        bar.addWidget(end_btn)
        layout.addLayout(bar)
        self.app_view = LiveTree(["Application", "Processes", "CPU %", "Memory", "Disk read", "Disk write"],
                                 [str, str, "{:.1f}".format, human, rate, rate], sort_column=2)
        search.textChanged.connect(self.app_view.proxy.setFilterFixedString)
        self.app_view.header().resizeSection(0, 260)
        self.app_pids = {}
        layout.addWidget(self.app_view)
        layout.addWidget(muted("Apps launched from the desktop (grouped by their systemd scope). "
                               "Expand an app to see its processes."))
        self.add_page("Applications", "preferences-desktop-apps applications-all view-list-icons", page,
                      self.refresh_applications)

    def create_processes_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        bar = QHBoxLayout()
        search = QLineEdit(placeholderText="Filter by name…", clearButtonEnabled=True)
        self.proc_show = QComboBox()
        self.proc_show.addItems(["All processes", "My processes", "User processes", "System processes"])
        self.proc_tree = QCheckBox("Tree view")
        self.proc_count = muted()
        end_btn = QPushButton(QIcon.fromTheme("process-stop"), "End process")
        kill_btn = QPushButton(QIcon.fromTheme("edit-delete"), "Kill")
        end_btn.clicked.connect(lambda: self.send_signal(signal.SIGTERM, "End"))
        kill_btn.clicked.connect(lambda: self.send_signal(signal.SIGKILL, "Kill"))
        for widget in (search, self.proc_show, self.proc_tree, self.proc_count):
            bar.addWidget(widget)
        bar.addStretch()
        bar.addWidget(end_btn)
        bar.addWidget(kill_btn)
        layout.addLayout(bar)

        self.proc_view = LiveTree(["Name", "PID", "User", "CPU %", "Memory", "Disk read", "Disk write",
                                   "Threads", "Nice", "Status", "Command"],
                                  [str, str, str, "{:.1f}".format, human, rate, rate, str, str, str, str],
                                  sort_column=3)
        self.proc_view.header().resizeSection(0, 220)
        self.proc_view.setRootIsDecorated(False)
        self.proc_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.proc_view.customContextMenuRequested.connect(self.process_menu)
        search.textChanged.connect(self.proc_view.proxy.setFilterFixedString)
        for signal_ in (self.proc_show.currentIndexChanged, self.proc_tree.toggled):
            signal_.connect(self.rebuild_processes)
        layout.addWidget(self.proc_view)
        self.add_page("Processes", "view-process-all", page, self.refresh_processes)

    def create_details_page(self):
        self.details = Tree(["Item", "Value", "Extra"])
        self.add_page("Details", "dialog-information", self.details, self.refresh_details)

    def create_fan_control_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        self.fan_widgets = []
        if not self.fan_controller.available:
            layout.addWidget(QLabel("No PWM fan control found in /sys/class/hwmon on this machine.\n"
                                    "Fan RPMs (if any) are still shown on the Dashboard and Details pages.",
                                    alignment=Qt.AlignCenter))
            self.add_page("Fan Control", "sensors-fan-symbolic fan weather-windy", page)
            return

        if self.fan_controller.needs_helper():
            self.helper_card = QFrame(objectName="card")
            row = QHBoxLayout(self.helper_card)
            row.addWidget(muted("Fan control needs a small helper installed system-wide (one admin password prompt)."), 1)
            button = QPushButton(QIcon.fromTheme("security-high"), "Enable fan control")
            button.clicked.connect(self.on_install_helper)
            row.addWidget(button)
            layout.addWidget(self.helper_card)

        mode_card = QFrame(objectName="card")
        mode = QHBoxLayout(mode_card)
        mode.addWidget(QLabel("<b>Control mode</b>"))
        self.auto_radio, self.manual_radio = QRadioButton("Auto (firmware)"), QRadioButton("Manual")
        self.mode_group = QButtonGroup(self)
        for radio in (self.auto_radio, self.manual_radio):
            self.mode_group.addButton(radio)
            mode.addWidget(radio)
        mode.addStretch()
        self.sync_mode_radio()
        self.mode_group.buttonClicked.connect(self.on_mode_change)
        layout.addWidget(mode_card)

        names = {1: "CPU Fan", 2: "GPU Fan"}
        for n in range(1, self.fan_controller.fan_count + 1):
            card = QFrame(objectName="card")
            row = QGridLayout(card)
            value, rpm = QLabel("PWM 0  (0%)"), QLabel("0 RPM", objectName="big")
            slider = QSlider(Qt.Horizontal, minimum=0, maximum=255)
            slider.valueChanged.connect(lambda v, lbl=value: lbl.setText(f"PWM {v}  ({v * 100 // 255}%)"))
            slider.sliderReleased.connect(lambda n=n: self.on_fan_release(n))
            row.addWidget(QLabel(f"<b>{names.get(n, f'Fan {n}')}</b>"), 0, 0)
            row.addWidget(rpm, 0, 1, 2, 1, Qt.AlignRight)
            row.addWidget(slider, 1, 0)
            row.addWidget(value, 2, 0)
            row.setColumnStretch(0, 1)
            layout.addWidget(card)
            self.fan_widgets.append((n, slider, rpm))
        layout.addWidget(muted(f"Device: {self.fan_controller.hwmon}  ·  Sliders apply in Manual mode. "
                               "Fans return to Auto when the app closes."))
        layout.addStretch()
        self.add_page("Fan Control", "sensors-fan-symbolic fan weather-windy", page, self.refresh_fans)

    def create_network_page(self):
        page = QWidget()
        self.net_layout = QVBoxLayout(page)
        self.net_layout.addWidget(muted("Switch a connection's DNS for this session only. \"Network DNS\" uses the "
                                        "servers your network hands out (e.g. campus DNS for internal sites); "
                                        "\"Profile DNS\" restores what the connection is configured with. "
                                        "Reconnecting also restores the profile."))
        self.net_cards = {}
        self.net_layout.addStretch()
        self.add_page("Networking", "network-wired network-workgroup preferences-system-network", page,
                      self.refresh_network)

    def on_dns_switch(self, device, network_dns):
        ok, err = net.use_network_dns(device) if network_dns else net.use_profile_dns(device)
        if not ok:
            QMessageBox.critical(self, "Networking", f"Could not change DNS on {device}:\n{err}")
        self.refresh_network()

    def create_plugins_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(muted(f"Drop .py files with get_data() into {self.config.plugins_directory}"))
        self.plugin_view = Tree(["Plugin / Metric", "Value"])
        layout.addWidget(self.plugin_view)
        self.add_page("Plugins", "plugins preferences-plugin application-x-addon", page, self.refresh_plugins)

    def create_settings_page(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        form = QFormLayout(fieldGrowthPolicy=QFormLayout.FieldsStayAtSizeHint)
        suffixes = {'update_interval': ' ms', 'cpu_temp_threshold': ' °C', 'gpu_temp_threshold': ' °C',
                    'battery_low_percent': ' %', 'gpu_poll_seconds': ' s', 'window_width': ' px', 'window_height': ' px'}
        self.setting_widgets = {}
        for key, default in DEFAULTS.items():
            value = self.config.get(key)
            if isinstance(default, bool):
                widget = QCheckBox(checked=value)
            elif isinstance(default, int):
                widget = QSpinBox(maximum=100000, value=value)
            else:
                widget = QDoubleSpinBox(maximum=150, decimals=1, value=value)
            if key in suffixes:
                widget.setSuffix(suffixes[key])
            widget.setToolTip(f"Default: {default}")
            label = key.replace('_', ' ').capitalize().replace('Cpu', 'CPU').replace('Gpu', 'GPU')
            form.addRow(label, widget)
            self.setting_widgets[key] = widget
        outer.addLayout(form)
        save = QPushButton(QIcon.fromTheme("document-save"), "Save")
        save.clicked.connect(self.save_settings)
        outer.addWidget(save, alignment=Qt.AlignLeft)
        outer.addWidget(muted(f"Saved to {self.config.env_file}. Window size and graph length apply on restart."))
        outer.addStretch()
        self.add_page("Settings", "configure", page)

    # ------------------------------------------------------------ actions
    def on_page_change(self, index):
        self.stack.setCurrentIndex(index)
        if self.refreshers[index]:
            self.refreshers[index]()

    def sync_mode_radio(self):
        (self.manual_radio if self.fan_controller.get_mode() == 1 else self.auto_radio).setChecked(True)

    def on_install_helper(self):
        if install_helper():
            self.helper_card.hide()
            self.statusBar().showMessage("Fan control enabled", 3000)
        else:
            QMessageBox.critical(self, "Fan control", "Helper was not installed (cancelled, or pkexec/polkit missing).")

    def on_fan_release(self, n):
        if self.manual_radio.isChecked():
            slider = next(s for m, s, _ in self.fan_widgets if m == n)
            self.fan_controller.set_fan_speed(n, slider.value())

    def on_mode_change(self):
        if self.manual_radio.isChecked():
            ok = self.fan_controller.set_manual_mode()
        else:
            ok = self.fan_controller.set_auto_mode_fixed()
        if not ok:
            QMessageBox.critical(self, "Fan control", "Could not change fan mode. See INSTALL.md → Fan Control Setup.")
            self.sync_mode_radio()

    def selected_process(self):
        pid = self.proc_view.selected_key()
        return (pid, self.proc_view.text(pid, 0)) if pid is not None else (None, None)

    def send_signal(self, sig, verb=None):
        """Send sig to the selected process; verb set = ask first"""
        pid, name = self.selected_process()
        if pid is None:
            return
        if verb and QMessageBox.question(self, "Confirm", f"{verb} {name} (PID {pid})?") != QMessageBox.Yes:
            return
        try:
            psutil.Process(pid).send_signal(sig)
        except psutil.NoSuchProcess:
            pass
        except psutil.AccessDenied:
            QMessageBox.critical(self, "Permission denied", f"{name} belongs to another user.")

    def renice_process(self):
        pid, name = self.selected_process()
        try:
            current = psutil.Process(pid).nice()
        except (psutil.Error, ValueError):
            return
        value, ok = QInputDialog.getInt(self, "Set priority", f"Nice value for {name} (PID {pid})\n"
                                        "-20 = highest priority, 19 = lowest", current, -20, 19)
        if not ok or value == current:
            return
        try:
            psutil.Process(pid).nice(value)
        except psutil.NoSuchProcess:
            pass
        except psutil.AccessDenied:  # raising priority or touching another user's process needs root
            try:
                ok = subprocess.run(["pkexec", "renice", "-n", str(value), "-p", str(pid)],
                                    capture_output=True, timeout=300).returncode == 0
            except (OSError, subprocess.TimeoutExpired):
                ok = False
            if not ok:
                QMessageBox.critical(self, "Set priority", "Priority was not changed (cancelled or not permitted).")

    def process_menu(self, pos):
        if self.proc_view.selected_key() is None:
            return
        menu = QMenu(self)
        menu.addAction(QIcon.fromTheme("process-stop"), "End process", lambda: self.send_signal(signal.SIGTERM, "End"))
        menu.addAction(QIcon.fromTheme("edit-delete"), "Kill", lambda: self.send_signal(signal.SIGKILL, "Kill"))
        signals = menu.addMenu("Send signal")
        for sig, desc in ((signal.SIGSTOP, "pause"), (signal.SIGCONT, "resume"), (signal.SIGHUP, "hang up"),
                          (signal.SIGINT, "interrupt"), (signal.SIGUSR1, ""), (signal.SIGUSR2, "")):
            signals.addAction(f"{sig.name} ({desc})" if desc else sig.name, lambda s=sig: self.send_signal(s))
        menu.addSeparator()
        menu.addAction("Set priority…", self.renice_process)
        menu.exec(self.proc_view.viewport().mapToGlobal(pos))

    def end_application(self):
        key = self.app_view.selected_key()
        if key is None:
            return
        key = key if isinstance(key, str) else self.app_view.parents[key]  # a process row → its app
        name, pids = self.app_view.text(key, 0), self.app_pids.get(key, [])
        if QMessageBox.question(self, "Confirm", f"End {name} ({len(pids)} processes)?") != QMessageBox.Yes:
            return
        denied = False
        for pid in pids:
            try:
                psutil.Process(pid).terminate()
            except psutil.NoSuchProcess:
                pass
            except psutil.AccessDenied:
                denied = True
        if denied:
            QMessageBox.critical(self, "Permission denied", f"Some processes of {name} belong to another user.")

    def save_settings(self):
        for key, widget in self.setting_widgets.items():
            self.config.set(key, widget.isChecked() if isinstance(widget, QCheckBox) else widget.value())
        self.config.save()
        self.monitor.gpu_poll_seconds = self.config.gpu_poll_seconds
        self.timer.setInterval(max(250, self.config.update_interval))
        self.statusBar().showMessage("Settings saved", 3000)  # temporarily replaces sys_label

    def closeEvent(self, event):
        # Never leave fans pinned at a manual speed with nobody watching temperatures
        if self.fan_controller.available and self.fan_controller.get_mode() == 1:
            self.fan_controller.set_auto_mode_fixed()
        super().closeEvent(event)

    def notify(self, key, active, title, body):
        """Desktop notification once per threshold crossing"""
        if not active:
            self.alerted.discard(key)
        elif key not in self.alerted:
            self.alerted.add(key)
            if self.config.notifications and shutil.which("notify-send"):
                subprocess.Popen(["notify-send", "-u", "critical", "-a", "Laptop Monitor",
                                  "-i", os.path.join(APP_DIR, "laptop-monitor.svg"), title, body])

    # ------------------------------------------------------------ plugins
    def load_plugins(self):
        if not self.config.plugins_enabled:
            return []
        plugins = []
        for path in sorted(glob.glob(os.path.join(APP_DIR, 'plugins', '*.py')) +
                           glob.glob(os.path.join(self.config.plugins_directory, '*.py'))):
            name = os.path.basename(path)[:-3]
            if name.startswith('_'):
                continue
            try:
                spec = importlib.util.spec_from_file_location(f"lm_plugin_{name}", path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                info = module.get_plugin_info() if hasattr(module, 'get_plugin_info') else {'name': name}
                plugins.append((name, info, module))
            except Exception as e:  # a broken user plugin must not take the app down
                print(f"Error loading plugin {path}: {e}")
        return plugins

    # ------------------------------------------------------------ refresh
    def update_monitoring(self):
        try:
            self.refresh_dashboard()
            refresh = self.refreshers[self.stack.currentIndex()]
            if refresh:
                refresh()
        except Exception as e:  # keep the loop alive; one bad sensor read shouldn't freeze the UI
            print(f"Refresh error: {e!r}")

    def tile(self, name, big, small=""):
        self.tiles[name][0].setText(big)
        self.tiles[name][1].setText(small)

    def refresh_dashboard(self):
        m = self.monitor
        cpu, cpu_temp, gpu_temp = m.get_cpu_usage(), m.get_cpu_temperature(), m.get_gpu_temperature()
        vm, swap = m.get_memory_info()
        self.net_rates = rates = m.get_network_rates()  # stateful: sample once per tick, Details reuses it
        down = sum(r[0] for nic, r in rates.items() if nic != 'lo') / 1024
        up = sum(r[1] for nic, r in rates.items() if nic != 'lo') / 1024
        info, gpu, bat = m.get_cpu_info(), m.get_gpu_info(), m.get_battery()
        self.charts['gpu'].push(float(gpu['util']) if str(gpu.get('util', '')).isdigit() else 0)

        self.charts['cpu'].push(cpu)
        self.charts['temp'].push(cpu_temp, gpu_temp)
        self.charts['mem'].push(vm.percent, swap.percent)
        self.charts['net'].push(down, up)
        self.disk_rates = m.get_disk_rates()  # stateful like net_rates; Details reuses it
        disks = [r for d, r in self.disk_rates.items()
                 if os.path.exists(f"/sys/block/{d}") and not d.startswith(('loop', 'ram', 'zram'))]
        self.charts['disk'].push(sum(r[0] for r in disks) / 1024, sum(r[1] for r in disks) / 1024)
        self.per_cpu = m.get_per_cpu_usage()
        for chart, pct in zip(self.core_charts, self.per_cpu):
            chart.push(pct)

        self.tile("CPU", f"{cpu:.0f}%", f"{info['freq_mhz']} MHz · load {info['load_avg'][0]:.2f}")
        self.tile("CPU Temp", f"{cpu_temp:.0f}°C", f"alert at {self.config.cpu_temp_threshold:.0f}°C")
        gpu_detail = gpu.get('state', 'no discrete GPU')
        if 'util' in gpu:
            gpu_detail = f"{gpu['util']}% busy" + (f" · {gpu['power']} W" if 'power' in gpu else "")
        self.tile("GPU", f"{gpu_temp:.0f}°C" if gpu_temp else "—", gpu_detail)
        self.tile("Memory", f"{vm.percent:.0f}%", f"{human(vm.used)} / {human(vm.total)} · swap {swap.percent:.0f}%")
        if bat:
            watts = f" · {bat['watts']:.1f} W" if bat.get('watts') else ""
            left = f" · {fmt_duration(bat['secsleft'])} left" if bat['secsleft'] and not bat['plugged'] else ""
            self.tile("Battery", f"{bat['percent']:.0f}%", f"{bat.get('status', '')}{watts}{left}")
        else:
            self.tile("Battery", "—", "no battery")
        fans = m.get_fan_speeds()
        self.tile("Fans", " / ".join(str(v) for v in fans.values()) or "—", "RPM" if fans else "no fan sensors")

        self.sys_label.setText(f"{self.system_info.get('PRETTY_NAME', 'Linux')}  ·  {self.system_info['hostname']}  ·  "
                               f"kernel {self.system_info['kernel']}  ·  up {fmt_duration(info['uptime_s'])}")

        self.notify('cpu', cpu_temp >= self.config.cpu_temp_threshold, "CPU is hot", f"CPU at {cpu_temp:.0f}°C")
        self.notify('gpu', gpu_temp >= self.config.gpu_temp_threshold, "GPU is hot", f"GPU at {gpu_temp:.0f}°C")
        self.notify('bat', bool(bat) and not bat['plugged'] and bat['percent'] <= self.config.battery_low_percent,
                    "Battery low", f"{bat['percent']:.0f}% remaining" if bat else "")

    def rebuild_processes(self):
        self.proc_view.clear()
        self.proc_view.expand_new = self.proc_tree.isChecked()
        self.proc_view.setRootIsDecorated(self.proc_tree.isChecked())
        self.refresh_processes()

    def refresh_processes(self):
        show, tree, me = self.proc_show.currentIndex(), self.proc_tree.isChecked(), os.getuid()
        rows = {}
        for p in self.monitor.get_processes():
            uid = p['uids'].real if p['uids'] else 0
            if (show == 1 and uid != me) or (show == 2 and uid < 1000) or (show == 3 and uid >= 1000):
                continue
            mem = p['memory_info']
            rows[p['pid']] = (p['ppid'] if tree else None,
                              (p['name'] or '', p['pid'], p['username'] or '', round(p['cpu_percent'] or 0, 1),
                               mem.rss if mem else None, p['read'], p['write'], p['num_threads'], p['nice'],
                               p['status'], ' '.join(p['cmdline'] or [])), None)
        self.proc_view.update(rows)
        self.proc_count.setText(f"{len(rows)} processes")

    def refresh_applications(self):
        apps, rows = {}, {}
        for p in self.monitor.get_processes():
            app = app_id(p['pid'])
            if app:
                apps.setdefault(f"app:{app}", []).append(p)
        for key, procs in apps.items():
            name, icon = desktop_entry(key[4:])
            mem = [p['memory_info'].rss for p in procs if p['memory_info']]
            total = lambda field: sum(p[field] or 0 for p in procs)
            rows[key] = (None, (name, len(procs), round(total('cpu_percent'), 1), sum(mem), total('read'),
                                total('write')), QIcon.fromTheme(icon) if icon else None)
            for p in procs:
                rows[p['pid']] = (key, (f"{p['name']}  ({p['pid']})", None, round(p['cpu_percent'] or 0, 1),
                                        p['memory_info'].rss if p['memory_info'] else None, p['read'], p['write']),
                                  None)
        self.app_pids = {key: [p['pid'] for p in procs] for key, procs in apps.items()}
        self.app_view.update(rows)
        self.app_count.setText(f"{len(apps)} applications")

    def refresh_details(self):
        m, d = self.monitor, self.details
        info = m.get_cpu_info()
        d.row('cpu', "CPU", (f"{info['cores']} cores / {info['threads']} threads",
                             f"{info['freq_mhz']} / {info['freq_max_mhz']} MHz"))
        d.row('cpu/load', "Load average (1/5/15 min)", (" / ".join(f"{x:.2f}" for x in info['load_avg']), ""), 'cpu')
        freqs = psutil.cpu_freq(percpu=True)
        for i, pct in enumerate(self.per_cpu):
            mhz = f"{freqs[i].current:.0f} MHz" if i < len(freqs) else ""
            d.row(f'cpu/{i}', f"Core {i}", (f"{pct:.0f}%", mhz), 'cpu')

        gpu = m.get_gpu_info()
        d.row('gpu', "GPU", (gpu.get('name', 'none detected'), gpu.get('state', '')))
        for key, label, unit in (('util', 'Utilization', '%'), ('temp', 'Temperature', '°C'),
                                 ('power', 'Power', ' W'), ('clock', 'Clock', ' MHz')):
            if key in gpu:
                d.row(f'gpu/{key}', label, (f"{gpu[key]}{unit}", ""), 'gpu')
        if 'mem_total' in gpu:
            d.row('gpu/mem', "VRAM", (f"{gpu['mem_used']} / {gpu['mem_total']} MiB", ""), 'gpu')

        bat = m.get_battery()
        if bat:
            d.row('bat', "Battery", (f"{bat['percent']}%", bat.get('status', '')))
            for key, label, fmt in (('watts', 'Power draw', "{:.2f} W"), ('health', 'Health (full vs design)', "{}%"),
                                    ('cycles', 'Charge cycles', "{}"), ('secsleft', 'Time left', None)):
                if bat.get(key) is not None:
                    d.row(f'bat/{key}', label, (fmt.format(bat[key]) if fmt else fmt_duration(bat[key]), ""), 'bat')

        d.row('temps', "Temperatures")
        for chip, entries in m.get_all_temperatures().items():
            d.row(f'temps/{chip}', chip, (), 'temps')
            for i, e in enumerate(entries):
                limits = " · ".join(f"{k} {v:.0f}°C" for k, v in (('high', e.high), ('crit', e.critical)) if v)
                d.row(f'temps/{chip}/{i}', e.label or f"sensor {i + 1}", (f"{e.current:.1f}°C", limits),
                      f'temps/{chip}')

        d.row('fans', "Fans")
        for name, rpm in m.get_fan_speeds().items():
            d.row(f'fans/{name}', name, (f"{rpm} RPM", ""), 'fans')

        vm, swap = m.get_memory_info()
        d.row('mem', "Memory", (f"{human(vm.used)} / {human(vm.total)}", f"{vm.percent}%"))
        d.row('mem/avail', "Available", (human(vm.available), ""), 'mem')
        d.row('mem/cache', "Buffers + cache", (human(getattr(vm, 'buffers', 0) + getattr(vm, 'cached', 0)), ""), 'mem')
        d.row('mem/swap', "Swap", (f"{human(swap.used)} / {human(swap.total)}", f"{swap.percent}%"), 'mem')

        d.row('disks', "Disks")
        for p, u in m.get_partitions():
            d.row(f'disks/{p.mountpoint}', f"{p.mountpoint}  ({p.device}, {p.fstype})",
                  (f"{human(u.used)} / {human(u.total)}", f"{u.percent}% used"), 'disks')
        for disk, (r, w) in sorted(self.disk_rates.items()):
            if not disk.startswith(('loop', 'ram', 'zram')):
                d.row(f'disks/io/{disk}', f"{disk} I/O", (f"read {human(r)}/s", f"write {human(w)}/s"), 'disks')

        d.row('net', "Network")
        addrs = psutil.net_if_addrs()
        stats = psutil.net_io_counters(pernic=True)
        for nic, (rx, tx) in sorted(self.net_rates.items()):
            ip = next((a.address for a in addrs.get(nic, []) if a.family == socket.AF_INET), '')
            d.row(f'net/{nic}', f"{nic}  {ip}", (f"↓ {human(rx)}/s  ↑ {human(tx)}/s",
                                                  f"total ↓ {human(stats[nic].bytes_recv)} ↑ {human(stats[nic].bytes_sent)}"),
                  'net')
        d.prune()

    def refresh_fans(self):
        for n, slider, rpm in self.fan_widgets:
            if not slider.isSliderDown():
                slider.setValue(self.fan_controller.get_fan_speed(n))
            rpm.setText(f"{self.fan_controller.get_fan_rpm(n)} RPM")

    def refresh_network(self):
        devices = net.devices()
        for device in [d for d in self.net_cards if d not in devices]:
            self.net_cards.pop(device)[0].deleteLater()
        for device, connection in devices.items():
            if device not in self.net_cards:
                card = QFrame(objectName="card")
                row = QHBoxLayout(card)
                label = QLabel()
                row.addWidget(label, 1)
                for text, network_dns in (("Network DNS", True), ("Profile DNS", False)):
                    button = QPushButton(text)
                    button.clicked.connect(lambda _=False, d=device, n=network_dns: self.on_dns_switch(d, n))
                    row.addWidget(button)
                self.net_layout.insertWidget(self.net_layout.count() - 1, card)
                self.net_cards[device] = (card, label)
            active, dhcp = net.dns_info(device)
            self.net_cards[device][1].setText(
                f"<b>{connection}</b> ({device})<br>DNS in use: {', '.join(active) or '—'}"
                f"<br><span style='color:gray'>Network offers: {', '.join(dhcp) or '—'}</span>")

    def refresh_plugins(self):
        v = self.plugin_view
        for name, info, module in self.plugins:
            v.row(name, info.get('name', name), (info.get('version', ''),))
            try:
                data = module.get_data()
            except Exception as e:
                data = {'error': e}
            for key, value in data.items():
                v.row(f'{name}/{key}', key, (value,), name)
        v.prune()


def main():
    if '--version' in sys.argv:
        print(f"laptop-monitor {VERSION}")
        return
    app = QApplication(sys.argv)
    app.setApplicationName("Laptop Monitor")
    app.setDesktopFileName("laptop-monitor")  # Wayland: match the .desktop entry for the taskbar icon
    app.setWindowIcon(QIcon(os.path.join(APP_DIR, "laptop-monitor.svg")))
    app.setStyleSheet(STYLE)
    window = LaptopMonitorApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
