"""
System Telemetry Widget (CPU, RAM, Network) using psutil
"""

import time
import psutil
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import QTimer, Qt


class SystemMonitorWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")

        self.last_net_bytes = psutil.net_io_counters()
        self.last_net_time = time.time()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Header
        lbl_head = QLabel("SISTEMA (RYZEN 7 5700U)")
        lbl_head.setObjectName("sec_title")
        layout.addWidget(lbl_head)

        # CPU Row
        cpu_box = QVBoxLayout()
        cpu_box.setSpacing(3)
        h_cpu = QHBoxLayout()
        lbl_cpu = QLabel("CPU:")
        lbl_cpu.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        self.lbl_cpu_val = QLabel("0%")
        self.lbl_cpu_val.setStyleSheet("color: #38bdf8; font-weight: 600; font-size: 11px;")
        h_cpu.addWidget(lbl_cpu)
        h_cpu.addStretch()
        h_cpu.addWidget(self.lbl_cpu_val)
        cpu_box.addLayout(h_cpu)

        self.bar_cpu = QProgressBar()
        self.bar_cpu.setObjectName("cpu_bar")
        self.bar_cpu.setRange(0, 100)
        self.bar_cpu.setValue(0)
        cpu_box.addWidget(self.bar_cpu)
        layout.addLayout(cpu_box)

        # RAM Row
        ram_box = QVBoxLayout()
        ram_box.setSpacing(3)
        h_ram = QHBoxLayout()
        lbl_ram = QLabel("Memória RAM:")
        lbl_ram.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        self.lbl_ram_val = QLabel("0.0 / 0.0 GB")
        self.lbl_ram_val.setStyleSheet("color: #818cf8; font-weight: 600; font-size: 11px;")
        h_ram.addWidget(lbl_ram)
        h_ram.addStretch()
        h_ram.addWidget(self.lbl_ram_val)
        ram_box.addLayout(h_ram)

        self.bar_ram = QProgressBar()
        self.bar_ram.setObjectName("ram_bar")
        self.bar_ram.setRange(0, 100)
        self.bar_ram.setValue(0)
        ram_box.addWidget(self.bar_ram)
        layout.addLayout(ram_box)

        # Network row
        h_net = QHBoxLayout()
        lbl_net = QLabel("Rede:")
        lbl_net.setStyleSheet("color: #94a3b8; font-size: 11px;")
        self.lbl_net_val = QLabel("↓ 0 KB/s   ↑ 0 KB/s")
        self.lbl_net_val.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        h_net.addWidget(lbl_net)
        h_net.addStretch()
        h_net.addWidget(self.lbl_net_val)
        layout.addLayout(h_net)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_telemetry)
        self.timer.start(1500)
        self.update_telemetry()

    def update_telemetry(self):
        # CPU
        cpu_pct = psutil.cpu_percent(interval=None)
        self.lbl_cpu_val.setText(f"{cpu_pct:.1f}%")
        self.bar_cpu.setValue(int(min(100, cpu_pct)))

        # RAM
        mem = psutil.virtual_memory()
        used_gb = mem.used / (1024 ** 3)
        total_gb = mem.total / (1024 ** 3)
        self.lbl_ram_val.setText(f"{used_gb:.1f} / {total_gb:.1f} GB ({mem.percent}%)")
        self.bar_ram.setValue(int(min(100, mem.percent)))

        # Network speed
        now = time.time()
        dt = max(0.1, now - self.last_net_time)
        net_now = psutil.net_io_counters()

        bytes_down = (net_now.bytes_recv - self.last_net_bytes.bytes_recv) / dt
        bytes_up = (net_now.bytes_sent - self.last_net_bytes.bytes_sent) / dt

        self.last_net_bytes = net_now
        self.last_net_time = now

        str_down = self._format_speed(bytes_down)
        str_up = self._format_speed(bytes_up)
        self.lbl_net_val.setText(f"↓ {str_down}   ↑ {str_up}")

    def _format_speed(self, bytes_sec: float) -> str:
        if bytes_sec >= 1024 * 1024:
            return f"{bytes_sec / (1024 * 1024):.1f} MB/s"
        return f"{bytes_sec / 1024:.0f} KB/s"
