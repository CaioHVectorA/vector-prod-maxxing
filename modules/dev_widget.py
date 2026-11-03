"""
Dev & Antigravity Projects Management Suite
Features:
- Full administration of Antigravity IDE workspaces and projects
- Reads conversation_summaries.db, globalStorage/storage.json, and ~/develop
- Real-time git status (branch, uncommitted changes, last commit, lines added/deleted since 06:00 AM)
- Search filter for instant project lookup
- Pin/Star favorite projects to top
- 1-Click Launch in Antigravity IDE
- 1-Click Open Terminal in project directory
- Quick Push to origin/main with background thread
"""

import os
import re
import time
import json
import sqlite3
import subprocess
from datetime import datetime, timedelta
from typing import List, Dict

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QWidget, QMessageBox, QProgressBar, QLineEdit, QFileDialog
)
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, Qt

from modules.env_resolver import (
    discover_develop_dir, PINNED_FILE, LOCAL_CONFIG_DIR as CONFIG_DIR,
    get_antigravity_db_path, get_antigravity_storage_path,
    open_terminal_at, open_in_antigravity, IS_WINDOWS
)
from modules.nodes_widget import EnvironmentsMonitorWidget

DEVELOP_DIR = discover_develop_dir()
ANTIGRAVITY_DB = get_antigravity_db_path()
STORAGE_JSON = get_antigravity_storage_path()


def get_daily_cutoff():
    """Returns the start of the current work day starting at 06:00 AM"""
    now = datetime.now()
    if now.hour >= 6:
        start_day = now.replace(hour=6, minute=0, second=0, microsecond=0)
    else:
        start_day = (now - timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)
    return start_day


def format_time_ago(seconds_ago: float) -> str:
    if seconds_ago < 60:
        return "agora"
    elif seconds_ago < 3600:
        return f"{int(seconds_ago // 60)}m atrás"
    elif seconds_ago < 86400:
        return f"{int(seconds_ago // 3600)}h atrás"
    elif seconds_ago < 86400 * 30:
        return f"{int(seconds_ago // 86400)}d atrás"
    else:
        return f"{int(seconds_ago // (86400 * 30))}m atrás"


class PushWorkerThread(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, repo_path: str, repo_name: str):
        super().__init__()
        self.repo_path = repo_path
        self.repo_name = repo_name

    def run(self):
        try:
            res = subprocess.run(
                ["git", "-C", self.repo_path, "push", "origin", "main"],
                capture_output=True, text=True, timeout=25
            )
            if res.returncode == 0:
                self.finished.emit(True, f"Push em '{self.repo_name}' (main) concluído com sucesso!")
            else:
                self.finished.emit(False, res.stderr or res.stdout or "Falha ao enviar push.")
        except Exception as e:
            self.finished.emit(False, str(e))


class AntigravityScannerThread(QThread):
    completed = pyqtSignal(dict)

    def run(self):
        now = time.time()
        start_day = get_daily_cutoff()
        start_ts = start_day.timestamp()
        start_iso = start_day.strftime("%Y-%m-%d %H:%M:%S")

        # Load pinned projects
        pinned = set()
        if os.path.exists(PINNED_FILE):
            try:
                with open(PINNED_FILE, "r", encoding="utf-8") as f:
                    pinned = set(json.load(f))
            except Exception:
                pass

        projects = {}

        # 1. Inspect conversation_summaries.db
        if os.path.exists(ANTIGRAVITY_DB):
            try:
                conn = sqlite3.connect(ANTIGRAVITY_DB)
                c = conn.cursor()
                c.execute("""
                    SELECT workspace_uris, project_id, title, last_modified_time, step_count
                    FROM conversation_summaries 
                    ORDER BY last_modified_time DESC
                """)
                for uris_raw, pid, title, last_mod, steps in c.fetchall():
                    try:
                        uris = json.loads(uris_raw) if uris_raw else []
                    except Exception:
                        uris = [uris_raw] if uris_raw else []

                    for uri in uris:
                        if uri.startswith("file://"):
                            path = uri.replace("file://", "")
                            if os.path.exists(path) and path != "/home/usuario":
                                name = os.path.basename(path)
                                if name not in projects:
                                    projects[name] = {
                                        "name": name,
                                        "path": path,
                                        "last_activity": last_mod,
                                        "last_title": title,
                                        "convo_count": 1,
                                        "total_steps": steps,
                                        "source": "antigravity"
                                    }
                                else:
                                    projects[name]["convo_count"] += 1
                                    projects[name]["total_steps"] += steps
                conn.close()
            except Exception:
                pass

        # 2. Inspect storage.json
        if os.path.exists(STORAGE_JSON):
            try:
                with open(STORAGE_JSON, "r", encoding="utf-8") as f:
                    sdata = json.load(f)
                    workspaces = sdata.get("profileAssociations", {}).get("workspaces", {})
                    for w in workspaces:
                        if w.startswith("file://"):
                            path = w.replace("file://", "")
                            if os.path.exists(path) and path != "/home/usuario":
                                name = os.path.basename(path)
                                if name not in projects:
                                    projects[name] = {
                                        "name": name,
                                        "path": path,
                                        "last_activity": "",
                                        "last_title": "",
                                        "convo_count": 0,
                                        "total_steps": 0,
                                        "source": "storage"
                                    }
            except Exception:
                pass

        # 3. Add all repos from ~/develop
        if os.path.isdir(DEVELOP_DIR):
            for item in sorted(os.listdir(DEVELOP_DIR)):
                p = os.path.join(DEVELOP_DIR, item)
                if os.path.isdir(os.path.join(p, ".git")):
                    if item not in projects:
                        projects[item] = {
                            "name": item,
                            "path": p,
                            "last_activity": "",
                            "last_title": "",
                            "convo_count": 0,
                            "total_steps": 0,
                            "source": "develop"
                        }

        # 4. Gather git & activity stats for all projects
        total_today_add = 0
        total_today_del = 0
        total_week_add = 0
        total_week_del = 0

        project_list = []

        for name, pinfo in projects.items():
            path = pinfo["path"]
            is_pinned = (name in pinned) or (path in pinned)
            pinfo["is_pinned"] = is_pinned

            git_dir = os.path.join(path, ".git")
            pinfo["is_git"] = os.path.isdir(git_dir)
            pinfo["branch"] = "main"
            pinfo["dirty_files"] = 0
            pinfo["today_add"] = 0
            pinfo["today_del"] = 0
            pinfo["commit_ts"] = 0
            pinfo["max_mtime"] = 0
            pinfo["touched_today"] = False

            if pinfo["is_git"]:
                try:
                    # Current branch
                    res_b = subprocess.run(
                        ["git", "-C", path, "branch", "--show-current"],
                        capture_output=True, text=True, timeout=0.8
                    )
                    if res_b.returncode == 0 and res_b.stdout.strip():
                        pinfo["branch"] = res_b.stdout.strip()

                    # Commits today since 06:00
                    res_c_today = subprocess.run(
                        ["git", "-C", path, "log", f"--since={start_iso}", "--shortstat"],
                        capture_output=True, text=True, timeout=0.8
                    )
                    c_add = sum(int(x) for x in re.findall(r"(\d+) insertion", res_c_today.stdout)) if res_c_today.returncode == 0 else 0
                    c_del = sum(int(x) for x in re.findall(r"(\d+) deletion", res_c_today.stdout)) if res_c_today.returncode == 0 else 0

                    # Uncommitted status
                    res_stat = subprocess.run(
                        ["git", "-C", path, "status", "--porcelain"],
                        capture_output=True, text=True, timeout=0.8
                    )
                    dirty = len(res_stat.stdout.strip().splitlines()) if (res_stat.returncode == 0 and res_stat.stdout.strip()) else 0
                    pinfo["dirty_files"] = dirty

                    # Uncommitted diff
                    u_add, u_del = 0, 0
                    if dirty > 0:
                        res_diff = subprocess.run(
                            ["git", "-C", path, "diff", "--shortstat"],
                            capture_output=True, text=True, timeout=0.8
                        )
                        if res_diff.returncode == 0 and res_diff.stdout.strip():
                            u_add = sum(int(x) for x in re.findall(r"(\d+) insertion", res_diff.stdout))
                            u_del = sum(int(x) for x in re.findall(r"(\d+) deletion", res_diff.stdout))

                    pinfo["today_add"] = c_add + u_add
                    pinfo["today_del"] = c_del + u_del
                    total_today_add += pinfo["today_add"]
                    total_today_del += pinfo["today_del"]

                    # Last commit info
                    res_log = subprocess.run(
                        ["git", "-C", path, "log", "-1", "--format=%ct|%s"],
                        capture_output=True, text=True, timeout=0.8
                    )
                    if res_log.returncode == 0 and res_log.stdout.strip():
                        parts = res_log.stdout.strip().split("|", 1)
                        pinfo["commit_ts"] = int(parts[0])

                    # 7 days stats
                    res_7d = subprocess.run(
                        ["git", "-C", path, "log", "--since=7 days ago", "--shortstat"],
                        capture_output=True, text=True, timeout=0.8
                    )
                    if res_7d.returncode == 0 and res_7d.stdout.strip():
                        total_week_add += sum(int(x) for x in re.findall(r"(\d+) insertion", res_7d.stdout))
                        total_week_del += sum(int(x) for x in re.findall(r"(\d+) deletion", res_7d.stdout))

                except Exception:
                    pass

            # Check if touched today
            pinfo["touched_today"] = (pinfo["today_add"] > 0 or pinfo["today_del"] > 0 or (pinfo["commit_ts"] >= start_ts))

            project_list.append(pinfo)

        # Sort: Pinned first, then touched today, then convo_count desc, then name
        project_list.sort(key=lambda x: (
            x["is_pinned"],
            x["touched_today"],
            x.get("convo_count", 0),
            x.get("commit_ts", 0)
        ), reverse=True)

        stats = {
            "today_add": total_today_add,
            "today_del": total_today_del,
            "week_add": total_week_add,
            "week_del": total_week_del,
            "total_projects": len(project_list)
        }

        self.completed.emit({
            "projects": project_list,
            "stats": stats
        })


class DevProductivityWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.scanner_thread = None
        self.push_thread = None
        self.all_projects = []
        self.filter_text = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        # Header with Antigravity Badge & Action Buttons
        h_head = QHBoxLayout()
        lbl_head = QLabel("🪐 ANTIGRAVITY & PROJETOS DEV")
        lbl_head.setObjectName("sec_title")
        h_head.addWidget(lbl_head)
        h_head.addStretch()

        btn_add = QPushButton("+ Abrir Pasta")
        btn_add.setStyleSheet("background-color: rgba(14, 165, 233, 0.15); border: 1px solid rgba(14, 165, 233, 0.35); color: #38bdf8; font-size: 10px; font-weight: 600; padding: 3px 6px; border-radius: 4px;")
        btn_add.setToolTip("Selecionar pasta para abrir no Antigravity IDE")
        btn_add.clicked.connect(self._select_folder_to_open)
        h_head.addWidget(btn_add)

        btn_refresh = QPushButton("🔄")
        btn_refresh.setObjectName("btn_icon")
        btn_refresh.setFixedSize(22, 22)
        btn_refresh.setToolTip("Atualizar projetos e git status")
        btn_refresh.clicked.connect(self.refresh)
        h_head.addWidget(btn_refresh)
        layout.addLayout(h_head)

        # Metrics Card (Lines of Code Today since 06:00 + 7 Days)
        self.card_metrics = QFrame()
        self.card_metrics.setStyleSheet("background-color: rgba(20, 24, 32, 0.7); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 8px; padding: 6px;")
        v_card = QVBoxLayout(self.card_metrics)
        v_card.setContentsMargins(6, 6, 6, 6)
        v_card.setSpacing(4)

        lbl_loc_title = QLabel("LINHAS DE CÓDIGO (CICLO DIÁRIO A PARTIR DAS 06:00):")
        lbl_loc_title.setStyleSheet("font-size: 9px; font-weight: 700; color: #94a3b8;")
        v_card.addWidget(lbl_loc_title)

        h_lines = QHBoxLayout()
        self.lbl_today_lines = QLabel("Hoje: +0 / -0")
        self.lbl_today_lines.setStyleSheet("font-size: 11px; font-weight: 700; color: #38bdf8;")
        h_lines.addWidget(self.lbl_today_lines)

        self.lbl_week_lines = QLabel("Semana: +0 / -0")
        self.lbl_week_lines.setStyleSheet("font-size: 10px; color: #94a3b8;")
        h_lines.addWidget(self.lbl_week_lines)
        v_card.addLayout(h_lines)

        self.bar_ratio = QProgressBar()
        self.bar_ratio.setFixedHeight(5)
        self.bar_ratio.setTextVisible(False)
        self.bar_ratio.setStyleSheet("""
            QProgressBar { background-color: rgba(244, 63, 94, 0.4); border-radius: 2px; border: none; }
            QProgressBar::chunk { background-color: #22c55e; border-radius: 2px; }
        """)
        self.bar_ratio.setValue(50)
        v_card.addWidget(self.bar_ratio)
        layout.addWidget(self.card_metrics)

        # Multi-Environment & Remote AI Training Rigs Monitor
        self.envs_widget = EnvironmentsMonitorWidget(self)
        layout.addWidget(self.envs_widget)

        # Search Bar
        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("🔍 Filtrar projetos Antigravity (nome ou caminho)...")
        self.input_search.setStyleSheet("""
            QLineEdit {
                background-color: rgba(20, 24, 32, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                color: #f1f5f9;
                font-size: 11px;
                padding: 4px 8px;
            }
            QLineEdit:focus {
                border: 1px solid #0284c7;
            }
        """)
        self.input_search.textChanged.connect(self._on_search_changed)
        layout.addWidget(self.input_search)

        # Repos Section Header
        self.lbl_sec = QLabel("PROJETOS ANTIGRAVITY:")
        self.lbl_sec.setStyleSheet("font-size: 9px; font-weight: 700; color: #94a3b8; margin-top: 2px;")
        layout.addWidget(self.lbl_sec)

        # Scrollable Repos List
        self.scroll_repos = QScrollArea()
        self.scroll_repos.setWidgetResizable(True)
        self.scroll_repos.setStyleSheet("background: transparent; border: none;")
        self.scroll_repos.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.repos_container = QWidget()
        self.repos_container.setStyleSheet("background: transparent;")
        self.repos_layout = QVBoxLayout(self.repos_container)
        self.repos_layout.setContentsMargins(0, 0, 0, 0)
        self.repos_layout.setSpacing(4)
        self.scroll_repos.setWidget(self.repos_container)
        layout.addWidget(self.scroll_repos, 1)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("font-size: 10px; color: #38bdf8;")
        layout.addWidget(self.lbl_status)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(25000)
        self.refresh()

    def refresh(self):
        if hasattr(self, "envs_widget"):
            self.envs_widget.refresh_nodes()
        if self.scanner_thread and self.scanner_thread.isRunning():
            return
        self.scanner_thread = AntigravityScannerThread()
        self.scanner_thread.completed.connect(self._on_scanner_completed)
        self.scanner_thread.start()

    def refresh_all(self):
        self.refresh()

    def _on_search_changed(self, text: str):
        self.filter_text = text.lower().strip()
        self._render_projects_list()

    def _on_scanner_completed(self, data: dict):
        stats = data.get("stats", {})
        t_add = stats.get("today_add", 0)
        t_del = stats.get("today_del", 0)
        w_add = stats.get("week_add", 0)
        w_del = stats.get("week_del", 0)
        total_p = stats.get("total_projects", 0)

        self.lbl_sec.setText(f"PROJETOS ANTIGRAVITY ({total_p}):")

        if t_add == 0 and t_del == 0:
            self.lbl_today_lines.setText("Hoje (desde 06h): <span style='color: #94a3b8;'>0 alterações</span>")
        else:
            self.lbl_today_lines.setText(
                f"Hoje: <span style='color: #4ade80;'>+{t_add}</span> / <span style='color: #f87171;'>-{t_del}</span>"
            )

        self.lbl_week_lines.setText(
            f"7 dias: <span style='color: #4ade80;'>+{w_add}</span> / <span style='color: #f87171;'>-{w_del}</span>"
        )

        total_t = t_add + t_del
        if total_t > 0:
            self.bar_ratio.setValue(int((t_add / total_t) * 100))
        else:
            self.bar_ratio.setValue(50)

        self.all_projects = data.get("projects", [])
        self._render_projects_list()

    def _render_projects_list(self):
        self._clear_layout(self.repos_layout)
        now = time.time()

        filtered = []
        for p in self.all_projects:
            if not self.filter_text:
                filtered.append(p)
            elif self.filter_text in p["name"].lower() or self.filter_text in p["path"].lower() or self.filter_text in p.get("last_title", "").lower():
                filtered.append(p)

        if not filtered:
            lbl_empty = QLabel("Nenhum projeto encontrado com este filtro.")
            lbl_empty.setStyleSheet("color: #64748b; font-size: 11px; font-style: italic; padding: 8px;")
            self.repos_layout.addWidget(lbl_empty)
            return

        for p in filtered:
            self.repos_layout.addWidget(self._create_project_card(p, now))

    def _create_project_card(self, p: dict, now: float) -> QFrame:
        card = QFrame()
        card.setStyleSheet("background-color: rgba(20, 24, 32, 0.7); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 6px; padding: 4px 6px;")
        v_card = QVBoxLayout(card)
        v_card.setContentsMargins(4, 3, 4, 3)
        v_card.setSpacing(3)

        # Top row: Pin + Name + Branch + Conversations badge
        h_top = QHBoxLayout()
        h_top.setSpacing(4)

        btn_star = QPushButton("⭐" if p["is_pinned"] else "☆")
        btn_star.setFixedSize(18, 18)
        btn_star.setStyleSheet("background: transparent; border: none; font-size: 11px; padding: 0;")
        btn_star.setToolTip("Desafixar do topo" if p["is_pinned"] else "Fixar projeto no topo")
        btn_star.clicked.connect(lambda _, name=p["name"]: self._toggle_pin_project(name))
        h_top.addWidget(btn_star)

        lbl_name = QLabel(f"🪐 <b>{p['name']}</b>")
        lbl_name.setStyleSheet("font-size: 11px; color: #f1f5f9;")
        h_top.addWidget(lbl_name)

        if p.get("branch"):
            lbl_branch = QLabel(f"🌱 {p['branch']}")
            lbl_branch.setStyleSheet("font-size: 9px; color: #a5b4fc; background-color: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 3px; padding: 1px 4px;")
            h_top.addWidget(lbl_branch)

        if p.get("convo_count", 0) > 0:
            lbl_convos = QLabel(f"💬 {p['convo_count']}")
            lbl_convos.setStyleSheet("font-size: 9px; color: #38bdf8; background-color: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 3px; padding: 1px 4px;")
            lbl_convos.setToolTip(f"{p['convo_count']} sessões Antigravity registradas")
            h_top.addWidget(lbl_convos)

        h_top.addStretch()

        # Small Push to Main Button
        if p["is_git"]:
            btn_push = QPushButton("🚀 Push")
            btn_push.setStyleSheet("background-color: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.35); color: #fbbf24; font-size: 9px; font-weight: 700; padding: 2px 5px; border-radius: 4px;")
            btn_push.setToolTip(f"Subir alterações de '{p['name']}' para origin/main")
            btn_push.clicked.connect(lambda _, path=p["path"], name=p["name"]: self._push_main(path, name))
            h_top.addWidget(btn_push)

        # Terminal Button
        btn_term = QPushButton("💻")
        btn_term.setFixedSize(22, 20)
        btn_term.setStyleSheet("background-color: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255, 255, 255, 0.1); color: #cbd5e1; font-size: 10px; border-radius: 4px;")
        btn_term.setToolTip(f"Abrir terminal em {p['path']}")
        btn_term.clicked.connect(lambda _, path=p["path"]: self._open_terminal(path))
        h_top.addWidget(btn_term)

        # Antigravity IDE Button
        btn_ide = QPushButton("⚡ IDE")
        btn_ide.setStyleSheet("background-color: rgba(14, 165, 233, 0.25); border: 1px solid rgba(14, 165, 233, 0.5); color: #38bdf8; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px;")
        btn_ide.setToolTip(f"Abrir {p['name']} no Antigravity IDE")
        btn_ide.clicked.connect(lambda _, path=p["path"]: self._open_antigravity(path))
        h_top.addWidget(btn_ide)

        v_card.addLayout(h_top)

        # Subtitle Row: Path + Activity + Dirty status
        diff_str = ""
        if p["today_add"] > 0 or p["today_del"] > 0:
            diff_str = f"<span style='color: #38bdf8;'>Hoje:</span> <span style='color: #4ade80;'>+{p['today_add']}</span>/<span style='color: #f87171;'>-{p['today_del']}</span>"
        elif p["dirty_files"] > 0:
            diff_str = f"<span style='color: #fbbf24;'>📝 {p['dirty_files']} arq pendentes</span>"
        else:
            diff_str = "<span style='color: #4ade80;'>✓ limpo</span>"

        time_str = ""
        if p.get("commit_ts", 0) > 0:
            time_str = format_time_ago(now - p["commit_ts"])
        elif p.get("last_activity"):
            time_str = "recente"

        last_info = p.get("last_title", "")
        if last_info:
            last_info = f" · <i>{last_info[:32]}...</i>" if len(last_info) > 32 else f" · <i>{last_info}</i>"

        lbl_desc = QLabel(f"{diff_str} · <span style='color: #64748b;'>{time_str}</span>{last_info}")
        lbl_desc.setStyleSheet("font-size: 9px; color: #94a3b8;")
        v_card.addWidget(lbl_desc)

        return card

    def _toggle_pin_project(self, project_name: str):
        pinned = []
        if os.path.exists(PINNED_FILE):
            try:
                with open(PINNED_FILE, "r", encoding="utf-8") as f:
                    pinned = json.load(f)
            except Exception:
                pinned = []

        if project_name in pinned:
            pinned.remove(project_name)
        else:
            pinned.insert(0, project_name)

        os.makedirs( os.path.dirname(PINNED_FILE), exist_ok=True)
        try:
            with open(PINNED_FILE, "w", encoding="utf-8") as f:
                json.dump(pinned, f, indent=2)
        except Exception:
            pass

        self.refresh()

    def _select_folder_to_open(self):
        folder = QFileDialog.getExistingDirectory(self, "Selecionar Projeto para Antigravity IDE", DEVELOP_DIR)
        if folder:
            self._open_antigravity(folder)

    def _open_terminal(self, path: str):
        open_terminal_at(path)

    def _push_main(self, repo_path: str, repo_name: str):
        if self.push_thread and self.push_thread.isRunning():
            return
        self.lbl_status.setText(f"⏳ Subindo '{repo_name}' para main...")
        self.push_thread = PushWorkerThread(repo_path, repo_name)
        self.push_thread.finished.connect(self._on_push_finished)
        self.push_thread.start()

    def _on_push_finished(self, success: bool, msg: str):
        self.lbl_status.setText("")
        if success:
            QMessageBox.information(self, "Git Push Concluído", msg)
            self.refresh()
        else:
            QMessageBox.warning(self, "Falha no Git Push", msg)

    def _open_antigravity(self, path: str):
        if not open_in_antigravity(path):
            QMessageBox.warning(self, "IDE não encontrada", "Não foi possível localizar o executável do Antigravity IDE nesta máquina.")

    def _clear_layout(self, layout):
        while layout.count() > 0:
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
