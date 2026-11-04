"""
Dev & Antigravity Projects Management Suite (modules/dev_widget.py)
Usa exclusivamente ``core.*`` (zero chamadas diretas a subprocess).
"""

import time

from PyQt6.QtCore import QThread, QTimer, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core import gitutil, launchers, projects
from core.timeutil import time_ago
from core.workspace import discover_develop_dir
from modules.nodes_widget import EnvironmentsMonitorWidget


class PushWorkerThread(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, repo_path: str, repo_name: str, branch: str = ""):
        super().__init__()
        self.repo_path = repo_path
        self.repo_name = repo_name
        self.branch = branch

    def run(self):
        branch = self.branch or gitutil.current_branch(self.repo_path) or "main"
        res = gitutil.git(self.repo_path, "push", "origin", branch, timeout=30.0)
        if res.ok:
            self.finished.emit(True, f"Push em '{self.repo_name}' ({branch}) concluído com sucesso!")
        else:
            self.finished.emit(False, res.error or res.output or "Falha ao enviar push.")


class AntigravityScannerThread(QThread):
    completed = pyqtSignal(dict)

    def run(self):
        self.completed.emit(projects.scan_projects())


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
        btn_add.setStyleSheet(
            "background-color: rgba(14, 165, 233, 0.15); border: 1px solid rgba(14, 165, 233, 0.35); "
            "color: #38bdf8; font-size: 10px; font-weight: 600; padding: 3px 6px; border-radius: 4px;"
        )
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
        self.card_metrics.setStyleSheet(
            "background-color: rgba(20, 24, 32, 0.7); border: 1px solid rgba(255, 255, 255, 0.05); "
            "border-radius: 8px; padding: 6px;"
        )
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
        self.bar_ratio.setStyleSheet(
            "QProgressBar { background-color: rgba(244, 63, 94, 0.4); border-radius: 2px; border: none; }"
            "QProgressBar::chunk { background-color: #22c55e; border-radius: 2px; }"
        )
        self.bar_ratio.setValue(50)
        v_card.addWidget(self.bar_ratio)
        layout.addWidget(self.card_metrics)

        # Multi-Environment & Remote AI Training Rigs Monitor
        self.envs_widget = EnvironmentsMonitorWidget(self)
        layout.addWidget(self.envs_widget)

        # Search Bar
        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("🔍 Filtrar projetos Antigravity (nome ou caminho)...")
        self.input_search.setStyleSheet(
            "QLineEdit {"
            "    background-color: rgba(20, 24, 32, 0.8);"
            "    border: 1px solid rgba(255, 255, 255, 0.08);"
            "    border-radius: 6px;"
            "    color: #f1f5f9;"
            "    font-size: 11px;"
            "    padding: 4px 8px;"
            "}"
            "QLineEdit:focus { border: 1px solid #0284c7; }"
        )
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
        self.timer.start(30000)
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
            elif (
                self.filter_text in p["name"].lower()
                or self.filter_text in p["path"].lower()
                or self.filter_text in p.get("last_title", "").lower()
            ):
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
        card.setStyleSheet(
            "background-color: rgba(20, 24, 32, 0.7); border: 1px solid rgba(255, 255, 255, 0.05); "
            "border-radius: 6px; padding: 4px 6px;"
        )
        v_card = QVBoxLayout(card)
        v_card.setContentsMargins(4, 3, 4, 3)
        v_card.setSpacing(3)

        h_top = QHBoxLayout()
        h_top.setSpacing(4)

        btn_star = QPushButton("⭐" if p.get("is_pinned") else "☆")
        btn_star.setFixedSize(18, 18)
        btn_star.setStyleSheet("background: transparent; border: none; font-size: 11px; padding: 0;")
        btn_star.setToolTip("Desafixar do topo" if p.get("is_pinned") else "Fixar projeto no topo")
        btn_star.clicked.connect(lambda _, name=p["name"]: self._toggle_pin_project(name))
        h_top.addWidget(btn_star)

        lbl_name = QLabel(f"🪐 <b>{p['name']}</b>")
        lbl_name.setStyleSheet("font-size: 11px; color: #f1f5f9;")
        h_top.addWidget(lbl_name)

        if p.get("branch"):
            lbl_branch = QLabel(f"🌱 {p['branch']}")
            lbl_branch.setStyleSheet(
                "font-size: 9px; color: #a5b4fc; background-color: rgba(99, 102, 241, 0.15); "
                "border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 3px; padding: 1px 4px;"
            )
            h_top.addWidget(lbl_branch)

        if p.get("convo_count", 0) > 0:
            lbl_convos = QLabel(f"💬 {p['convo_count']}")
            lbl_convos.setStyleSheet(
                "font-size: 9px; color: #38bdf8; background-color: rgba(56, 189, 248, 0.15); "
                "border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 3px; padding: 1px 4px;"
            )
            lbl_convos.setToolTip(f"{p['convo_count']} sessões Antigravity registradas")
            h_top.addWidget(lbl_convos)

        h_top.addStretch()

        if p.get("is_git"):
            btn_push = QPushButton("🚀 Push")
            btn_push.setStyleSheet(
                "background-color: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.35); "
                "color: #fbbf24; font-size: 9px; font-weight: 700; padding: 2px 5px; border-radius: 4px;"
            )
            branch = p.get("branch") or "main"
            btn_push.setToolTip(f"Subir alterações de '{p['name']}' para origin/{branch}")
            btn_push.clicked.connect(
                lambda _, path=p["path"], name=p["name"], br=branch: self._push_repo(path, name, br)
            )
            h_top.addWidget(btn_push)

        btn_term = QPushButton("💻")
        btn_term.setFixedSize(22, 20)
        btn_term.setStyleSheet(
            "background-color: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255, 255, 255, 0.1); "
            "color: #cbd5e1; font-size: 10px; border-radius: 4px;"
        )
        btn_term.setToolTip(f"Abrir terminal em {p['path']}")
        btn_term.clicked.connect(lambda _, path=p["path"]: launchers.open_terminal(path))
        h_top.addWidget(btn_term)

        btn_ide = QPushButton("⚡ IDE")
        btn_ide.setStyleSheet(
            "background-color: rgba(14, 165, 233, 0.25); border: 1px solid rgba(14, 165, 233, 0.5); "
            "color: #38bdf8; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px;"
        )
        btn_ide.setToolTip(f"Abrir {p['name']} no Antigravity IDE")
        btn_ide.clicked.connect(lambda _, path=p["path"]: self._open_antigravity(path))
        h_top.addWidget(btn_ide)

        v_card.addLayout(h_top)

        today_add = p.get("today_add", 0)
        today_del = p.get("today_del", 0)
        dirty = p.get("dirty_files", p.get("dirty", 0))
        if today_add > 0 or today_del > 0:
            diff_str = (
                f"<span style='color: #38bdf8;'>Hoje:</span> "
                f"<span style='color: #4ade80;'>+{today_add}</span>/"
                f"<span style='color: #f87171;'>-{today_del}</span>"
            )
        elif dirty > 0:
            diff_str = f"<span style='color: #fbbf24;'>📝 {dirty} arq pendentes</span>"
        else:
            diff_str = "<span style='color: #4ade80;'>✓ limpo</span>"

        commit_ts = p.get("commit_ts", p.get("last_commit_ts", 0))
        time_str = time_ago(now - commit_ts) if commit_ts > 0 else ("recente" if p.get("last_activity") else "")

        last_info = p.get("last_title", "")
        if last_info:
            last_info = f" · <i>{last_info[:32]}...</i>" if len(last_info) > 32 else f" · <i>{last_info}</i>"

        lbl_desc = QLabel(f"{diff_str} · <span style='color: #64748b;'>{time_str}</span>{last_info}")
        lbl_desc.setStyleSheet("font-size: 9px; color: #94a3b8;")
        v_card.addWidget(lbl_desc)

        return card

    def _toggle_pin_project(self, project_name: str):
        projects.toggle_pinned(project_name)
        self.refresh()

    def _select_folder_to_open(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Selecionar Projeto para Antigravity IDE", discover_develop_dir()
        )
        if folder:
            self._open_antigravity(folder)

    def _push_repo(self, repo_path: str, repo_name: str, branch: str):
        if self.push_thread and self.push_thread.isRunning():
            return
        self.lbl_status.setText(f"⏳ Subindo '{repo_name}' para {branch}...")
        self.push_thread = PushWorkerThread(repo_path, repo_name, branch)
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
        if not launchers.open_in_ide(path):
            QMessageBox.warning(
                self,
                "IDE não encontrada",
                "Não foi possível localizar o executável do Antigravity IDE ou VS Code nesta máquina.",
            )

    def _clear_layout(self, layout):
        while layout.count() > 0:
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
