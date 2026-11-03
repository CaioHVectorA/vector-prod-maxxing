"""
Smart Projects Module (Pinned Priority Projects + Recently Active in Today/Yesterday)
"""

import os
import time
import json
import subprocess
from typing import List, Dict, Set
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QInputDialog
)
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, Qt
from config import DEVELOP_DIR, PREFERRED_IDE, FALLBACK_IDE

CONFIG_DIR = os.path.expanduser("~/.config/desktop-hud")
PINNED_FILE = os.path.join(CONFIG_DIR, "pinned_projects.json")

DEFAULT_PINNED = ["sumo-app", "rl-robot", "haxball-rl", "vss-ironcup-rl", "tcg-simulator"]


def load_pinned_projects() -> List[str]:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if os.path.exists(PINNED_FILE):
        try:
            with open(PINNED_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    return list(DEFAULT_PINNED)


def save_pinned_projects(pinned: List[str]):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    try:
        with open(PINNED_FILE, "w") as f:
            json.dump(pinned, f, indent=2)
    except Exception:
        pass


class ProjectsScannerThread(QThread):
    scanned = pyqtSignal(dict)

    def __init__(self, base_dir: str, pinned_list: List[str]):
        super().__init__()
        self.base_dir = base_dir
        self.pinned_list = pinned_list

    def run(self):
        pinned_data = []
        recent_data = []

        if not os.path.exists(self.base_dir):
            self.scanned.emit({"pinned": [], "recent": []})
            return

        now = time.time()
        two_days_ago = now - (48 * 3600)

        all_dirs = []
        try:
            all_dirs = os.listdir(self.base_dir)
        except Exception:
            pass

        # 1. Gather Pinned Projects info
        for name in self.pinned_list:
            full_path = os.path.join(self.base_dir, name)
            if os.path.exists(full_path):
                branch = self._get_branch(full_path)
                pinned_data.append({
                    "name": name,
                    "path": full_path,
                    "branch": branch,
                    "is_pinned": True
                })

        # 2. Gather Recently modified (Today or Yesterday)
        for name in all_dirs:
            if name in self.pinned_list:
                continue
            full_path = os.path.join(self.base_dir, name)
            if not os.path.isdir(full_path):
                continue

            # Check latest mtime inside git or folder
            mtime = self._get_latest_activity(full_path)
            if mtime >= two_days_ago:
                branch = self._get_branch(full_path)
                diff_hours = (now - mtime) / 3600
                rel_time = "Hoje" if diff_hours < 24 else "Ontem"
                recent_data.append({
                    "name": name,
                    "path": full_path,
                    "branch": branch,
                    "rel_time": rel_time,
                    "mtime": mtime,
                    "is_pinned": False
                })

        recent_data.sort(key=lambda x: x["mtime"], reverse=True)

        self.scanned.emit({
            "pinned": pinned_data,
            "recent": recent_data[:4]
        })

    def _get_branch(self, path: str) -> str:
        try:
            res = subprocess.run(
                ["git", "-C", path, "branch", "--show-current"],
                capture_output=True, text=True, timeout=1.2
            )
            return res.stdout.strip() or "main"
        except Exception:
            return "repo"

    def _get_latest_activity(self, path: str) -> float:
        mtimes = [os.path.getmtime(path)]
        git_head = os.path.join(path, ".git", "logs", "HEAD")
        git_index = os.path.join(path, ".git", "index")
        if os.path.exists(git_head):
            mtimes.append(os.path.getmtime(git_head))
        if os.path.exists(git_index):
            mtimes.append(os.path.getmtime(git_index))
        return max(mtimes)


class ProjectItemWidget(QFrame):
    unpinned = pyqtSignal(str)

    def __init__(self, proj: dict, parent=None):
        super().__init__(parent)
        self.proj = proj

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        # Name button
        btn_open = QPushButton(proj["name"])
        btn_open.setStyleSheet("""
            text-align: left;
            padding: 4px 6px;
            font-size: 11px;
            font-weight: 700;
            background-color: rgba(35, 40, 52, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 5px;
        """)
        btn_open.setToolTip(f"Abrir {proj['name']} na IDE")
        btn_open.clicked.connect(self._open_in_ide)
        layout.addWidget(btn_open, 1)

        # Branch label
        lbl_branch = QLabel(proj["branch"])
        lbl_branch.setObjectName("badge_branch")
        layout.addWidget(lbl_branch)

        # Extra info (Pin icon or Recent tag)
        if proj.get("is_pinned"):
            btn_star = QPushButton("★")
            btn_star.setObjectName("btn_icon")
            btn_star.setStyleSheet("color: #f59e0b; font-size: 11px; padding: 2px 4px;")
            btn_star.setToolTip("Desafixar projeto")
            btn_star.clicked.connect(lambda: self.unpinned.emit(self.proj["name"]))
            layout.addWidget(btn_star)
        else:
            lbl_rel = QLabel(proj.get("rel_time", "recente"))
            lbl_rel.setObjectName("badge_clean")
            layout.addWidget(lbl_rel)

        # Terminal button
        btn_term = QPushButton(">_")
        btn_term.setObjectName("btn_icon")
        btn_term.setToolTip("Abrir terminal nesta pasta")
        btn_term.clicked.connect(self._open_terminal)
        layout.addWidget(btn_term)

    def _open_in_ide(self):
        ide = PREFERRED_IDE if os.path.exists(PREFERRED_IDE) else FALLBACK_IDE
        subprocess.Popen([ide, self.proj["path"]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _open_terminal(self):
        cmd = ["gnome-terminal", f"--working-directory={self.proj['path']}"]
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class SmartProjectsWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.pinned_list = load_pinned_projects()
        self.scanner_thread = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Header
        h_head = QHBoxLayout()
        lbl_head = QLabel("📁 PROJETOS (PRIORITÁRIOS & ATIVOS)")
        lbl_head.setObjectName("sec_title")
        h_head.addWidget(lbl_head)
        h_head.addStretch()

        btn_add = QPushButton("⭐ +")
        btn_add.setObjectName("btn_icon")
        btn_add.setStyleSheet("padding: 2px 6px; font-size: 10px;")
        btn_add.setToolTip("Fixar novo projeto")
        btn_add.clicked.connect(self._prompt_add_pin)
        h_head.addWidget(btn_add)

        btn_refresh = QPushButton("🔄")
        btn_refresh.setObjectName("btn_icon")
        btn_refresh.setStyleSheet("padding: 2px 6px; font-size: 10px;")
        btn_refresh.setToolTip("Atualizar projetos")
        btn_refresh.clicked.connect(self.scan_projects)
        h_head.addWidget(btn_refresh)
        layout.addLayout(h_head)

        # Container
        self.items_container = QVBoxLayout()
        self.items_container.setSpacing(4)
        layout.addLayout(self.items_container)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.scan_projects)
        self.timer.start(10000)
        self.scan_projects()

    def _prompt_add_pin(self):
        try:
            available = [d for d in os.listdir(DEVELOP_DIR) if os.path.isdir(os.path.join(DEVELOP_DIR, d)) and d not in self.pinned_list]
            available.sort()
            if not available:
                return
            item, ok = QInputDialog.getItem(self, "Fixar Projeto", "Escolha um projeto do ~/develop para priorizar:", available, 0, False)
            if ok and item:
                self.pinned_list.append(item)
                save_pinned_projects(self.pinned_list)
                self.scan_projects()
        except Exception:
            pass

    def _on_unpin(self, name: str):
        if name in self.pinned_list:
            self.pinned_list.remove(name)
            save_pinned_projects(self.pinned_list)
            self.scan_projects()

    def scan_projects(self):
        self.pinned_list = load_pinned_projects()
        if self.scanner_thread and self.scanner_thread.isRunning():
            return
        self.scanner_thread = ProjectsScannerThread(DEVELOP_DIR, self.pinned_list)
        self.scanner_thread.scanned.connect(self._on_scanned)
        self.scanner_thread.start()

    def _on_scanned(self, data: dict):
        while self.items_container.count() > 0:
            item = self.items_container.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        pinned = data.get("pinned", [])
        recent = data.get("recent", [])

        # 1. Pinned
        for p in pinned:
            w = ProjectItemWidget(p, self)
            w.unpinned.connect(self._on_unpin)
            self.items_container.addWidget(w)

        # 2. Recent (Only if there are any modified today/yesterday)
        if recent:
            lbl_sep = QLabel("⏱️ ATIVOS RECENTEMENTE (HOJE/ONTEM):")
            lbl_sep.setStyleSheet("font-size: 9px; font-weight: 700; color: #64748b; margin-top: 4px;")
            self.items_container.addWidget(lbl_sep)
            for p in recent:
                w = ProjectItemWidget(p, self)
                self.items_container.addWidget(w)
