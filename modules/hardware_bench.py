"""
Hardware and Robotics Bench Widget Module
"""

import serial.tools.list_ports
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
)
from PyQt6.QtCore import QTimer, Qt
from modules.serial_dialog import SerialMonitorDialog


class HardwareBenchWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.active_dialogs = []

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 10, 12, 10)
        self.layout.setSpacing(6)

        # Header
        lbl_head = QLabel("HARDWARE & ROBÓTICA (SERIAL)")
        lbl_head.setObjectName("sec_title")
        self.layout.addWidget(lbl_head)

        self.container_devices = QVBoxLayout()
        self.container_devices.setSpacing(4)
        self.layout.addLayout(self.container_devices)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.scan_ports)
        self.timer.start(2000)
        self.scan_ports()

    def _clear_devices(self):
        while self.container_devices.count() > 0:
            item = self.container_devices.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def scan_ports(self):
        all_ports = list(serial.tools.list_ports.comports())
        # Filter for actual USB/ACM ports or ports with valid VID
        real_ports = [
            p for p in all_ports
            if ("ttyUSB" in p.device or "ttyACM" in p.device or p.vid is not None)
            and not p.device.startswith("/dev/ttyS")
        ]

        self._clear_devices()

        if not real_ports:
            lbl_empty = QLabel("⚫ Nenhuma porta serial USB ativa")
            lbl_empty.setObjectName("badge_offline")
            lbl_empty.setStyleSheet("color: #94a3b8; font-size: 11px; padding: 4px;")
            self.container_devices.addWidget(lbl_empty)
            return

        for p in real_ports:
            row = QHBoxLayout()
            row.setSpacing(6)

            # Identification
            desc = p.description or "Dispositivo Serial"
            if len(desc) > 22:
                desc = desc[:20] + "..."

            lbl_port = QLabel(f"<b>{p.device}</b>")
            lbl_port.setObjectName("badge_online")
            lbl_port.setToolTip(f"{p.device} — {p.description}")

            lbl_desc = QLabel(desc)
            lbl_desc.setStyleSheet("color: #cbd5e1; font-size: 11px;")

            btn_mon = QPushButton("⚡ Monitor")
            btn_mon.setObjectName("btn_action_accent")
            btn_mon.setStyleSheet("padding: 3px 8px; font-size: 11px;")
            btn_mon.clicked.connect(lambda checked, port_name=p.device: self.open_serial_monitor(port_name))

            row.addWidget(lbl_port)
            row.addWidget(lbl_desc, 1)
            row.addWidget(btn_mon)

            w_row = QFrame()
            w_row.setLayout(row)
            self.container_devices.addWidget(w_row)

    def open_serial_monitor(self, port_name: str):
        dlg = SerialMonitorDialog(port_name, baudrate=115200, parent=self)
        dlg.show()
        self.active_dialogs.append(dlg)
