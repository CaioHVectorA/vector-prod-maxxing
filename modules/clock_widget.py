"""
Clock and Date Widget Module
"""

from datetime import datetime
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt6.QtCore import QTimer, Qt


class ClockWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)

        self.lbl_time = QLabel("00:00")
        self.lbl_time.setObjectName("clock_time")
        self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.lbl_date = QLabel("Carregando...")
        self.lbl_date.setObjectName("clock_date")
        self.lbl_date.setAlignment(Qt.AlignmentFlag.AlignLeft)

        layout.addWidget(self.lbl_time)
        layout.addWidget(self.lbl_date)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        self.update_time()

    def update_time(self):
        now = datetime.now()
        self.lbl_time.setText(now.strftime("%H:%M"))

        # Portuguese date formatting
        dias = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
        meses = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

        dia_sem = dias[now.weekday()]
        mes = meses[now.month - 1]
        self.lbl_date.setText(f"{dia_sem}, {now.day} de {mes}")
