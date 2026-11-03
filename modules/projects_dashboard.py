"""
Projects Dashboard Module (Git Status & Quick Launch)
"""

import os
import subprocess
from typing import List, Dict
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QWidget
)
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, Qt
from config import DEVELOP_DIR, PREFERRED_IDE, FALLBACK_IDE, TERMINAL_CMD


class GitScannerThread(QThread):
    projects_scanned = pyqtSignal(list)

    def __init__(self, base_dir: str):
        super().__init__()
        self.base_dir = base_dir

    def run(self):
        projects = []
        if not os.path.exists(self.base_dir):
            self.projects_scanned.emit([])
            return

        entries = []
        try:
            for name in os.listdir(self.base_dir):
                full_path = os.path.join(self.base_dir, name)
                git_dir = os.path.join(full_path, ".git")
                if os.path.isdir(full_path) and os.path.exists(git_dir):
                    try:
                        mtime = os.path.getmtime(full_path)
                        entries.append((mtime, name, full_path))
                    except Exception:
                        pass
        except Exception:
            pass

        # Sort by most recently modified
        entries.sort(key=lambda x: x[0], reverse=True)
        top_entries = entries[:6]

        for _, name, full_path in top_entries:
            branch = "main"
            status_text = "clean"
            is_clean = True
            try:
                res_b = subprocess.run(
                    ["git", "-C", full_path, "branch", "--show-current"],
                    capture_output=True, text=True, timeout=1.5
                )
                branch = res_b.stdout.strip() or "HEAD"

                res_s = subprocess.run(
                    ["git", "-C", full_path, "status", "--porcelain"],
                    capture_output=True, text=True, timeout=1.5
                )
                changes = res_s.stdout.strip().splitlines()
                if changes:
                    is_clean = False
                    status_text = f"{len(changes)} alterado{'s' if len(changes) > 1 else ''}"
                else:
                    is_clean = True
                    status_text = "clean"
            except Exception:
                pass

            projects.append({
                "name": name,
                "path": full_path,
                "branch": branch,
                "status": status_text,
                "is_clean": is_clean
            })

        self.projects_scanned.emit(projects)


class ProjectItemWidget(QFrame):
    def __init__(self, proj: dict, parent=None):
        super().__init__(parent)
        self.proj = proj

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(6)

        # Name and branch button
        btn_open = QPushButton(proj['name'])
        btn_open.setStyleSheet("""
            text-align: left;
            padding: 5px 8px;
            font-size: 12px;
            font-weight: 700;
            background-color: rgba(35, 40, 52, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 6px;
        """)
        btn_open.setToolTip(f"Abrir {proj['name']} na IDE ({proj['path']})")
        btn_open.clicked.connect(self._open_in_ide)
        layout.addWidget(btn_open, 1)

        # Branch label
        lbl_branch = QLabel(proj["branch"])
        lbl_branch.setObjectName("badge_branch")
        layout.addWidget(lbl_branch)

        # Status label
        lbl_status = QLabel(proj["status"])
        if proj["is_clean"]:
            lbl_status.setObjectName("badge_clean")
        else:
            lbl_status.setObjectName("badge_dirty")
        layout.addWidget(lbl_status)

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


class ProjectsDashboardWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.scanner_thread = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Header
        h_head = QHBoxLayout()
        lbl_head = QLabel("PROJETOS RECENTES (~/develop)")
        lbl_head.setObjectName("sec_title")
        h_head.addWidget(lbl_head)
        h_head.addStretch()

        btn_refresh = QPushButton("🔄")
        btn_refresh.setObjectName("btn_icon")
        btn_refresh.setStyleSheet("padding: 2px 6px; font-size: 10px;")
        btn_refresh.setToolTip("Atualizar projetos")
        btn_refresh.clicked.connect(self.scan_projects)
        h_head.addWidget(btn_refresh)
        layout.addLayout(h_head)

        # Container for project items
        self.items_container = QVBoxLayout()
        self.items_container.setSpacing(4)
        layout.addLayout(self.items_container)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.scan_projects)
        self.timer.start(8000)
        self.scan_projects()

    def scan_projects(self):
        if self.scanner_thread and self.scanner_thread.isRunning():
            return
        self.scanner_thread = GitScannerThread(DEVELOP_DIR)
        self.scanner_thread.projects_scanned.connect(self._on_projects_scanned)
        self.scanner_thread.start()

    def _on_projects_scanned(self, projects: list):
        # Clear existing
        while self.items_container.count() > 0:
            item = self.items_container.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not projects:
            lbl_empty = QLabel("Nenhum repositório Git encontrado em ~/develop")
            lbl_empty.setStyleSheet("color: #94a3b8; font-size: 11px;")
            self.items_container.addWidget(lbl_empty)
            return

        for p in projects:
            w = ProjectItemWidget(p, self)
            self.items_container.addWidget(w)
