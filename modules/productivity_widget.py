"""
Productivity & Code Activity Monitor Widget
Scans ~/develop for recent commits, working-tree changes, and prioritized projects.
"""

import os
import json
import time
import subprocess
from typing import List, Dict
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QWidget
)
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, Qt

CONFIG_FILE = os.path.expanduser("~/.config/desktop-hud/pinned_repos.json")
DEVELOP_DIR = os.path.expanduser("~/develop")
DEFAULT_PINNED = ["mp3", "desktop-hud", "rotina", "laser-widget", "eidos-system-v1"]


def format_time_ago(seconds_ago: float) -> str:
    if seconds_ago < 60:
        return "agora mesmo"
    elif seconds_ago < 3600:
        return f"{int(seconds_ago // 60)}m atrás"
    elif seconds_ago < 86400:
        return f"{int(seconds_ago // 3600)}h atrás"
    elif seconds_ago < 86400 * 30:
        return f"{int(seconds_ago // 86400)}d atrás"
    else:
        return f"{int(seconds_ago // (86400 * 30))} meses atrás"


class GitScanThread(QThread):
    scan_completed = pyqtSignal(dict)

    def run(self):
        pinned = self._load_pinned()
        repos = []
        now = time.time()

        if not os.path.isdir(DEVELOP_DIR):
            self.scan_completed.emit({"recent": [], "pinned": [], "stats": {}})
            return

        for item in os.listdir(DEVELOP_DIR):
            p = os.path.join(DEVELOP_DIR, item)
            if os.path.isdir(os.path.join(p, ".git")):
                repos.append((item, p))

        all_repo_data = []
        total_recent_commits = 0
        total_dirty_files = 0

        for name, path in repos:
            try:
                # 1. Last commit date & subject
                res_log = subprocess.run(
                    ["git", "-C", path, "log", "-1", "--format=%ct|%s"],
                    capture_output=True, text=True, timeout=1.0
                )
                commit_ts = 0
                subject = ""
                if res_log.returncode == 0 and res_log.stdout.strip():
                    parts = res_log.stdout.strip().split("|", 1)
                    commit_ts = int(parts[0])
                    if len(parts) > 1:
                        subject = parts[1]

                # 2. Dirty working tree status
                res_stat = subprocess.run(
                    ["git", "-C", path, "status", "--porcelain"],
                    capture_output=True, text=True, timeout=1.0
                )
                dirty_count = 0
                if res_stat.returncode == 0 and res_stat.stdout.strip():
                    dirty_count = len(res_stat.stdout.strip().splitlines())
                    total_dirty_files += dirty_count

                # 3. Commits in last 48 hours
                res_commits = subprocess.run(
                    ["git", "-C", path, "rev-list", "--count", "--since=48 hours ago", "HEAD"],
                    capture_output=True, text=True, timeout=1.0
                )
                commits_48h = int(res_commits.stdout.strip()) if res_commits.returncode == 0 and res_commits.stdout.strip().isdigit() else 0
                total_recent_commits += commits_48h

                # 4. Check latest mtime in working directory
                last_mtime = commit_ts
                for root, dirs, files in os.walk(path):
                    if ".git" in dirs: dirs.remove(".git")
                    if "node_modules" in dirs: dirs.remove("node_modules")
                    if ".venv" in dirs: dirs.remove(".venv")
                    if "build" in dirs: dirs.remove("build")
                    if ".pio" in dirs: dirs.remove(".pio")
                    for f in files:
                        fp = os.path.join(root, f)
                        try:
                            mt = os.path.getmtime(fp)
                            if mt > last_mtime:
                                last_mtime = mt
                        except OSError:
                            pass
                    break  # top-level files + first level check for speed

                all_repo_data.append({
                    "name": name,
                    "path": path,
                    "commit_ts": commit_ts,
                    "last_mtime": last_mtime,
                    "subject": subject,
                    "dirty_count": dirty_count,
                    "commits_48h": commits_48h,
                    "is_pinned": name in pinned
                })
            except Exception:
                continue

        # Recent: Active within last 48h or with dirty files
        recent_repos = [
            r for r in all_repo_data
            if r["commits_48h"] > 0 or r["dirty_count"] > 0 or (now - r["last_mtime"]) < 86400 * 2
        ]
        recent_repos.sort(key=lambda x: max(x["last_mtime"], x["commit_ts"]), reverse=True)

        # Pinned repos
        pinned_repos = [r for r in all_repo_data if r["is_pinned"]]
        pinned_repos.sort(key=lambda x: x["commit_ts"], reverse=True)

        stats = {
            "total_commits": total_recent_commits,
            "total_dirty": total_dirty_files,
            "active_repos": len(recent_repos)
        }

        self.scan_completed.emit({
            "recent": recent_repos[:4],
            "pinned": pinned_repos[:4],
            "stats": stats
        })

    def _load_pinned(self) -> List[str]:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return DEFAULT_PINNED


class ProductivityWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.scan_thread = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Header
        h_head = QHBoxLayout()
        lbl_head = QLabel("⚡ PRODUTIVIDADE & DEV")
        lbl_head.setObjectName("sec_title")
        h_head.addWidget(lbl_head)
        h_head.addStretch()

        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setObjectName("btn_icon")
        self.btn_refresh.setFixedSize(22, 22)
        self.btn_refresh.clicked.connect(self.start_scan)
        h_head.addWidget(self.btn_refresh)
        layout.addLayout(h_head)

        # Metrics Pills
        self.h_metrics = QHBoxLayout()
        self.h_metrics.setSpacing(6)
        
        self.badge_commits = QLabel("🔥 0 commits (48h)")
        self.badge_commits.setStyleSheet("background-color: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.35); color: #fbbf24; border-radius: 6px; padding: 3px 6px; font-size: 10px; font-weight: 600;")
        self.h_metrics.addWidget(self.badge_commits)

        self.badge_dirty = QLabel("📝 0 pendentes")
        self.badge_dirty.setStyleSheet("background-color: rgba(14, 165, 233, 0.15); border: 1px solid rgba(14, 165, 233, 0.35); color: #38bdf8; border-radius: 6px; padding: 3px 6px; font-size: 10px; font-weight: 600;")
        self.h_metrics.addWidget(self.badge_dirty)

        self.badge_active = QLabel("🚀 0 ativos")
        self.badge_active.setStyleSheet("background-color: rgba(34, 197, 94, 0.15); border: 1px solid rgba(34, 197, 94, 0.35); color: #4ade80; border-radius: 6px; padding: 3px 6px; font-size: 10px; font-weight: 600;")
        self.h_metrics.addWidget(self.badge_active)
        layout.addLayout(self.h_metrics)

        # Recent Section Title
        self.lbl_sec_recent = QLabel("PROJETOS RECENTES (HOJE / ONTEM):")
        self.lbl_sec_recent.setStyleSheet("font-size: 10px; font-weight: 700; color: #94a3b8; margin-top: 2px;")
        layout.addWidget(self.lbl_sec_recent)

        self.recent_container = QVBoxLayout()
        self.recent_container.setSpacing(4)
        layout.addLayout(self.recent_container)

        # Pinned Section Title
        self.lbl_sec_pinned = QLabel("PRIORIDADES & ACOMPANHAMENTO:")
        self.lbl_sec_pinned.setStyleSheet("font-size: 10px; font-weight: 700; color: #94a3b8; margin-top: 4px;")
        layout.addWidget(self.lbl_sec_pinned)

        self.pinned_container = QVBoxLayout()
        self.pinned_container.setSpacing(4)
        layout.addLayout(self.pinned_container)

        # Scan Timer (every 30 seconds)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.start_scan)
        self.timer.start(30000)
        self.start_scan()

    def start_scan(self):
        if self.scan_thread and self.scan_thread.isRunning():
            return
        self.scan_thread = GitScanThread()
        self.scan_thread.scan_completed.connect(self._on_scan_completed)
        self.scan_thread.start()

    def _on_scan_completed(self, data: dict):
        now = time.time()
        stats = data.get("stats", {})
        self.badge_commits.setText(f"🔥 {stats.get('total_commits', 0)} commits (48h)")
        self.badge_dirty.setText(f"📝 {stats.get('total_dirty', 0)} pendentes")
        self.badge_active.setText(f"🚀 {stats.get('active_repos', 0)} ativos")

        # Update Recent
        self._clear_layout(self.recent_container)
        recent = data.get("recent", [])
        if not recent:
            lbl = QLabel("Nenhuma alteração recente nos repos.")
            lbl.setStyleSheet("color: #64748b; font-size: 11px; font-style: italic;")
            self.recent_container.addWidget(lbl)
        else:
            for r in recent:
                self.recent_container.addWidget(self._create_repo_row(r, now, is_recent=True))

        # Update Pinned
        self._clear_layout(self.pinned_container)
        pinned = data.get("pinned", [])
        for r in pinned:
            self.pinned_container.addWidget(self._create_repo_row(r, now, is_recent=False))

    def _create_repo_row(self, r: dict, now: float, is_recent: bool) -> QFrame:
        row = QFrame()
        row.setStyleSheet("background-color: rgba(20, 24, 32, 0.6); border: 1px solid rgba(255, 255, 255, 0.04); border-radius: 6px; padding: 4px 6px;")
        h = QHBoxLayout(row)
        h.setContentsMargins(4, 2, 4, 2)
        h.setSpacing(6)

        # Info
        v_info = QVBoxLayout()
        v_info.setSpacing(1)

        name_text = f"📦 {r['name']}"
        lbl_name = QLabel(name_text)
        lbl_name.setStyleSheet("font-size: 11px; font-weight: 700; color: #f1f5f9;")
        v_info.addWidget(lbl_name)

        # Details
        time_diff = now - r["commit_ts"] if r["commit_ts"] else 9999999
        time_str = format_time_ago(time_diff)

        details = []
        if r["dirty_count"] > 0:
            details.append(f"<span style='color: #38bdf8;'>📝 {r['dirty_count']} modif.</span>")
        if r["commits_48h"] > 0:
            details.append(f"<span style='color: #fbbf24;'>🔥 {r['commits_48h']} com.</span>")
        details.append(f"<span style='color: #64748b;'>{time_str}</span>")

        lbl_desc = QLabel(" · ".join(details))
        lbl_desc.setStyleSheet("font-size: 10px;")
        v_info.addWidget(lbl_desc)
        h.addLayout(v_info, 1)

        # Button VS Code
        btn_code = QPushButton("💻 Code")
        btn_code.setStyleSheet("background-color: rgba(14, 165, 233, 0.15); border: 1px solid rgba(14, 165, 233, 0.35); color: #38bdf8; font-size: 10px; font-weight: 600; padding: 3px 6px; border-radius: 4px;")
        btn_code.setToolTip(f"Abrir {r['name']} no VS Code")
        btn_code.clicked.connect(lambda _, p=r["path"]: self._open_in_code(p))
        h.addWidget(btn_code)

        return row

    def _open_in_code(self, path: str):
        subprocess.Popen(["code", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _clear_layout(self, layout):
        while layout.count() > 0:
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
