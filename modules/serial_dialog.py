"""
Interactive Serial Monitor Dialog (PyQt6)
"""

import sys
import serial
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QPlainTextEdit, QLineEdit, QMessageBox
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont


class SerialReaderThread(QThread):
    data_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, port: str, baudrate: int):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.running = True
        self.ser = None

    def run(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=0.2)
            while self.running and self.ser.is_open:
                if self.ser.in_waiting > 0:
                    raw = self.ser.read(self.ser.in_waiting)
                    text = raw.decode("utf-8", errors="replace")
                    self.data_received.emit(text)
                self.msleep(10)
        except Exception as e:
            if self.running:
                self.error_occurred.emit(str(e))
        finally:
            if self.ser and self.ser.is_open:
                try:
                    self.ser.close()
                except Exception:
                    pass

    def stop(self):
        self.running = False
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception:
                pass
        self.wait(1000)

    def send_line(self, line: str):
        if self.ser and self.ser.is_open:
            try:
                self.ser.write((line + "\n").encode("utf-8"))
            except Exception as e:
                self.error_occurred.emit(f"Falha ao enviar: {e}")


class SerialMonitorDialog(QDialog):
    def __init__(self, port: str, baudrate: int = 115200, parent=None):
        super().__init__(parent)
        self.port = port
        self.baudrate = baudrate
        self.reader = None

        self.setWindowTitle(f"Monitor Serial — {port}")
        self.resize(680, 480)
        self.setStyleSheet("""
            QDialog {
                background-color: #16181f;
                color: #f1f5f9;
                font-family: 'Cantarell', 'Segoe UI', monospace;
            }
            QPlainTextEdit {
                background-color: #0f1117;
                color: #38bdf8;
                border: 1px solid #2d3748;
                border-radius: 6px;
                font-family: 'JetBrains Mono', 'Ubuntu Mono', 'Monospace';
                font-size: 12px;
                padding: 6px;
            }
            QLineEdit {
                background-color: #1e222d;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #1d4ed8; }
            QPushButton#btn_disconnect { background-color: #dc2626; }
            QPushButton#btn_disconnect:hover { background-color: #b91c1c; }
            QPushButton#btn_clear { background-color: #334155; }
            QPushButton#btn_clear:hover { background-color: #475569; }
            QComboBox {
                background-color: #1e222d;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Top Bar
        h_top = QHBoxLayout()
        lbl_info = QLabel(f"Porta: <b>{self.port}</b>")
        lbl_info.setStyleSheet("font-size: 13px;")
        h_top.addWidget(lbl_info)

        h_top.addStretch()

        lbl_baud = QLabel("Baudrate:")
        h_top.addWidget(lbl_baud)

        self.cb_baud = QComboBox()
        self.cb_baud.addItems(["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600"])
        idx = self.cb_baud.findText(str(self.baudrate))
        if idx >= 0:
            self.cb_baud.setCurrentIndex(idx)
        self.cb_baud.currentTextChanged.connect(self._on_baud_changed)
        h_top.addWidget(self.cb_baud)

        self.btn_clear = QPushButton("Limpar")
        self.btn_clear.setObjectName("btn_clear")
        self.btn_clear.clicked.connect(self._clear_terminal)
        h_top.addWidget(self.btn_clear)

        self.btn_toggle = QPushButton("Desconectar")
        self.btn_toggle.setObjectName("btn_disconnect")
        self.btn_toggle.clicked.connect(self._toggle_connection)
        h_top.addWidget(self.btn_toggle)

        layout.addLayout(h_top)

        # Output text
        self.txt_output = QPlainTextEdit()
        self.txt_output.setReadOnly(True)
        layout.addWidget(self.txt_output, 1)

        # Send row
        h_send = QHBoxLayout()
        self.inp_send = QLineEdit()
        self.inp_send.setPlaceholderText("Digite um comando e pressione Enter...")
        self.inp_send.returnPressed.connect(self._send_command)
        h_send.addWidget(self.inp_send, 1)

        self.btn_send = QPushButton("Enviar")
        self.btn_send.clicked.connect(self._send_command)
        h_send.addWidget(self.btn_send)

        layout.addLayout(h_send)

        self._start_connection()

    def _start_connection(self):
        baud = int(self.cb_baud.currentText())
        self.reader = SerialReaderThread(self.port, baud)
        self.reader.data_received.connect(self._append_data)
        self.reader.error_occurred.connect(self._on_error)
        self.reader.start()
        self.btn_toggle.setText("Desconectar")
        self.btn_toggle.setObjectName("btn_disconnect")
        self.txt_output.appendPlainText(f"[SISTEMA] Conectado em {self.port} @ {baud} bps\n")

    def _stop_connection(self):
        if self.reader:
            self.reader.stop()
            self.reader = None
        self.btn_toggle.setText("Conectar")
        self.btn_toggle.setStyleSheet("background-color: #16a34a;")
        self.txt_output.appendPlainText("[SISTEMA] Porta desconectada.\n")

    def _toggle_connection(self):
        if self.reader:
            self._stop_connection()
        else:
            self._start_connection()

    def _on_baud_changed(self):
        if self.reader:
            self._stop_connection()
            self._start_connection()

    def _append_data(self, text: str):
        self.txt_output.insertPlainText(text)
        sb = self.txt_output.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _send_command(self):
        cmd = self.inp_send.text()
        if not cmd:
            return
        if self.reader:
            self.reader.send_line(cmd)
            self.txt_output.appendPlainText(f"> {cmd}\n")
            self.inp_send.clear()
        else:
            QMessageBox.warning(self, "Aviso", "Porta serial não está conectada!")

    def _clear_terminal(self):
        self.txt_output.clear()

    def _on_error(self, err: str):
        self.txt_output.appendPlainText(f"\n[ERRO SERIAL] {err}\n")
        self._stop_connection()

    def closeEvent(self, event):
        self._stop_connection()
        super().closeEvent(event)
