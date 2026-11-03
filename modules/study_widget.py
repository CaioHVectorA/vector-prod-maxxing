"""
UFF College & Study Organization Module
Features:
- Real UFF Grades & Weighted Average Formulas:
  - Cálculo III: (2*P1 + 3*P2)/5 >= 6.0 (P1=7.7 -> Meta P2=4.9)
  - Física II: P1=6.7, P2=8.7, P3 & Tests (Simulador Pfisicas integration)
  - Secondary: Métodos Numéricos, Sistemas de Computação, Física Experimental II
- Daily Study Quest: 5 Questions Goal & Daily Streak
- On-Hand Interactive Question Trainer (Calculo III & Fisica II)
- Study Log & Accumulated Subject Warnings (days since last study)
- Focus Mode with GNOME Notification muting & Distraction Minimizer
- 1-Click Launch of Pfisicas Simulator on localhost:8080
"""

import os
import json
import subprocess
from datetime import datetime
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QScrollArea, QWidget, QMessageBox, QProgressBar
)
from PyQt6.QtCore import QTimer, Qt
from modules.focus_manager import (
    activate_focus_mode, deactivate_focus_mode, block_active_distractions, record_study_session
)

DATA_PATH = os.path.expanduser("~/.config/desktop-hud/data.json")
QUESTOES_DIR = os.path.expanduser("~/.config/desktop-hud/questoes")
PFISICAS_DIR = os.path.expanduser("~/develop/Pfisicas")


def format_days_ago(date_str: str) -> str:
    if not date_str:
        return "nunca registrado"
    try:
        dt = datetime.fromisoformat(date_str)
        diff = (datetime.now() - dt).total_seconds() / 86400
        if diff < 1.0:
            return "hoje"
        elif diff < 2.0:
            return "ontem"
        else:
            return f"{int(diff)} dias atrás"
    except Exception:
        return "data inválida"


class StudyWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.is_focusing = False
        self.seconds_left = 25 * 60
        self.current_questions = []
        self.current_q_index = 0
        self.show_solution = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(8)

        # 1. Focus Mode & Distraction Blocker Card
        card_focus = QFrame()
        card_focus.setStyleSheet("background-color: rgba(20, 24, 32, 0.7); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 8px; padding: 6px;")
        f_layout = QVBoxLayout(card_focus)
        f_layout.setContentsMargins(6, 6, 6, 6)
        f_layout.setSpacing(4)

        h_fhead = QHBoxLayout()
        lbl_fhead = QLabel("⏱️ MODO FOCO & ANTI-DISTRAÇÃO")
        lbl_fhead.setStyleSheet("font-size: 9px; font-weight: 700; color: #94a3b8;")
        h_fhead.addWidget(lbl_fhead)
        h_fhead.addStretch()

        self.lbl_focus_badge = QLabel("Inativo")
        self.lbl_focus_badge.setStyleSheet("font-size: 9px; color: #94a3b8; background-color: rgba(255, 255, 255, 0.05); padding: 2px 6px; border-radius: 4px;")
        h_fhead.addWidget(self.lbl_focus_badge)
        f_layout.addLayout(h_fhead)

        h_ftimer = QHBoxLayout()
        self.lbl_timer = QLabel("25:00")
        self.lbl_timer.setStyleSheet("font-size: 26px; font-weight: 800; color: #38bdf8; font-family: monospace;")
        h_ftimer.addWidget(self.lbl_timer)
        h_ftimer.addStretch()

        self.btn_focus_toggle = QPushButton("▶ Iniciar Foco")
        self.btn_focus_toggle.setStyleSheet("background-color: rgba(14, 165, 233, 0.25); border: 1px solid rgba(14, 165, 233, 0.5); color: #38bdf8; font-weight: 700; font-size: 11px; padding: 5px 12px;")
        self.btn_focus_toggle.clicked.connect(self._toggle_focus)
        h_ftimer.addWidget(self.btn_focus_toggle)
        f_layout.addLayout(h_ftimer)

        self.lbl_focus_info = QLabel("Silencia notificações do GNOME e minimiza distrações (WhatsApp/Instagram).")
        self.lbl_focus_info.setStyleSheet("font-size: 10px; color: #64748b;")
        f_layout.addWidget(self.lbl_focus_info)
        c_layout.addWidget(card_focus)

        # 2. Daily Study Goal & Subject Log
        card_subjects = QFrame()
        card_subjects.setStyleSheet("background-color: rgba(20, 24, 32, 0.7); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 8px; padding: 6px;")
        s_layout = QVBoxLayout(card_subjects)
        s_layout.setContentsMargins(6, 6, 6, 6)
        s_layout.setSpacing(4)

        h_shead = QHBoxLayout()
        lbl_shead = QLabel("🎯 STATUS DE MATÉRIAS & LOG UFF:")
        lbl_shead.setStyleSheet("font-size: 9px; font-weight: 700; color: #94a3b8;")
        h_shead.addWidget(lbl_shead)
        h_shead.addStretch()

        self.lbl_quest_goal = QLabel("Meta: 0/5 questões hoje")
        self.lbl_quest_goal.setStyleSheet("font-size: 9px; font-weight: 700; color: #fbbf24; background-color: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.3); padding: 2px 6px; border-radius: 4px;")
        h_shead.addWidget(self.lbl_quest_goal)
        s_layout.addLayout(h_shead)

        self.subjects_container = QVBoxLayout()
        self.subjects_container.setSpacing(4)
        s_layout.addLayout(self.subjects_container)
        c_layout.addWidget(card_subjects)

        # 3. On-Hand Question Trainer Card
        card_questions = QFrame()
        card_questions.setStyleSheet("background-color: rgba(20, 24, 32, 0.7); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 8px; padding: 6px;")
        q_layout = QVBoxLayout(card_questions)
        q_layout.setContentsMargins(6, 6, 6, 6)
        q_layout.setSpacing(4)

        h_qhead = QHBoxLayout()
        lbl_qhead = QLabel("📝 TREINO RÁPIDO DE QUESTÕES (ON-HAND):")
        lbl_qhead.setStyleSheet("font-size: 9px; font-weight: 700; color: #94a3b8;")
        h_qhead.addWidget(lbl_qhead)
        h_qhead.addStretch()

        self.combo_q_subject = QComboBox()
        self.combo_q_subject.addItem("Cálculo III", "calculo3.json")
        self.combo_q_subject.addItem("Física II", "fisica2.json")
        self.combo_q_subject.setStyleSheet("""
            QComboBox { background-color: rgba(30, 35, 48, 0.8); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 4px; color: #f1f5f9; font-size: 10px; padding: 2px 6px; }
            QComboBox QAbstractItemView { background-color: #1a1e27; color: #f1f5f9; selection-background-color: #0284c7; }
        """)
        self.combo_q_subject.currentIndexChanged.connect(self._load_questions)
        h_qhead.addWidget(self.combo_q_subject)
        q_layout.addLayout(h_qhead)

        # Question Box
        self.box_question = QFrame()
        self.box_question.setStyleSheet("background-color: rgba(26, 32, 44, 0.6); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 6px; padding: 6px;")
        bq_layout = QVBoxLayout(self.box_question)
        bq_layout.setContentsMargins(4, 4, 4, 4)
        bq_layout.setSpacing(3)

        self.lbl_q_topic = QLabel("Tópico:")
        self.lbl_q_topic.setStyleSheet("font-size: 10px; font-weight: 700; color: #38bdf8;")
        bq_layout.addWidget(self.lbl_q_topic)

        self.lbl_q_text = QLabel("Carregando questão...")
        self.lbl_q_text.setStyleSheet("font-size: 11px; color: #f1f5f9;")
        self.lbl_q_text.setWordWrap(True)
        bq_layout.addWidget(self.lbl_q_text)

        self.lbl_q_solution = QLabel("")
        self.lbl_q_solution.setStyleSheet("font-size: 10px; color: #4ade80; background-color: rgba(34, 197, 94, 0.1); border: 1px solid rgba(34, 197, 94, 0.2); border-radius: 4px; padding: 4px;")
        self.lbl_q_solution.setWordWrap(True)
        self.lbl_q_solution.setVisible(False)
        bq_layout.addWidget(self.lbl_q_solution)

        q_layout.addWidget(self.box_question)

        # Question Action Buttons
        h_qbtns = QHBoxLayout()
        h_qbtns.setSpacing(4)

        self.btn_toggle_sol = QPushButton("💡 Gabarito")
        self.btn_toggle_sol.setStyleSheet("font-size: 10px; padding: 3px 6px;")
        self.btn_toggle_sol.clicked.connect(self._toggle_solution)
        h_qbtns.addWidget(self.btn_toggle_sol)

        btn_mark_done = QPushButton("✅ Resolvi (+1 Meta)")
        btn_mark_done.setStyleSheet("background-color: rgba(34, 197, 94, 0.2); border: 1px solid rgba(34, 197, 94, 0.4); color: #4ade80; font-size: 10px; font-weight: 700; padding: 3px 6px;")
        btn_mark_done.clicked.connect(self._mark_question_done)
        h_qbtns.addWidget(btn_mark_done)

        btn_next_q = QPushButton("🎲 Próxima")
        btn_next_q.setStyleSheet("background-color: rgba(14, 165, 233, 0.15); border: 1px solid rgba(14, 165, 233, 0.35); color: #38bdf8; font-size: 10px; padding: 3px 6px;")
        btn_next_q.clicked.connect(self._next_question)
        h_qbtns.addWidget(btn_next_q)

        q_layout.addLayout(h_qbtns)
        c_layout.addWidget(card_questions)

        # 4. Cálculo III Course Materials & Exercise Lists Card
        card_calc = QFrame()
        card_calc.setStyleSheet("background-color: rgba(20, 24, 32, 0.7); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 8px; padding: 6px;")
        cc_layout = QVBoxLayout(card_calc)
        cc_layout.setContentsMargins(6, 6, 6, 6)
        cc_layout.setSpacing(4)

        h_cchead = QHBoxLayout()
        lbl_cchead = QLabel("📚 ACERVO CÁLCULO III (Downloads/calc):")
        lbl_cchead.setStyleSheet("font-size: 9px; font-weight: 700; color: #94a3b8;")
        h_cchead.addWidget(lbl_cchead)
        h_cchead.addStretch()

        btn_calc_folder = QPushButton("📂 Abrir Pasta")
        btn_calc_folder.setStyleSheet("font-size: 9px; padding: 2px 5px; background: rgba(255,255,255,0.06); color: #cbd5e1; border-radius: 3px;")
        btn_calc_folder.clicked.connect(self._open_calc_folder)
        h_cchead.addWidget(btn_calc_folder)
        cc_layout.addLayout(h_cchead)

        h_ccquick = QHBoxLayout()
        h_ccquick.setSpacing(4)
        btn_apostila = QPushButton("📑 Apostila Completa")
        btn_apostila.setStyleSheet("background-color: rgba(14, 165, 233, 0.15); border: 1px solid rgba(14, 165, 233, 0.35); color: #38bdf8; font-size: 10px; font-weight: 600; padding: 4px;")
        btn_apostila.clicked.connect(lambda: self._open_calc_pdf("Apostila-CálculoIIIA-completa.pdf"))
        h_ccquick.addWidget(btn_apostila)

        btn_cronograma = QPushButton("📅 Cronograma")
        btn_cronograma.setStyleSheet("background-color: rgba(168, 85, 247, 0.15); border: 1px solid rgba(168, 85, 247, 0.35); color: #c084fc; font-size: 10px; font-weight: 600; padding: 4px;")
        btn_cronograma.clicked.connect(lambda: self._open_calc_pdf("Cronograma 2026.2_atualizado.pdf"))
        h_ccquick.addWidget(btn_cronograma)
        cc_layout.addLayout(h_ccquick)

        # Dropdown with specific EPs
        h_ep_row = QHBoxLayout()
        h_ep_row.setSpacing(4)
        self.combo_eps = QComboBox()
        self.combo_eps.setStyleSheet("""
            QComboBox { background-color: rgba(30, 35, 48, 0.8); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 4px; color: #f1f5f9; font-size: 10px; padding: 3px 6px; }
            QComboBox QAbstractItemView { background-color: #1a1e27; color: #f1f5f9; selection-background-color: #0284c7; }
        """)
        self._populate_calc_eps()
        h_ep_row.addWidget(self.combo_eps, 1)

        btn_open_ep = QPushButton("📖 Abrir PDF")
        btn_open_ep.setStyleSheet("background-color: rgba(34, 197, 94, 0.2); border: 1px solid rgba(34, 197, 94, 0.4); color: #4ade80; font-size: 10px; font-weight: 700; padding: 3px 8px;")
        btn_open_ep.clicked.connect(self._open_selected_ep)
        h_ep_row.addWidget(btn_open_ep)
        cc_layout.addLayout(h_ep_row)

        c_layout.addWidget(card_calc)

        # 5. Web Dashboard Link Button
        btn_open_web = QPushButton("🌐 Abrir Centro de Estudos Web 24/7 (localhost:8090)")
        btn_open_web.setStyleSheet("background-color: rgba(99, 102, 241, 0.2); border: 1px solid rgba(99, 102, 241, 0.4); color: #a5b4fc; font-weight: 700; font-size: 11px; padding: 6px;")
        btn_open_web.clicked.connect(self._open_web_dashboard)
        c_layout.addWidget(btn_open_web)

        scroll.setWidget(container)
        layout.addWidget(scroll)

        # Focus Timer
        self.focus_timer = QTimer(self)
        self.focus_timer.timeout.connect(self._on_timer_tick)

        self.reload_data()
        self._load_questions()

    def reload_data(self):
        while self.subjects_container.count() > 0:
            item = self.subjects_container.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not os.path.exists(DATA_PATH):
            return

        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)

            estudos = data.get("estudos", {})
            meta = estudos.get("meta_questoes_diarias", 5)
            feitas = estudos.get("questoes_feitas_hoje", 0)
            streak = estudos.get("streak_dias", 1)
            self.lbl_quest_goal.setText(f"🔥 Streak: {streak}d | Meta: {feitas}/{meta} hoje")

            disciplinas = estudos.get("disciplinas", [])
            for d in disciplinas:
                card = QFrame()
                card.setStyleSheet("background-color: rgba(30, 35, 48, 0.6); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 6px; padding: 4px 6px;")
                h = QHBoxLayout(card)
                h.setContentsMargins(4, 2, 4, 2)
                h.setSpacing(6)

                v = QVBoxLayout()
                v.setSpacing(1)

                nome = d.get("nome", "Disciplina")
                p1 = d.get("p1")
                p2 = d.get("p2")
                d_id = d.get("id")

                # Status calculation
                status_parts = []
                if d_id == "calculo3":
                    # Ponderada 2 e 3
                    meta_p2 = d.get("meta_p2", 4.9)
                    status_parts.append(f"<span style='color: #38bdf8;'>P1: <b>{p1}</b> (peso 2)</span>")
                    status_parts.append(f"<span style='color: #4ade80;'>Meta P2: <b>{meta_p2}</b> (peso 3)</span>")
                elif d_id == "fisica2":
                    p3_val = d.get("p3")
                    p3_str = f"P3: <b>{p3_val}</b>" if p3_val is not None else "<span style='color: #fbbf24;'>P3: Pendente</span>"
                    status_parts.append(f"<span style='color: #38bdf8;'>P1: <b>{p1}</b> | P2: <b>{p2}</b> | {p3_str}</span>")
                    avg_12 = (p1 + p2) / 2 if (p1 and p2) else 0
                    status_parts.append(f"<span style='color: #4ade80;'>Média P1+P2: <b>{avg_12:.1f}</b></span>")
                else:
                    if p1 is not None:
                        status_parts.append(f"P1: {p1}")
                    if d.get("data_p1"):
                        status_parts.append(f"Prova: {d['data_p1']}")

                # Last study warning
                ult_str = format_days_ago(d.get("ultimo_estudo"))
                is_accumulating = "dias atrás" in ult_str and int(ult_str.split()[0]) >= 3

                lbl_title = QLabel(f"<b>{nome}</b> · <span style='color: {'#f87171' if is_accumulating else '#94a3b8'};'>Estudo: {ult_str}</span>")
                lbl_title.setStyleSheet("font-size: 11px; color: #f1f5f9;")
                v.addWidget(lbl_title)

                lbl_sub = QLabel(" · ".join(status_parts))
                lbl_sub.setStyleSheet("font-size: 10px;")
                v.addWidget(lbl_sub)
                h.addLayout(v, 1)

                # Action button per discipline
                if d_id == "fisica2":
                    btn_sim = QPushButton("🚀 Simulador")
                    btn_sim.setStyleSheet("background-color: rgba(99, 102, 241, 0.2); border: 1px solid rgba(99, 102, 241, 0.4); color: #a5b4fc; font-size: 10px; font-weight: 700; padding: 3px 6px;")
                    btn_sim.clicked.connect(self._launch_pfisicas_simulador)
                    h.addWidget(btn_sim)

                btn_study = QPushButton("📖 Estudar")
                btn_study.setStyleSheet("background-color: rgba(14, 165, 233, 0.2); border: 1px solid rgba(14, 165, 233, 0.4); color: #38bdf8; font-size: 10px; font-weight: 600; padding: 3px 6px;")
                btn_study.clicked.connect(lambda _, did=d_id: self._start_study_session(did))
                h.addWidget(btn_study)

                self.subjects_container.addWidget(card)

        except Exception:
            pass

    def _load_questions(self):
        filename = self.combo_q_subject.currentData()
        q_path = os.path.join(QUESTOES_DIR, filename)
        self.current_questions = []
        self.current_q_index = 0
        self.show_solution = False
        self.lbl_q_solution.setVisible(False)

        if os.path.exists(q_path):
            try:
                with open(q_path, "r", encoding="utf-8") as f:
                    self.current_questions = json.load(f)
            except Exception:
                pass

        self._display_current_question()

    def _display_current_question(self):
        if not self.current_questions:
            self.lbl_q_topic.setText("Sem questões")
            self.lbl_q_text.setText("Nenhuma questão encontrada para este arquivo.")
            return

        q = self.current_questions[self.current_q_index % len(self.current_questions)]
        self.lbl_q_topic.setText(f"📌 {q.get('topico', 'Exercício')} (#{self.current_q_index + 1}/{len(self.current_questions)})")
        self.lbl_q_text.setText(q.get("enunciado", ""))
        self.lbl_q_solution.setText(f"<b>Gabarito:</b> {q.get('gabarito', '')}\n\n<i>Dica: {q.get('dica', '')}</i>")
        self.lbl_q_solution.setVisible(self.show_solution)

    def _toggle_solution(self):
        self.show_solution = not self.show_solution
        self.lbl_q_solution.setVisible(self.show_solution)
        self.btn_toggle_sol.setText("🙈 Ocultar" if self.show_solution else "💡 Gabarito")

    def _mark_question_done(self):
        did = "calculo3" if "calculo" in self.combo_q_subject.currentText().lower() else "fisica2"
        record_study_session(did)
        self.reload_data()
        self._next_question()

    def _next_question(self):
        if self.current_questions:
            self.current_q_index = (self.current_q_index + 1) % len(self.current_questions)
            self.show_solution = False
            self.btn_toggle_sol.setText("💡 Gabarito")
            self._display_current_question()

    def _start_study_session(self, did: str):
        record_study_session(did)
        self.reload_data()
        self._start_focus()
        if did == "fisica2":
            self._launch_pfisicas_simulador()
        elif did == "calculo3":
            # Switch question trainer to calculo3
            idx = self.combo_q_subject.findData("calculo3.json")
            if idx >= 0:
                self.combo_q_subject.setCurrentIndex(idx)

    def _launch_pfisicas_simulador(self):
        # Start simulator server if not running
        sh_script = os.path.join(PFISICAS_DIR, "iniciar_simulador.sh")
        if os.path.exists(sh_script):
            subprocess.Popen(["bash", sh_script], cwd=PFISICAS_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.Popen(["xdg-open", "http://localhost:8080"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _toggle_focus(self):
        if self.is_focusing:
            self._stop_focus()
        else:
            self._start_focus()

    def _start_focus(self):
        self.is_focusing = True
        self.btn_focus_toggle.setText("⏸ Pausar")
        self.btn_focus_toggle.setStyleSheet("background-color: rgba(239, 68, 68, 0.25); border: 1px solid rgba(239, 68, 68, 0.5); color: #f87171; font-weight: 700; font-size: 11px; padding: 5px 12px;")
        self.lbl_focus_badge.setText("Ativo 🛑")
        self.lbl_focus_badge.setStyleSheet("font-size: 9px; color: #4ade80; background-color: rgba(74, 222, 128, 0.15); border: 1px solid rgba(74, 222, 128, 0.3); padding: 2px 6px; border-radius: 4px; font-weight: 700;")
        self.lbl_focus_info.setText("Foco ATIVO: Notificações e distrações bloqueadas.")

        activate_focus_mode()
        self.focus_timer.start(1000)

    def _stop_focus(self):
        self.is_focusing = False
        self.focus_timer.stop()
        self.btn_focus_toggle.setText("▶ Retomar")
        self.btn_focus_toggle.setStyleSheet("background-color: rgba(14, 165, 233, 0.25); border: 1px solid rgba(14, 165, 233, 0.5); color: #38bdf8; font-weight: 700; font-size: 11px; padding: 5px 12px;")
        self.lbl_focus_badge.setText("Pausado")
        self.lbl_focus_badge.setStyleSheet("font-size: 9px; color: #94a3b8; background-color: rgba(255, 255, 255, 0.05); padding: 2px 6px; border-radius: 4px;")
        self.lbl_focus_info.setText("Notificações normais no sistema.")

        deactivate_focus_mode()

    def refresh_metrics(self):
        self.reload_data()

    def _on_timer_tick(self):
        if self.seconds_left > 0:
            self.seconds_left -= 1
            m = self.seconds_left // 60
            s = self.seconds_left % 60
            self.lbl_timer.setText(f"{m:02d}:{s:02d}")
            # Periodically ensure distraction apps stay minimized during focus
            if self.seconds_left % 30 == 0:
                block_active_distractions()
        else:
            self._stop_focus()
            self.seconds_left = 25 * 60
            self.lbl_timer.setText("25:00")
            subprocess.run(["notify-send", "Modo Foco Concluído!", "Hora de descansar por 5 minutos."], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _open_calc_folder(self):
        calc_dir = os.path.expanduser("~/Downloads/calc")
        if os.path.exists(calc_dir):
            subprocess.Popen(["xdg-open", calc_dir], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _open_calc_pdf(self, rel_filename: str):
        calc_dir = os.path.expanduser("~/Downloads/calc")
        target = os.path.join(calc_dir, rel_filename)
        if os.path.exists(target):
            subprocess.Popen(["xdg-open", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            QMessageBox.information(self, "Arquivo não encontrado", f"Arquivo não encontrado:\n{target}")

    def _populate_calc_eps(self):
        calc_dir = os.path.expanduser("~/Downloads/calc/Listas de exercícios")
        self.combo_eps.clear()
        if os.path.exists(calc_dir):
            for root, dirs, files in os.walk(calc_dir):
                for f in sorted(files):
                    if f.endswith(".pdf"):
                        # Pretty label
                        label = f.replace(".pdf", "").replace("-", " ")
                        if len(label) > 42:
                            label = label[:40] + "..."
                        self.combo_eps.addItem(label, os.path.join(root, f))

    def _open_selected_ep(self):
        filepath = self.combo_eps.currentData()
        if filepath and os.path.exists(filepath):
            subprocess.Popen(["xdg-open", filepath], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _open_web_dashboard(self):
        subprocess.Popen(["xdg-open", "http://localhost:8090"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
