"""
Writing & Creative Productivity Widget (modules/writing_widget.py)
Integrado com ``core.writing`` e ``core.launchers`` (zero chamadas diretas a subprocess).
"""

import os

from PyQt6.QtCore import QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core import launchers, writing


class WritingScannerThread(QThread):
    finished_scan = pyqtSignal(dict)

    def run(self):
        self.finished_scan.emit(writing.scan_writing())


class WritingProductivityWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.sprint_seconds_left = 0
        self.scanner = None
        self.sprint_timer = QTimer(self)
        self.sprint_timer.timeout.connect(self._sprint_tick)

        self._build_ui()

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh)
        self.refresh_timer.start(15000)

        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        self.card_summary = QFrame()
        self.card_summary.setObjectName("card")
        l_sum = QVBoxLayout(self.card_summary)
        l_sum.setContentsMargins(8, 6, 8, 6)
        l_sum.setSpacing(4)

        h_title = QHBoxLayout()
        lbl_head = QLabel("✍️ UNIVERSO UVC & ESCRITA CRIATIVA")
        lbl_head.setObjectName("sec_title")
        h_title.addWidget(lbl_head)
        h_title.addStretch()

        btn_ide_uvc = QPushButton("⚡ UVC no IDE")
        btn_ide_uvc.setStyleSheet(
            "font-size: 10px; font-weight: 700; padding: 2px 7px; background-color: #0284c7; color: white;"
        )
        btn_ide_uvc.setToolTip("Abrir projeto UVC completo na Antigravity IDE")
        btn_ide_uvc.clicked.connect(lambda: self._open_ide(writing.uvc_dir()))
        h_title.addWidget(btn_ide_uvc)
        l_sum.addLayout(h_title)

        h_metrics = QHBoxLayout()
        h_metrics.setSpacing(8)

        self.lbl_words_today = QLabel("0")
        self.lbl_words_today.setStyleSheet("font-size: 20px; font-weight: 800; color: #34d399;")
        self.lbl_words_today_sub = QLabel("palavras hoje (06h)")
        self.lbl_words_today_sub.setStyleSheet("font-size: 9px; color: #94a3b8;")
        v_w1 = QVBoxLayout()
        v_w1.setSpacing(0)
        v_w1.addWidget(self.lbl_words_today)
        v_w1.addWidget(self.lbl_words_today_sub)
        h_metrics.addLayout(v_w1)

        self.lbl_words_total = QLabel("0")
        self.lbl_words_total.setStyleSheet("font-size: 20px; font-weight: 800; color: #38bdf8;")
        self.lbl_words_total_sub = QLabel("total Red Right Hand")
        self.lbl_words_total_sub.setStyleSheet("font-size: 9px; color: #94a3b8;")
        v_w2 = QVBoxLayout()
        v_w2.setSpacing(0)
        v_w2.addWidget(self.lbl_words_total)
        v_w2.addWidget(self.lbl_words_total_sub)
        h_metrics.addLayout(v_w2)

        self.lbl_lore_meta = QLabel("...")
        self.lbl_lore_meta.setStyleSheet("font-size: 11px; font-weight: 600; color: #e2e8f0;")
        v_w3 = QVBoxLayout()
        v_w3.setSpacing(0)
        v_w3.addWidget(self.lbl_lore_meta)
        v_w3.addWidget(QLabel("lore & personagens", styleSheet="font-size: 9px; color: #94a3b8;"))
        h_metrics.addLayout(v_w3)

        h_metrics.addStretch()
        l_sum.addLayout(h_metrics)

        h_sprint = QHBoxLayout()
        h_sprint.setSpacing(6)

        self.btn_sprint = QPushButton("⏱️ Iniciar Sprint (20 min)")
        self.btn_sprint.setStyleSheet(
            "font-size: 10px; font-weight: 700; padding: 4px 8px; "
            "background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3);"
        )
        self.btn_sprint.clicked.connect(self._toggle_sprint)
        h_sprint.addWidget(self.btn_sprint)

        self.lbl_sprint_timer = QLabel("")
        self.lbl_sprint_timer.setStyleSheet("font-size: 12px; font-weight: 800; color: #f59e0b;")
        h_sprint.addWidget(self.lbl_sprint_timer)

        h_sprint.addStretch()

        btn_new_cap = QPushButton("➕ Novo Capítulo")
        btn_new_cap.setStyleSheet(
            "font-size: 10px; font-weight: 600; padding: 4px 8px; "
            "background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3);"
        )
        btn_new_cap.clicked.connect(self._create_new_chapter)
        h_sprint.addWidget(btn_new_cap)

        l_sum.addLayout(h_sprint)
        layout.addWidget(self.card_summary)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")

        self.caps_container = QWidget()
        self.l_caps = QVBoxLayout(self.caps_container)
        self.l_caps.setContentsMargins(0, 0, 0, 0)
        self.l_caps.setSpacing(5)

        scroll.setWidget(self.caps_container)
        layout.addWidget(scroll, 1)

    def refresh(self):
        if self.scanner and self.scanner.isRunning():
            return
        self.scanner = WritingScannerThread()
        self.scanner.finished_scan.connect(self._on_scan_finished)
        self.scanner.start()

    def _on_scan_finished(self, data: dict):
        total_words = data.get("total_words", 0)
        words_today = data.get("words_today", 0)
        chapters = data.get("chapters", [])
        char_count = data.get("char_count", 0)
        factions_count = data.get("factions_count", 0)

        self.lbl_words_today.setText(str(words_today))
        self.lbl_words_total.setText(f"{total_words:,}".replace(",", "."))
        self.lbl_lore_meta.setText(f"📖 {char_count} chars · {factions_count} facções")

        while self.l_caps.count():
            item = self.l_caps.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for c in chapters:
            card = self._create_chapter_item(c)
            self.l_caps.addWidget(card)

        self.l_caps.addStretch()

    def _create_chapter_item(self, c: dict) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        v_info = QVBoxLayout()
        v_info.setSpacing(1)

        lbl_title = QLabel(c["title"])
        lbl_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #ffffff;")
        v_info.addWidget(lbl_title)

        meta_text = f"{c['words']} palavras"
        if c.get("is_today"):
            meta_text += " · ✍️ Editado hoje"
        lbl_meta = QLabel(meta_text)
        lbl_meta.setStyleSheet(f"font-size: 9px; color: {'#34d399' if c.get('is_today') else '#94a3b8'};")
        v_info.addWidget(lbl_meta)
        layout.addLayout(v_info, 1)

        btn_edit = QPushButton("✍️ Escrever")
        btn_edit.setStyleSheet(
            "font-size: 10px; font-weight: 600; padding: 2px 7px; "
            "background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3);"
        )
        btn_edit.clicked.connect(lambda _, p=c["file"]: self._open_ide(p))
        layout.addWidget(btn_edit)

        return card

    def _open_ide(self, path: str):
        if os.path.exists(path):
            launchers.open_in_ide(path)

    def _create_new_chapter(self):
        title, ok = QInputDialog.getText(
            self, "Novo Capítulo", "Nome do novo capítulo (ex: Confronto em Severum):"
        )
        if not ok or not title.strip():
            return
        filepath = writing.create_chapter(title)
        self._open_ide(filepath)
        self.refresh()

    def _toggle_sprint(self):
        if self.sprint_seconds_left > 0:
            self.sprint_seconds_left = 0
            self.sprint_timer.stop()
            self.lbl_sprint_timer.setText("")
            self.btn_sprint.setText("⏱️ Iniciar Sprint (20 min)")
            self.btn_sprint.setStyleSheet(
                "font-size: 10px; font-weight: 700; padding: 4px 8px; "
                "background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3);"
            )
        else:
            self.sprint_seconds_left = 20 * 60
            self.sprint_timer.start(1000)
            self.btn_sprint.setText("🛑 Parar Sprint")
            self.btn_sprint.setStyleSheet(
                "font-size: 10px; font-weight: 700; padding: 4px 8px; "
                "background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4);"
            )
            self._sprint_tick()

    def _sprint_tick(self):
        if self.sprint_seconds_left <= 0:
            self.sprint_timer.stop()
            self.lbl_sprint_timer.setText("🎉 Sprint finalizado!")
            self.btn_sprint.setText("⏱️ Iniciar Sprint (20 min)")
            return
        m = self.sprint_seconds_left // 60
        s = self.sprint_seconds_left % 60
        self.lbl_sprint_timer.setText(f"{m:02d}:{s:02d}")
        self.sprint_seconds_left -= 1
