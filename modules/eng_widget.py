"""
Engineering & Hardware Tab Widget
Combines:
- Hardware Detection & Firmware Flasher (9 utilities + Erase + Serial Monitor)
- Engineering Projects integration with .hud.json (like ~/develop/mp3)
- Windows VM (Fusion 360) Docker management
"""

import os
import json
import subprocess
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QScrollArea, QWidget, QMessageBox
)
from PyQt6.QtCore import QTimer, Qt

from modules.hardware_flasher import HardwareFlasherWidget
from modules.vm_widget import WindowsVMWidget

DEVELOP_DIR = os.path.expanduser("~/develop")
ANTIGRAVITY_IDE = "/home/usuario/.local/bin/antigravity-ide"


class EngHardwareWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        # Scroll area for eng tab
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(8)

        # 1. Hardware Flasher Widget
        self.flasher = HardwareFlasherWidget(self)
        c_layout.addWidget(self.flasher)

        # 2. Engineering Projects (.hud.json)
        self.card_projects = QFrame()
        self.card_projects.setStyleSheet("background-color: rgba(20, 24, 32, 0.7); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 8px; padding: 6px;")
        p_layout = QVBoxLayout(self.card_projects)
        p_layout.setContentsMargins(6, 6, 6, 6)
        p_layout.setSpacing(4)

        h_phead = QHBoxLayout()
        lbl_phead = QLabel("PROJETOS DE ENGENHARIA (.hud.json):")
        lbl_phead.setStyleSheet("font-size: 9px; font-weight: 700; color: #94a3b8;")
        h_phead.addWidget(lbl_phead)
        h_phead.addStretch()

        btn_ref_proj = QPushButton("🔄")
        btn_ref_proj.setObjectName("btn_icon")
        btn_ref_proj.setFixedSize(20, 20)
        btn_ref_proj.clicked.connect(self.scan_hud_projects)
        h_phead.addWidget(btn_ref_proj)
        p_layout.addLayout(h_phead)

        self.hud_projects_layout = QVBoxLayout()
        self.hud_projects_layout.setSpacing(4)
        p_layout.addLayout(self.hud_projects_layout)

        c_layout.addWidget(self.card_projects)

        # 3. Windows VM Control
        self.vm_widget = WindowsVMWidget(self)
        c_layout.addWidget(self.vm_widget)

        scroll.setWidget(container)
        layout.addWidget(scroll)

        self.scan_hud_projects()

    def scan_hud_projects(self):
        while self.hud_projects_layout.count() > 0:
            item = self.hud_projects_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        found = []
        if os.path.isdir(DEVELOP_DIR):
            for item in os.listdir(DEVELOP_DIR):
                p = os.path.join(DEVELOP_DIR, item)
                hud_file = os.path.join(p, ".hud.json")
                if os.path.isfile(hud_file):
                    try:
                        with open(hud_file, "r") as f:
                            cfg = json.load(f)
                            cfg["folder"] = item
                            cfg["path"] = p
                            found.append(cfg)
                    except Exception:
                        pass

        if not found:
            lbl_empty = QLabel("Nenhum .hud.json encontrado. Crie um em ~/develop/<projeto>/.hud.json")
            lbl_empty.setStyleSheet("color: #64748b; font-size: 10px; font-style: italic;")
            self.hud_projects_layout.addWidget(lbl_empty)
            return

        for p in found:
            row = QFrame()
            row.setStyleSheet("background-color: rgba(30, 35, 48, 0.6); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 6px; padding: 4px 6px;")
            h = QHBoxLayout(row)
            h.setContentsMargins(4, 2, 4, 2)
            h.setSpacing(6)

            v_info = QVBoxLayout()
            v_info.setSpacing(1)

            name = p.get("name", p["folder"])
            lbl_name = QLabel(f"⚡ {name}")
            lbl_name.setStyleSheet("font-size: 11px; font-weight: 700; color: #f1f5f9;")
            v_info.addWidget(lbl_name)

            status = p.get("status", p.get("target", ""))
            lbl_sub = QLabel(f"<span style='color: #c084fc;'>{status}</span>")
            lbl_sub.setStyleSheet("font-size: 10px;")
            v_info.addWidget(lbl_sub)
            h.addLayout(v_info, 1)

            # Flash Action
            if p["folder"] == "mp3":
                btn_flash = QPushButton("🎵 Flash MP3")
                btn_flash.setStyleSheet("background-color: rgba(168, 85, 247, 0.2); border: 1px solid rgba(168, 85, 247, 0.4); color: #c084fc; font-size: 10px; font-weight: 700; padding: 3px 6px;")
                btn_flash.clicked.connect(lambda: self.flasher._start_flash("mp3_bt"))
                h.addWidget(btn_flash)

            # Open IDE
            btn_ide = QPushButton("⚡ IDE")
            btn_ide.setStyleSheet("background-color: rgba(14, 165, 233, 0.15); border: 1px solid rgba(14, 165, 233, 0.35); color: #38bdf8; font-size: 10px; font-weight: 600; padding: 3px 6px;")
            btn_ide.clicked.connect(lambda _, path=p["path"]: self._open_ide(path))
            h.addWidget(btn_ide)

            self.hud_projects_layout.addWidget(row)

    def _open_ide(self, path: str):
        if os.path.exists(ANTIGRAVITY_IDE):
            subprocess.Popen([ANTIGRAVITY_IDE, path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
