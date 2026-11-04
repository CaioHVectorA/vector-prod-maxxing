"""
Hardware Identification & 1-Click Firmware Flashing Suite Module (modules/hardware_flasher.py)
Usa ``core.proc``, ``core.paths`` e ``core.launchers`` (zero chamadas diretas a subprocess).
"""

import glob
import os
import re
import time
from pathlib import Path
from typing import List, Optional, Tuple

import serial.tools.list_ports
from PyQt6.QtCore import QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from core import launchers, paths, proc
from core.osinfo import IS_WINDOWS, python_executable
from core.workspace import find_project_subdir
from modules.serial_dialog import SerialMonitorDialog


def _resolve_esptool() -> List[str]:
    """Localiza o comando do esptool em qualquer sistema operacional."""
    for bin_name in ("esptool.py", "esptool"):
        found = proc.which(bin_name)
        if found:
            return [found]

    home = str(Path.home())
    arduino_dirs = [
        os.path.join(home, ".arduino15", "packages", "esp32", "tools", "esptool_py"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Arduino15", "packages", "esp32", "tools", "esptool_py"),
    ]
    for base in arduino_dirs:
        if base and os.path.isdir(base):
            matches = sorted(glob.glob(os.path.join(base, "*", "esptool.py")), reverse=True)
            if matches:
                return [python_executable(), matches[0]]
            exe_matches = sorted(glob.glob(os.path.join(base, "*", "esptool.exe")), reverse=True)
            if exe_matches:
                return [exe_matches[0]]

    return [python_executable(), "-m", "esptool"]


ESP32_PRESETS = [
    {
        "id": "blink",
        "name": "⚡ Blink LED (GPIO 2)",
        "desc": "Pisca o LED onboard (GPIO 2) a cada 1 segundo (1Hz).",
        "type": "utility",
    },
    {
        "id": "wifi_scan",
        "name": "📡 Scanner Wi-Fi 2.4GHz",
        "desc": "Varre redes Wi-Fi e exibe SSID, RSSI e canal no Monitor Serial.",
        "type": "utility",
    },
    {
        "id": "i2c_scan",
        "name": "🔍 Scanner de Barramento I2C",
        "desc": "Varre endereços 0x01 a 0x7F nos pinos SDA=21 e SCL=22.",
        "type": "utility",
    },
    {
        "id": "ble_scan",
        "name": "📶 Scanner Bluetooth BLE",
        "desc": "Detecta beacons BLE e dispositivos próximos com endereço MAC.",
        "type": "utility",
    },
    {
        "id": "analog_read",
        "name": "📊 Leitor ADC / Tensão",
        "desc": "Lê entradas analógicas GPIO 34/36/39 e calcula a tensão real.",
        "type": "utility",
    },
    {
        "id": "wifi_ap_server",
        "name": "🌐 Wi-Fi AP + Servidor Web",
        "desc": "Cria a rede 'ESP32-Setup' e serve painel Web HTTP com controle de GPIO.",
        "type": "utility",
    },
    {
        "id": "deep_sleep",
        "name": "💤 Teste Deep Sleep & Wakeup",
        "desc": "Dorme em Deep Sleep por 10s ou acorda ao apertar o botão BOOT (GPIO 0).",
        "type": "utility",
    },
    {
        "id": "sys_telemetry",
        "name": "ℹ️ Telemetria Chip & Memória",
        "desc": "Exibe modelo do chip, núcleos, CPU MHz, Flash, RAM livre e MAC.",
        "type": "utility",
    },
    {
        "id": "pwm_fade",
        "name": "💡 PWM Breathing LED (Fade)",
        "desc": "Fade suave de brilho no LED da GPIO 2 usando timer LEDC de hardware.",
        "type": "utility",
    },
    {
        "id": "mp3_bt",
        "name": "🎵 Projeto MP3: Bluetooth A2DP",
        "desc": "Transmite áudio MP3 (PROGMEM) direto para o fone JBL TUNE500BT.",
        "type": "project",
    },
    {
        "id": "erase",
        "name": "🧹 Limpar Memória Flash (Erase)",
        "desc": "Apaga completamente a memória flash do chip ESP32.",
        "type": "danger",
    },
]


class BoardDetectorThread(QThread):
    board_detected = pyqtSignal(dict)

    def __init__(self, cached_port: Optional[str] = None, cached_info: Optional[dict] = None):
        super().__init__()
        self.cached_port = cached_port
        self.cached_info = cached_info

    def run(self):
        ports = list(serial.tools.list_ports.comports())
        target_port = None
        for p in ports:
            dev = p.device or ""
            if dev.startswith("/dev/ttyS"):
                continue
            if "ttyUSB" in dev or "ttyACM" in dev or p.vid is not None or (IS_WINDOWS and dev.upper().startswith("COM")):
                target_port = p
                break

        if not target_port:
            self.board_detected.emit({"connected": False, "port": None})
            return

        device = target_port.device

        if self.cached_info and self.cached_port == device and self.cached_info.get("connected"):
            self.board_detected.emit(self.cached_info)
            return

        vid = f"{target_port.vid:04x}" if target_port.vid else ""
        pid = f"{target_port.pid:04x}" if target_port.pid else ""
        vid_pid = f"{vid}:{pid}".lower()
        desc_low = (target_port.description or "").lower()

        info = {
            "connected": True,
            "port": device,
            "vid_pid": vid_pid,
            "board_type": "generic",
            "name": target_port.description or "Dispositivo Serial",
            "details": f"Porta: {device}",
        }

        if vid_pid in ("1a86:55d4", "10c4:ea60", "303a:1001", "303a:0002") or any(
            k in desc_low for k in ("esp", "cp210", "ch340", "ch9102", "usb-enhanced-serial")
        ):
            info["board_type"] = "esp32"
            info["name"] = "ESP32"
            res = proc.run([*_resolve_esptool(), "--port", device, "chip_id"], timeout=4.0)
            m_chip = re.search(r"Chip is (ESP32[^\n\r]*)", res.stdout)
            m_mac = re.search(r"MAC: ([0-9a-fA-F:]{17})", res.stdout)
            if m_chip:
                info["name"] = m_chip.group(1).strip()
            if m_mac:
                info["details"] = f"MAC: {m_mac.group(1)} | {device}"
            else:
                info["details"] = f"Dual Core 240MHz | {device}"

        elif vid_pid in ("1a86:7523", "2341:0043", "2341:0001") or "nano" in desc_low or "arduino" in desc_low:
            info["board_type"] = "nano"
            info["name"] = "Arduino Nano / Uno"
            info["details"] = f"ATmega328P @ 16MHz | {device}"

        elif vid_pid == "0483:3748":
            info["board_type"] = "stm32"
            info["name"] = "STM32 ST-Link v2"
            info["details"] = f"ARM Cortex Debugger | {device}"

        self.board_detected.emit(info)


class FlashWorkerThread(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)

    def __init__(self, port: str, board_type: str, preset_id: str):
        super().__init__()
        self.port = port
        self.board_type = board_type
        self.preset_id = preset_id

    def _execute_with_progress(self, cmd: list, initial_pct: int = 10, timeout: int = 90) -> Tuple[int, str]:
        full_output = []
        try:
            p = proc.popen_piped(cmd)
            buffer = ""
            start_time = time.time()
            current_pct = initial_pct

            while True:
                if p.poll() is not None:
                    break
                if time.time() - start_time > timeout:
                    p.kill()
                    return -1, "Timeout durante a execução."

                ch = p.stdout.read(1) if p.stdout else ""
                if not ch:
                    time.sleep(0.01)
                    continue
                buffer += ch
                if ch in ("\r", "\n"):
                    line = buffer.strip()
                    buffer = ""
                    if line:
                        full_output.append(line)
                        m = re.search(r"\((\d+)\s*%\)", line) or re.search(r"(\d+)\s*%", line)
                        if m:
                            pct = int(m.group(1))
                            current_pct = max(current_pct, min(99, pct))
                            self.progress.emit(current_pct, f"Gravando: {current_pct}% ({line[:35]})")
                        elif "Connecting" in line:
                            self.progress.emit(8, "Conectando ao chip...")
                        elif "Chip is" in line:
                            self.progress.emit(15, f"Chip detectado: {line[:30]}")
                        elif "Erasing" in line or "erase" in line.lower():
                            self.progress.emit(25, "Apagando setores da memória...")
                        elif "Writing at" in line:
                            current_pct = min(95, current_pct + 2)
                            self.progress.emit(current_pct, f"Gravando dados... {current_pct}%")
                        elif "Wrote" in line or "Hash of data" in line:
                            self.progress.emit(96, "Validando gravação (checksum)...")
                        elif "Hard resetting" in line or "Leaving" in line:
                            self.progress.emit(100, "Reiniciando placa...")

            p.wait(timeout=5)
            rem = p.stdout.read() if p.stdout else ""
            if rem:
                full_output.append(rem)
            return p.returncode, "\n".join(full_output)
        except Exception as e:
            return -1, str(e)

    def run(self):
        try:
            esptool_cmd = _resolve_esptool()
            mp3_dir = find_project_subdir("mp3")

            if self.board_type == "esp32":
                if self.preset_id == "mp3_bt":
                    self.progress.emit(5, "Compilando Projeto MP3 com PlatformIO...")
                    res_build = proc.run(
                        ["pio", "run", "-d", mp3_dir, "-e", "esp32-wroom-test"],
                        timeout=120.0,
                    )
                    if not res_build.ok:
                        self.finished.emit(False, f"Erro de compilação do MP3:\n{res_build.output or res_build.error}")
                        return

                    self.progress.emit(15, f"Gravando MP3 em {self.port} (115.2 kbps)...")
                    build_dir = os.path.join(mp3_dir, ".pio", "build", "esp32-wroom-test")
                    bin_file = os.path.join(build_dir, "firmware.bin")
                    boot_file = os.path.join(build_dir, "bootloader.bin")
                    part_file = os.path.join(build_dir, "partitions.bin")

                    cmd = [
                        *esptool_cmd,
                        "--chip", "esp32", "--port", self.port, "--baud", "115200",
                        "--before", "default_reset", "--after", "hard_reset", "write_flash", "-z",
                        "--flash_mode", "dio", "--flash_freq", "keep", "--flash_size", "detect",
                        "0x1000", boot_file,
                        "0x8000", part_file,
                        "0x10000", bin_file,
                    ]
                    code, out = self._execute_with_progress(cmd, initial_pct=15, timeout=90)
                    if code == 0:
                        self.progress.emit(100, "Gravação 100% concluída!")
                        self.finished.emit(
                            True, "Projeto MP3 gravado! Abra o Monitor Serial para acompanhar a conexão ao fone."
                        )
                    else:
                        self.finished.emit(False, out)
                    return

                if self.preset_id == "erase":
                    self.progress.emit(20, "Limpando memória flash do ESP32...")
                    cmd = [*esptool_cmd, "--port", self.port, "--baud", "115200", "--no-stub", "erase_flash"]
                    code, out = self._execute_with_progress(cmd, initial_pct=20, timeout=30)
                    if code == 0:
                        self.progress.emit(100, "Flash apagada!")
                        self.finished.emit(True, "Memória flash do ESP32 limpa com sucesso!")
                    else:
                        self.finished.emit(False, out)
                    return

                bin_dir = os.path.join(paths.FIRMWARES_DIR, "esp32", self.preset_id, "build", "esp32.esp32.esp32")
                bin_file = os.path.join(bin_dir, f"{self.preset_id}.ino.bin")
                boot_file = os.path.join(bin_dir, f"{self.preset_id}.ino.bootloader.bin")
                part_file = os.path.join(bin_dir, f"{self.preset_id}.ino.partitions.bin")

                if not os.path.exists(bin_file):
                    self.finished.emit(False, f"Binário não encontrado: {bin_file}")
                    return

                self.progress.emit(10, f"Iniciando gravação de {self.preset_id}...")
                cmd = [
                    *esptool_cmd,
                    "--chip", "esp32", "--port", self.port, "--baud", "115200",
                    "--before", "default_reset", "--after", "hard_reset", "write_flash", "-z",
                    "--flash_mode", "dio", "--flash_freq", "keep", "--flash_size", "detect",
                    "0x1000", boot_file,
                    "0x8000", part_file,
                    "0x10000", bin_file,
                ]
                code, out = self._execute_with_progress(cmd, initial_pct=10, timeout=70)
                if code == 0:
                    self.progress.emit(100, "Concluído!")
                    self.finished.emit(True, f"Firmware '{self.preset_id}' gravado com sucesso!")
                else:
                    self.finished.emit(False, out)

            elif self.board_type == "nano":
                if self.preset_id == "blink":
                    self.progress.emit(15, "Gravando Blink no Arduino Nano...")
                    hex_file = os.path.join(
                        paths.FIRMWARES_DIR, "arduino_nano", "blink", "build", "arduino.avr.nano", "blink.ino.hex"
                    )
                    cmd = [
                        "avrdude", "-v", "-p", "atmega328p", "-c", "arduino",
                        "-P", self.port, "-b", "115200", "-D", f"-Uflash:w:{hex_file}:i",
                    ]
                    code, out = self._execute_with_progress(cmd, initial_pct=15, timeout=25)
                    if code == 0:
                        self.progress.emit(100, "Concluído!")
                        self.finished.emit(True, "Blink gravado no Arduino Nano (LED 13 piscando)!")
                    else:
                        self.finished.emit(False, out)
            else:
                self.finished.emit(False, f"Placa não suportada para o preset: {self.preset_id}")
        except Exception as e:
            self.finished.emit(False, str(e))


class HardwareFlasherWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.current_board = {"connected": False}
        self.detector_thread = None
        self.flash_thread = None
        self.active_dialogs = []
        self.is_flashing = False

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 10, 12, 10)
        self.layout.setSpacing(6)

        h_head = QHBoxLayout()
        lbl_head = QLabel("⚡ SUÍTE DE FLASH & HARDWARE")
        lbl_head.setObjectName("sec_title")
        h_head.addWidget(lbl_head)
        h_head.addStretch()

        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setObjectName("btn_icon")
        self.btn_refresh.setFixedSize(22, 22)
        self.btn_refresh.setToolTip("Atualizar detecção de placa")
        self.btn_refresh.clicked.connect(self.scan_board)
        h_head.addWidget(self.btn_refresh)
        self.layout.addLayout(h_head)

        self.card_info = QFrame()
        self.card_info.setStyleSheet(
            "background-color: rgba(20, 24, 32, 0.7); border: 1px solid rgba(255, 255, 255, 0.05); "
            "border-radius: 8px; padding: 6px;"
        )
        info_layout = QVBoxLayout(self.card_info)
        info_layout.setContentsMargins(6, 6, 6, 6)
        info_layout.setSpacing(3)

        h_title = QHBoxLayout()
        self.lbl_board_name = QLabel("⚫ Nenhuma placa conectada")
        self.lbl_board_name.setStyleSheet("font-size: 13px; font-weight: 700; color: #94a3b8;")
        h_title.addWidget(self.lbl_board_name, 1)

        self.btn_serial = QPushButton("⚡ Monitor Serial")
        self.btn_serial.setObjectName("btn_action_accent")
        self.btn_serial.setStyleSheet("font-size: 11px; padding: 3px 8px;")
        self.btn_serial.setToolTip("Abrir Monitor Serial a 115200 bps")
        self.btn_serial.clicked.connect(self._open_serial)
        self.btn_serial.setVisible(False)
        h_title.addWidget(self.btn_serial)
        info_layout.addLayout(h_title)

        self.lbl_board_sub = QLabel("Espete um ESP32, Arduino ou STM32 na USB")
        self.lbl_board_sub.setStyleSheet("font-size: 11px; color: #64748b;")
        info_layout.addWidget(self.lbl_board_sub)
        self.layout.addWidget(self.card_info)

        self.h_quick = QHBoxLayout()
        self.h_quick.setSpacing(6)

        self.btn_quick_mp3 = QPushButton("🎵 Flash: Projeto MP3")
        self.btn_quick_mp3.setStyleSheet(
            "background-color: rgba(168, 85, 247, 0.2); border: 1px solid rgba(168, 85, 247, 0.4); "
            "color: #c084fc; font-weight: 700; font-size: 11px; padding: 5px;"
        )
        self.btn_quick_mp3.setToolTip("Compilar e gravar o projeto mp3 (Bluetooth A2DP)")
        self.btn_quick_mp3.clicked.connect(lambda: self._start_flash("mp3_bt"))
        self.h_quick.addWidget(self.btn_quick_mp3)

        self.btn_quick_blink = QPushButton("⚡ Flash: Blink")
        self.btn_quick_blink.setStyleSheet(
            "background-color: rgba(14, 165, 233, 0.15); border: 1px solid rgba(14, 165, 233, 0.35); "
            "color: #38bdf8; font-weight: 600; font-size: 11px; padding: 5px;"
        )
        self.btn_quick_blink.clicked.connect(lambda: self._start_flash("blink"))
        self.h_quick.addWidget(self.btn_quick_blink)

        self.layout.addLayout(self.h_quick)

        lbl_dropdown = QLabel("BIBLIOTECA DE FIRMWARES:")
        lbl_dropdown.setStyleSheet("font-size: 10px; font-weight: 700; color: #94a3b8; margin-top: 2px;")
        self.layout.addWidget(lbl_dropdown)

        self.combo_presets = QComboBox()
        self.combo_presets.setStyleSheet(
            "QComboBox {"
            "    background-color: rgba(20, 24, 32, 0.8);"
            "    border: 1px solid rgba(255, 255, 255, 0.1);"
            "    border-radius: 6px;"
            "    color: #f1f5f9;"
            "    font-size: 11px;"
            "    padding: 5px 8px;"
            "}"
            "QComboBox::drop-down { border: none; width: 20px; }"
            "QComboBox QAbstractItemView {"
            "    background-color: #1a1e27; color: #f1f5f9;"
            "    selection-background-color: #0284c7; border: 1px solid rgba(255, 255, 255, 0.1);"
            "}"
        )
        self.combo_presets.currentIndexChanged.connect(self._on_preset_changed)
        self.layout.addWidget(self.combo_presets)

        self.lbl_preset_desc = QLabel("")
        self.lbl_preset_desc.setStyleSheet("font-size: 10px; color: #94a3b8; font-style: italic;")
        self.lbl_preset_desc.setWordWrap(True)
        self.layout.addWidget(self.lbl_preset_desc)

        self.btn_flash_selected = QPushButton("⚡ Gravar Firmware Selecionado")
        self.btn_flash_selected.setStyleSheet(
            "background-color: rgba(14, 165, 233, 0.25); border: 1px solid rgba(14, 165, 233, 0.5); "
            "color: #38bdf8; font-weight: 700; font-size: 11px; padding: 6px;"
        )
        self.btn_flash_selected.clicked.connect(self._flash_current_combo)
        self.layout.addWidget(self.btn_flash_selected)

        self.bar_flash = QProgressBar()
        self.bar_flash.setRange(0, 100)
        self.bar_flash.setValue(0)
        self.bar_flash.setTextVisible(True)
        self.bar_flash.setFixedHeight(18)
        self.bar_flash.setStyleSheet(
            "QProgressBar {"
            "    background-color: rgba(20, 24, 32, 0.9);"
            "    border: 1px solid rgba(255, 255, 255, 0.12);"
            "    border-radius: 4px; text-align: center; color: #f1f5f9;"
            "    font-size: 10px; font-weight: 700;"
            "}"
            "QProgressBar::chunk {"
            "    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #38bdf8);"
            "    border-radius: 3px;"
            "}"
        )
        self.bar_flash.setVisible(False)
        self.layout.addWidget(self.bar_flash)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("font-size: 11px; color: #38bdf8; font-weight: 600;")
        self.lbl_status.setWordWrap(True)
        self.layout.addWidget(self.lbl_status)

        btn_open_folder = QPushButton("📂 Abrir Pasta de Firmwares (.bin/.ino)")
        btn_open_folder.setStyleSheet(
            "font-size: 10px; padding: 4px 8px; background-color: rgba(35, 40, 52, 0.6); color: #cbd5e1;"
        )
        btn_open_folder.setToolTip("Abra para adicionar novos códigos e aumentar sua biblioteca")
        btn_open_folder.clicked.connect(self._open_firmwares_folder)
        self.layout.addWidget(btn_open_folder)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.scan_board)
        self.timer.start(5000)
        self.scan_board()

    def _open_firmwares_folder(self):
        launchers.open_path(paths.FIRMWARES_DIR)

    def scan_board(self):
        if self.is_flashing:
            return
        if self.detector_thread and self.detector_thread.isRunning():
            return
        cached_port = self.current_board.get("port")
        self.detector_thread = BoardDetectorThread(cached_port, self.current_board)
        self.detector_thread.board_detected.connect(self._on_board_detected)
        self.detector_thread.start()

    def _on_board_detected(self, info: dict):
        self.current_board = info

        if not info["connected"]:
            self.lbl_board_name.setText("⚫ Nenhuma placa conectada")
            self.lbl_board_name.setStyleSheet("font-size: 13px; font-weight: 700; color: #94a3b8;")
            self.lbl_board_sub.setText("Espete um ESP32, Arduino ou STM32 na USB")
            self.btn_serial.setVisible(False)
            self.btn_quick_mp3.setEnabled(False)
            self.btn_quick_blink.setEnabled(False)
            self.btn_flash_selected.setEnabled(False)
            self.combo_presets.clear()
            self.combo_presets.addItem("Conecte uma placa primeiro...")
            self.lbl_preset_desc.setText("")
            return

        name = info["name"]
        details = info["details"]
        b_type = info["board_type"]

        self.lbl_board_name.setText(f"🟢 {name}")
        self.lbl_board_name.setStyleSheet("font-size: 13px; font-weight: 700; color: #4ade80;")
        self.lbl_board_sub.setText(details)
        self.btn_serial.setVisible(True)
        self.btn_quick_mp3.setEnabled(b_type == "esp32")
        self.btn_quick_blink.setEnabled(True)
        self.btn_flash_selected.setEnabled(True)

        self._populate_presets(b_type)

    def _populate_presets(self, b_type: str):
        self.combo_presets.blockSignals(True)
        self.combo_presets.clear()

        if b_type == "esp32":
            for p in ESP32_PRESETS:
                self.combo_presets.addItem(p["name"], p["id"])
        elif b_type == "nano":
            self.combo_presets.addItem("⚡ Blink LED (Pino 13)", "blink")
        else:
            self.combo_presets.addItem("Dispositivo genérico (suporte básico)", "none")

        self.combo_presets.blockSignals(False)
        self._on_preset_changed(self.combo_presets.currentIndex())

    def _on_preset_changed(self, index: int):
        if index < 0:
            return
        preset_id = self.combo_presets.currentData()
        for p in ESP32_PRESETS:
            if p["id"] == preset_id:
                self.lbl_preset_desc.setText(p["desc"])
                return
        self.lbl_preset_desc.setText("")

    def _flash_current_combo(self):
        preset_id = self.combo_presets.currentData()
        if preset_id and preset_id != "none":
            self._start_flash(preset_id)

    def _start_flash(self, preset_id: str):
        if not self.current_board.get("connected") or self.is_flashing:
            return
        self.is_flashing = True
        self.timer.stop()

        port = self.current_board["port"]
        b_type = self.current_board["board_type"]

        self.bar_flash.setValue(0)
        self.bar_flash.setFormat("Iniciando gravação... 0%")
        self.bar_flash.setVisible(True)

        self.lbl_status.setText(f"⏳ Gravando {preset_id} em {port}...")
        self.lbl_status.setStyleSheet("color: #fbbf24; font-weight: 600; font-size: 11px;")

        self.flash_thread = FlashWorkerThread(port, b_type, preset_id)
        self.flash_thread.progress.connect(self._on_flash_progress)
        self.flash_thread.finished.connect(self._on_flash_finished)
        self.flash_thread.start()

    def _on_flash_progress(self, pct: int, msg: str):
        self.bar_flash.setValue(pct)
        self.bar_flash.setFormat(f"{pct}% - {msg[:35]}")
        self.lbl_status.setText(f"⏳ {msg}")

    def _on_flash_finished(self, success: bool, msg: str):
        self.is_flashing = False
        self.timer.start(5000)

        if success:
            self.bar_flash.setValue(100)
            self.bar_flash.setFormat("✅ 100% Gravado com Sucesso!")
            self.lbl_status.setText(f"✅ {msg}")
            self.lbl_status.setStyleSheet("color: #4ade80; font-weight: 600; font-size: 11px;")
            QTimer.singleShot(4000, lambda: self.bar_flash.setVisible(False))
        else:
            self.bar_flash.setVisible(False)
            self.lbl_status.setText(f"❌ Erro ao gravar: {msg[:60]}...")
            self.lbl_status.setStyleSheet("color: #f87171; font-weight: 600; font-size: 11px;")
            QMessageBox.critical(self, "Falha na Gravação", msg)

    def _open_serial(self):
        if not self.current_board.get("connected"):
            return
        port = self.current_board["port"]
        dlg = SerialMonitorDialog(port, baudrate=115200, parent=self)
        dlg.show()
        self.active_dialogs.append(dlg)
