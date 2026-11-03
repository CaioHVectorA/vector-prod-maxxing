"""
AI & Reinforcement Learning Workspace Widget
Monitors active RL trainings, model checkpoints (.pt, .zip), TensorBoard, and AI projects in ~/develop.
"""

import os
import glob
import subprocess
import time
from typing import List, Dict

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGridLayout
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal

DEVELOP_DIR = os.path.expanduser("~/develop")
IDE_BIN = "/home/usuario/.local/bin/antigravity-ide"

AI_PROJECTS = [
    {
        "id": "haxball-rl",
        "name": "haxball-rl",
        "desc": "PPO Autonomous Agents com física bit-exact em Rust",
        "icon": "⚽",
        "entry": "scripts/train_selfplay.py",
        "dashboard_port": 8000
    },
    {
        "id": "ball-balancer-rl",
        "name": "ball-balancer-rl",
        "desc": "2-DOF Ball-on-Plate RL (PPO vs PD) + GUI Pygame",
        "icon": "⚖️",
        "entry": "train.py"
    },
    {
        "id": "snake-rl",
        "name": "snake-rl",
        "desc": "Deep Q-Learning & PPO clássico no Snake Game",
        "icon": "🐍",
        "entry": "agent.py"
    },
    {
        "id": "Amnesia-AI",
        "name": "Amnesia-AI",
        "desc": "Machine Learning em Pokémon Trivia e Competitivo",
        "icon": "🧠",
        "entry": "main.py"
    },
    {
        "id": "rl-robot",
        "name": "rl-robot",
        "desc": "Robótica autônoma e locomoção com Reinforcement Learning",
        "icon": "🤖",
        "entry": "train.py"
    },
    {
        "id": "vss-ironcup-rl",
        "name": "vss-ironcup-rl",
        "desc": "Simulador IEEE VSSS Futebol de Robôs + Univector Field",
        "icon": "🏆",
        "entry": "train.py"
    }
]


class AIScannerThread(QThread):
    finished_scan = pyqtSignal(dict)

    def run(self):
        # 1. Detect active training processes
        active_trainings = []
        try:
            res = subprocess.run(["ps", "-eo", "pid,%cpu,%mem,cmd"], capture_output=True, text=True, timeout=1.5)
            if res.returncode == 0:
                for line in res.stdout.splitlines()[1:]:
                    parts = line.strip().split(None, 3)
                    if len(parts) >= 4:
                        pid, cpu, mem, cmd = parts[0], parts[1], parts[2], parts[3]
                        cmd_low = cmd.lower()
                        if "python" in cmd_low and ("train" in cmd_low or "agent.py" in cmd_low or "stable_baselines" in cmd_low or "torch" in cmd_low or "haxball" in cmd_low):
                            if "desktop-hud" not in cmd_low:
                                active_trainings.append({
                                    "pid": pid,
                                    "cpu": cpu,
                                    "mem": mem,
                                    "cmd": os.path.basename(cmd.split()[1]) if len(cmd.split()) > 1 else cmd[:30]
                                })
        except Exception:
            pass

        # 2. Checkpoints count & latest files
        total_ckpts = 0
        latest_ckpts = []
        for p in AI_PROJECTS:
            p_dir = os.path.join(DEVELOP_DIR, p["id"])
            if os.path.exists(p_dir):
                models_dir = os.path.join(p_dir, "models")
                runs_dir = os.path.join(p_dir, "runs")
                
                # Fast check in models/, runs/, and root dir only
                search_dirs = [p_dir, os.path.join(p_dir, "models"), os.path.join(p_dir, "runs"), os.path.join(p_dir, "experiments")]
                for sdir in search_dirs:
                    if os.path.isdir(sdir):
                        for ext in ["*.pt", "*.pth", "*.zip"]:
                            files = glob.glob(os.path.join(sdir, ext))
                            total_ckpts += len(files)
                            for f in files:
                                try:
                                    mtime = os.path.getmtime(f)
                                    sz_mb = os.path.getsize(f) / (1024 * 1024)
                                    latest_ckpts.append({
                                        "name": os.path.basename(f),
                                        "project": p["id"],
                                        "size_mb": round(sz_mb, 2),
                                        "mtime": mtime
                                    })
                                except Exception:
                                    pass

        latest_ckpts.sort(key=lambda x: x["mtime"], reverse=True)

        # 3. Check git branch & uncommitted status for projects
        proj_statuses = {}
        for p in AI_PROJECTS:
            p_dir = os.path.join(DEVELOP_DIR, p["id"])
            if os.path.exists(p_dir):
                try:
                    res_b = subprocess.run(["git", "-C", p_dir, "branch", "--show-current"], capture_output=True, text=True, timeout=1.0)
                    branch = res_b.stdout.strip() or "main"
                    res_s = subprocess.run(["git", "-C", p_dir, "status", "--porcelain"], capture_output=True, text=True, timeout=1.0)
                    uncommitted = len(res_s.stdout.strip().splitlines()) if res_s.stdout.strip() else 0
                    proj_statuses[p["id"]] = {"branch": branch, "uncommitted": uncommitted, "exists": True}
                except Exception:
                    proj_statuses[p["id"]] = {"branch": "main", "uncommitted": 0, "exists": True}
            else:
                proj_statuses[p["id"]] = {"exists": False}

        self.finished_scan.emit({
            "active_trainings": active_trainings,
            "total_ckpts": total_ckpts,
            "latest_ckpts": latest_ckpts[:4],
            "proj_statuses": proj_statuses
        })


class AIProductivityWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

        self.scan_timer = QTimer(self)
        self.scan_timer.timeout.connect(self.refresh)
        self.scan_timer.start(8000)

        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Header Card: Training Status & Quick Summary
        self.card_status = QFrame()
        self.card_status.setObjectName("card")
        l_status = QVBoxLayout(self.card_status)
        l_status.setContentsMargins(8, 6, 8, 6)
        l_status.setSpacing(4)

        h_title = QHBoxLayout()
        lbl_head = QLabel("🤖 TREINAMENTO & MODELOS (RL)")
        lbl_head.setObjectName("sec_title")
        h_title.addWidget(lbl_head)
        h_title.addStretch()

        self.lbl_train_badge = QLabel("⚪ Standby")
        self.lbl_train_badge.setStyleSheet("font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 6px; background: rgba(255,255,255,0.06); color: #94a3b8;")
        h_title.addWidget(self.lbl_train_badge)
        l_status.addLayout(h_title)

        # Metrics row
        h_metrics = QHBoxLayout()
        self.lbl_active_info = QLabel("Nenhum processo de treino ativo no momento.")
        self.lbl_active_info.setStyleSheet("font-size: 11px; color: #cbd5e1;")
        h_metrics.addWidget(self.lbl_active_info)
        h_metrics.addStretch()

        self.lbl_ckpts_count = QLabel("Checkpoints: ...")
        self.lbl_ckpts_count.setStyleSheet("font-size: 11px; font-weight: 700; color: #38bdf8;")
        h_metrics.addWidget(self.lbl_ckpts_count)
        l_status.addLayout(h_metrics)

        # Action Buttons
        h_actions = QHBoxLayout()
        h_actions.setSpacing(4)

        btn_tb = QPushButton("📊 TensorBoard")
        btn_tb.setStyleSheet("font-size: 10px; padding: 3px 6px; font-weight: 600; background-color: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3);")
        btn_tb.setToolTip("Abrir visualizador de métricas TensorBoard (localhost:6006)")
        btn_tb.clicked.connect(self._open_tensorboard)
        h_actions.addWidget(btn_tb)

        btn_dev = QPushButton("📂 ~/develop")
        btn_dev.setStyleSheet("font-size: 10px; padding: 3px 6px;")
        btn_dev.clicked.connect(lambda: subprocess.Popen(["xdg-open", DEVELOP_DIR]))
        h_actions.addWidget(btn_dev)

        btn_refresh = QPushButton("🔄")
        btn_refresh.setFixedSize(24, 24)
        btn_refresh.setToolTip("Atualizar status de treino e checkpoints")
        btn_refresh.clicked.connect(self.refresh)
        h_actions.addWidget(btn_refresh)

        h_actions.addStretch()
        l_status.addLayout(h_actions)

        layout.addWidget(self.card_status)

        # Scrollable Projects List
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")

        self.proj_container = QWidget()
        self.l_projs = QVBoxLayout(self.proj_container)
        self.l_projs.setContentsMargins(0, 0, 0, 0)
        self.l_projs.setSpacing(6)

        scroll.setWidget(self.proj_container)
        layout.addWidget(scroll, 1)

    def refresh(self):
        self.scanner = AIScannerThread()
        self.scanner.finished_scan.connect(self._on_scan_finished)
        self.scanner.start()

    def _on_scan_finished(self, data: dict):
        active_trainings = data.get("active_trainings", [])
        total_ckpts = data.get("total_ckpts", 0)
        proj_statuses = data.get("proj_statuses", {})

        # Update Top Status Card
        if active_trainings:
            first = active_trainings[0]
            self.lbl_train_badge.setText(f"🟢 Treino Ativo ({len(active_trainings)})")
            self.lbl_train_badge.setStyleSheet("font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 6px; background: rgba(34, 197, 94, 0.2); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.4);")
            self.lbl_active_info.setText(f"PID {first['pid']} · CPU: {first['cpu']}% · {first['cmd']}")
        else:
            self.lbl_train_badge.setText("⚪ Standby")
            self.lbl_train_badge.setStyleSheet("font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 6px; background: rgba(255,255,255,0.06); color: #94a3b8;")
            self.lbl_active_info.setText("Nenhum processo de treino rodando.")

        self.lbl_ckpts_count.setText(f"💾 {total_ckpts} checkpoints salvos")

        # Render Project Cards
        # Clear existing
        while self.l_projs.count():
            item = self.l_projs.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for p in AI_PROJECTS:
            st = proj_statuses.get(p["id"], {})
            card = self._create_project_card(p, st)
            self.l_projs.addWidget(card)

        self.l_projs.addStretch()

    def _create_project_card(self, p: dict, st: dict) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # Header of card: Icon, Name, Branch, Uncommitted
        h_top = QHBoxLayout()
        h_top.setSpacing(6)

        lbl_icon = QLabel(p["icon"])
        lbl_icon.setStyleSheet("font-size: 14px;")
        h_top.addWidget(lbl_icon)

        lbl_name = QLabel(p["name"])
        lbl_name.setStyleSheet("font-size: 12px; font-weight: 700; color: #ffffff;")
        h_top.addWidget(lbl_name)

        if st.get("exists", True):
            branch = st.get("branch", "main")
            lbl_branch = QLabel(f" {branch}")
            lbl_branch.setStyleSheet("font-size: 10px; color: #38bdf8; background: rgba(56, 189, 248, 0.1); padding: 1px 5px; border-radius: 4px;")
            h_top.addWidget(lbl_branch)

            uncommitted = st.get("uncommitted", 0)
            if uncommitted > 0:
                lbl_mod = QLabel(f"● {uncommitted} pendentes")
                lbl_mod.setStyleSheet("font-size: 10px; color: #fbbf24;")
                h_top.addWidget(lbl_mod)

        h_top.addStretch()

        # Button to open in Antigravity IDE
        btn_ide = QPushButton("⚡ IDE")
        btn_ide.setStyleSheet("font-size: 10px; font-weight: 700; padding: 2px 7px; background-color: #0284c7; color: white;")
        btn_ide.setToolTip(f"Abrir {p['name']} na Antigravity IDE")
        btn_ide.clicked.connect(lambda _, path=os.path.join(DEVELOP_DIR, p["id"]): self._open_ide(path))
        h_top.addWidget(btn_ide)

        layout.addLayout(h_top)

        # Description
        lbl_desc = QLabel(p["desc"])
        lbl_desc.setStyleSheet("font-size: 10px; color: #94a3b8;")
        lbl_desc.setWordWrap(True)
        layout.addWidget(lbl_desc)

        # Action links row
        h_sub = QHBoxLayout()
        h_sub.setSpacing(6)

        btn_folder = QPushButton("📂 Abrir Pasta")
        btn_folder.setStyleSheet("font-size: 9px; padding: 2px 5px; background: transparent; color: #94a3b8; border: 1px solid rgba(255,255,255,0.08);")
        btn_folder.clicked.connect(lambda _, path=os.path.join(DEVELOP_DIR, p["id"]): subprocess.Popen(["xdg-open", path]))
        h_sub.addWidget(btn_folder)

        if p["id"] == "haxball-rl":
            dash_path = os.path.join(DEVELOP_DIR, "haxball-rl", "dashboard.html")
            if os.path.exists(dash_path):
                btn_dash = QPushButton("🌐 Live Dashboard")
                btn_dash.setStyleSheet("font-size: 9px; padding: 2px 5px; background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3);")
                btn_dash.clicked.connect(lambda: subprocess.Popen(["xdg-open", dash_path]))
                h_sub.addWidget(btn_dash)

        h_sub.addStretch()
        layout.addLayout(h_sub)

        return card

    def _open_ide(self, path: str):
        if os.path.exists(path):
            subprocess.Popen([IDE_BIN, path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _open_tensorboard(self):
        # Check if tensorboard is already running on port 6006
        subprocess.Popen(["xdg-open", "http://localhost:6006"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
