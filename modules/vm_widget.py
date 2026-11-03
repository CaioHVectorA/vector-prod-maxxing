"""
Windows VM Management & Status Widget
Integrates with dockurr/windows container via /home/usuario/windows-vm/windows.sh
"""

import subprocess
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox
)
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, Qt

VM_SCRIPT = "/home/usuario/windows-vm/windows.sh"


class VMActionThread(QThread):
    finished_action = pyqtSignal(bool, str)

    def __init__(self, action: str):
        super().__init__()
        self.action = action

    def run(self):
        try:
            res = subprocess.run([VM_SCRIPT, self.action], capture_output=True, text=True, timeout=90)
            if res.returncode == 0:
                self.finished_action.emit(True, f"Ação '{self.action}' executada com sucesso.")
            else:
                self.finished_action.emit(False, res.stderr or res.stdout)
        except Exception as e:
            self.finished_action.emit(False, str(e))


class WindowsVMWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.is_running = False
        self.action_thread = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Header
        h_head = QHBoxLayout()
        lbl_head = QLabel("🖥️ VM WINDOWS (FUSION 360)")
        lbl_head.setObjectName("sec_title")
        h_head.addWidget(lbl_head)
        h_head.addStretch()

        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setObjectName("btn_icon")
        self.btn_refresh.setFixedSize(22, 22)
        self.btn_refresh.clicked.connect(self.check_vm_status)
        h_head.addWidget(self.btn_refresh)
        layout.addLayout(h_head)

        # Status Display Box
        self.box_status = QFrame()
        self.box_status.setStyleSheet("background-color: rgba(20, 24, 32, 0.7); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 8px; padding: 6px;")
        box_layout = QVBoxLayout(self.box_status)
        box_layout.setContentsMargins(6, 6, 6, 6)
        box_layout.setSpacing(4)

        self.lbl_vm_state = QLabel("⚫ Verificando...")
        self.lbl_vm_state.setStyleSheet("font-size: 12px; font-weight: 700; color: #94a3b8;")
        box_layout.addWidget(self.lbl_vm_state)

        self.lbl_vm_details = QLabel("Docker container: windows-fusion360")
        self.lbl_vm_details.setStyleSheet("font-size: 10px; color: #64748b;")
        box_layout.addWidget(self.lbl_vm_details)
        layout.addWidget(self.box_status)

        # Buttons Container
        self.btns_container = QHBoxLayout()
        self.btns_container.setSpacing(6)
        layout.addLayout(self.btns_container)

        self.lbl_op_status = QLabel("")
        self.lbl_op_status.setStyleSheet("font-size: 10px; color: #38bdf8;")
        layout.addWidget(self.lbl_op_status)

        # Polling Timer (every 4 seconds)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_vm_status)
        self.timer.start(4000)
        self.check_vm_status()

    def check_vm_status(self):
        try:
            res = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", "windows-fusion360"],
                capture_output=True, text=True, timeout=2.0
            )
            is_running = res.stdout.strip() == "true"
            self._update_ui(is_running)
        except Exception:
            self._update_ui(False, error=True)

    def _update_ui(self, is_running: bool, error: bool = False):
        self.is_running = is_running

        # Clear buttons
        while self.btns_container.count() > 0:
            item = self.btns_container.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if error:
            self.lbl_vm_state.setText("⚠️ Docker indisponível")
            self.lbl_vm_state.setStyleSheet("font-size: 12px; font-weight: 700; color: #f87171;")
            self.lbl_vm_details.setText("Não foi possível consultar o daemon do Docker.")
            return

        if is_running:
            self.lbl_vm_state.setText("🟢 Online (RDP :3389 / Web :8006)")
            self.lbl_vm_state.setStyleSheet("font-size: 12px; font-weight: 700; color: #4ade80;")
            self.lbl_vm_details.setText("Windows 11 pronto | Fusion 360 disponível")

            # Button: Conectar Remmina
            btn_connect = QPushButton("🖥️ Conectar (RDP)")
            btn_connect.setStyleSheet("background-color: rgba(14, 165, 233, 0.2); border: 1px solid rgba(14, 165, 233, 0.4); color: #38bdf8; font-weight: 600; font-size: 11px; padding: 5px;")
            btn_connect.clicked.connect(lambda: self._run_action("conectar"))
            self.btns_container.addWidget(btn_connect)

            # Button: Web VNC
            btn_web = QPushButton("🌐 Web")
            btn_web.setStyleSheet("background-color: rgba(99, 102, 241, 0.2); border: 1px solid rgba(99, 102, 241, 0.4); color: #818cf8; font-size: 11px; padding: 5px;")
            btn_web.clicked.connect(lambda: self._run_action("web"))
            self.btns_container.addWidget(btn_web)

            # Button: Parar
            btn_stop = QPushButton("🛑 Parar")
            btn_stop.setStyleSheet("background-color: rgba(220, 38, 38, 0.2); border: 1px solid rgba(220, 38, 38, 0.4); color: #fca5a5; font-size: 11px; padding: 5px;")
            btn_stop.clicked.connect(lambda: self._run_action("stop"))
            self.btns_container.addWidget(btn_stop)
        else:
            self.lbl_vm_state.setText("⚫ Desligada (RAM Liberada)")
            self.lbl_vm_state.setStyleSheet("font-size: 12px; font-weight: 700; color: #94a3b8;")
            self.lbl_vm_details.setText("Ligue quando precisar usar o Fusion 360.")

            # Button: Iniciar
            btn_start = QPushButton("⚡ Iniciar VM Windows")
            btn_start.setStyleSheet("background-color: rgba(14, 165, 233, 0.2); border: 1px solid rgba(14, 165, 233, 0.4); color: #38bdf8; font-weight: 700; font-size: 11px; padding: 6px;")
            btn_start.clicked.connect(lambda: self._run_action("iniciar"))
            self.btns_container.addWidget(btn_start)

    def _run_action(self, action: str):
        if self.action_thread and self.action_thread.isRunning():
            return
        self.lbl_op_status.setText(f"⏳ Executando '{action}'...")
        self.action_thread = VMActionThread(action)
        self.action_thread.finished_action.connect(self._on_action_finished)
        self.action_thread.start()

    def _on_action_finished(self, success: bool, msg: str):
        self.lbl_op_status.setText("")
        self.check_vm_status()
        if not success:
            QMessageBox.warning(self, "Aviso VM Windows", msg)
