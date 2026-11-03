#!/usr/bin/env python3
"""
Dev & Hardware Desktop HUD (Interactive Rainmeter-style widget for Linux/GNOME)
Features:
- Global Windows VM status badge next to Clock
- Pin on Top vs Dock on Desktop background (_NET_WM_STATE_BELOW / ABOVE)
- Solid vs Glassmorphism background toggle
- Collapsible mode (shrinks to sleek top bar pill)
- Freely resizable window with QSizeGrip and persistent dimensions
- Tabbed organization: Dev, IA & RL, Eng & Hardware, Escrita (UVC), Estudos (UFF)
- Antigravity IDE integration
- Bidirectional AI-HUD communication protocol via QFileSystemWatcher
- 24/7 Localhost Web Dashboard integration
"""

import sys
import os
import json
import subprocess

# Add project root to path
base_dir = os.path.dirname(os.path.realpath(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSystemTrayIcon, QMenu, QTabWidget, QSizeGrip
)
from PyQt6.QtCore import Qt, QPoint, QRect, QTimer, QFileSystemWatcher
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont

from styles import HUD_STYLESHEET
from modules.clock_widget import ClockWidget
from modules.dev_widget import DevProductivityWidget
from modules.eng_widget import EngHardwareWidget
from modules.writing_widget import WritingProductivityWidget
from modules.study_widget import StudyWidget

CONFIG_DIR = os.path.expanduser("~/.config/desktop-hud")
DATA_PATH = os.path.join(CONFIG_DIR, "data.json")
EVENTS_FILE = os.path.join(CONFIG_DIR, "events.jsonl")

DEFAULT_WIDTH = 450
DEFAULT_HEIGHT = 760
VM_SCRIPT = "/home/usuario/windows-vm/windows.sh"


class DesktopHUDWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.is_pinned = True
        self.is_solid = False
        self.is_collapsed = False
        self.drag_position = None
        self.saved_height = DEFAULT_HEIGHT
        self.saved_width = DEFAULT_WIDTH

        self._load_settings()

        self.setObjectName("hud_root_solid" if self.is_solid else "hud_root")
        self._update_window_flags()

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet(HUD_STYLESHEET)

        self._build_ui()

        if self.is_collapsed:
            self.setFixedWidth(self.saved_width)
            self.setFixedHeight(48)
            self.tabs.setVisible(False)
            self.bottom_bar_widget.setVisible(False)
            self.btn_collapse.setText("▼")
        else:
            self.setMinimumSize(360, 420)
            self.setMaximumSize(950, 1150)
            self.resize(self.saved_width, self.saved_height)

        self._position_on_screen()

        # Global VM Poller Timer
        self.vm_timer = QTimer(self)
        self.vm_timer.timeout.connect(self._check_vm_status)
        self.vm_timer.start(4000)
        self._check_vm_status()

        # Bidirectional AI-HUD Communication File Watcher
        self._setup_file_watcher()

    def _load_settings(self):
        self.saved_width = DEFAULT_WIDTH
        self.saved_height = DEFAULT_HEIGHT
        if os.path.exists(DATA_PATH):
            try:
                with open(DATA_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    cfg = data.get("settings", {})
                    self.is_solid = cfg.get("solid_background", False)
                    self.is_pinned = cfg.get("is_pinned", True)
                    self.is_collapsed = cfg.get("is_collapsed", False)
                    self.active_tab = cfg.get("active_tab", 0)
                    self.saved_width = max(360, min(950, cfg.get("window_width", DEFAULT_WIDTH)))
                    self.saved_height = max(420, min(1150, cfg.get("window_height", DEFAULT_HEIGHT)))
            except Exception:
                pass

    def _save_settings(self):
        if not os.path.exists(DATA_PATH):
            return
        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "settings" not in data:
                data["settings"] = {}
            data["settings"]["solid_background"] = self.is_solid
            data["settings"]["is_pinned"] = self.is_pinned
            data["settings"]["is_collapsed"] = self.is_collapsed
            data["settings"]["active_tab"] = self.tabs.currentIndex() if hasattr(self, 'tabs') else 0
            data["settings"]["window_width"] = self.width()
            if not self.is_collapsed:
                data["settings"]["window_height"] = self.height()
            with open(DATA_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _setup_file_watcher(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        self.watcher = QFileSystemWatcher(self)
        for path in [DATA_PATH, EVENTS_FILE]:
            if not os.path.exists(path):
                try:
                    with open(path, "a", encoding="utf-8") as f:
                        pass
                except Exception:
                    pass
            if os.path.exists(path):
                self.watcher.addPath(path)
        self.watcher.fileChanged.connect(self._on_watched_file_changed)

    def _on_watched_file_changed(self, path):
        # Refresh study and writing widgets immediately
        QTimer.singleShot(200, self._refresh_all_tabs)
        if os.path.exists(path) and path not in self.watcher.files():
            self.watcher.addPath(path)

    def _refresh_all_tabs(self):
        try:
            if hasattr(self, 'tab_study'):
                self.tab_study.refresh_metrics()
            if hasattr(self, 'tab_writing'):
                self.tab_writing.refresh()
            if hasattr(self, 'tab_dev'):
                self.tab_dev.refresh_all()
        except Exception:
            pass

    def _update_window_flags(self):
        # Frameless top-level desktop window that never gets withdrawn
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)

    def _apply_x11_layer(self):
        try:
            win_id = hex(int(self.winId()))
            # Remove any lingering below atom to prevent GNOME from withdrawing the window
            subprocess.run(["wmctrl", "-i", "-r", win_id, "-b", "remove,below"], capture_output=True)
            # Skip taskbar and alt-tab pager, stick to all workspaces like a true desktop widget
            subprocess.run(["wmctrl", "-i", "-r", win_id, "-b", "add,skip_taskbar,skip_pager,sticky"], capture_output=True)
            if self.is_pinned:
                subprocess.run(["wmctrl", "-i", "-r", win_id, "-b", "add,above"], capture_output=True)
                self.raise_()
            else:
                subprocess.run(["wmctrl", "-i", "-r", win_id, "-b", "remove,above"], capture_output=True)
                self.lower()
        except Exception:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(150, self._apply_x11_layer)

    def toggle_pin(self):
        self.is_pinned = not self.is_pinned
        try:
            win_id = hex(int(self.winId()))
            if self.is_pinned:
                subprocess.run(["wmctrl", "-i", "-r", win_id, "-b", "add,above"], capture_output=True)
                self.raise_()
                self.btn_pin.setText("📌")
                self.btn_pin.setToolTip("Fixado no Topo (clique para deixar na Área de Trabalho)")
                self.btn_pin.setStyleSheet("color: #38bdf8; background-color: rgba(56, 189, 248, 0.2);")
            else:
                subprocess.run(["wmctrl", "-i", "-r", win_id, "-b", "remove,above"], capture_output=True)
                self.lower()
                self.btn_pin.setText("🖥️")
                self.btn_pin.setToolTip("Na Área de Trabalho (clique para fixar no topo)")
                self.btn_pin.setStyleSheet("color: #a855f7; background-color: rgba(168, 85, 247, 0.2);")
        except Exception:
            pass
        self._save_settings()

    def toggle_solid(self):
        self.is_solid = not self.is_solid
        self.setObjectName("hud_root_solid" if self.is_solid else "hud_root")
        self.btn_solid.setText("🎨" if not self.is_solid else "⬛")
        self.btn_solid.setToolTip("Modo Sólido (Área de Trabalho)" if self.is_solid else "Modo Translúcido (Vidro)")
        self.setStyleSheet(HUD_STYLESHEET)
        self._save_settings()
        self.update()
        self.repaint()

    def toggle_collapse(self):
        self.is_collapsed = not self.is_collapsed
        if self.is_collapsed:
            self.saved_height = max(420, self.height())
            self.tabs.setVisible(False)
            self.bottom_bar_widget.setVisible(False)
            self.setMinimumHeight(48)
            self.setMaximumHeight(48)
            self.resize(self.width(), 48)
            self.btn_collapse.setText("▼")
            self.btn_collapse.setToolTip("Expandir painel completo")
        else:
            self.setMinimumSize(360, 420)
            self.setMaximumSize(950, 1150)
            self.resize(self.width(), self.saved_height)
            self.tabs.setVisible(True)
            self.bottom_bar_widget.setVisible(True)
            self.btn_collapse.setText("▲")
            self.btn_collapse.setToolTip("Minimizar para barra compacta")
        self._save_settings()

    def _build_ui(self):
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(8, 6, 8, 6)
        self.root_layout.setSpacing(4)

        # Header bar (Clock, Global VM Badge, Controls)
        h_head = QHBoxLayout()
        h_head.setContentsMargins(2, 0, 2, 0)
        h_head.setSpacing(6)

        # Compact Clock & Date
        self.clock_widget = ClockWidget(self)
        h_head.addWidget(self.clock_widget)

        # Global VM Status Badge (Beside Clock)
        self.btn_vm_badge = QPushButton("⚫ Win11")
        self.btn_vm_badge.setStyleSheet("font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 6px; background-color: rgba(35, 40, 52, 0.7); color: #94a3b8; border: 1px solid rgba(255, 255, 255, 0.08);")
        self.btn_vm_badge.setToolTip("Status da VM Windows (Fusion 360)")
        self.btn_vm_badge.clicked.connect(self._on_vm_badge_clicked)
        h_head.addWidget(self.btn_vm_badge)

        h_head.addStretch()

        # Web Dashboard Button
        btn_web = QPushButton("🌐 Web")
        btn_web.setObjectName("btn_icon")
        btn_web.setToolTip("Abrir Centro de Comando Web 24/7 (localhost:8090)")
        btn_web.clicked.connect(self._open_web)
        h_head.addWidget(btn_web)

        # Solid vs Glass Toggle
        self.btn_solid = QPushButton("🎨" if not self.is_solid else "⬛")
        self.btn_solid.setObjectName("btn_icon")
        self.btn_solid.setFixedSize(22, 22)
        self.btn_solid.setToolTip("Alternar entre Modo Sólido (Área de Trabalho) e Vidro Translúcido")
        self.btn_solid.clicked.connect(self.toggle_solid)
        h_head.addWidget(self.btn_solid)

        # Pin Button
        self.btn_pin = QPushButton("📌" if self.is_pinned else "🖥️")
        self.btn_pin.setObjectName("btn_icon")
        if self.is_pinned:
            self.btn_pin.setStyleSheet("color: #38bdf8; background-color: rgba(56, 189, 248, 0.2);")
        else:
            self.btn_pin.setStyleSheet("color: #a855f7; background-color: rgba(168, 85, 247, 0.2);")
        self.btn_pin.setFixedSize(22, 22)
        self.btn_pin.clicked.connect(self.toggle_pin)
        h_head.addWidget(self.btn_pin)

        # Collapsible Toggle Button
        self.btn_collapse = QPushButton("▲" if not self.is_collapsed else "▼")
        self.btn_collapse.setObjectName("btn_icon")
        self.btn_collapse.setFixedSize(22, 22)
        self.btn_collapse.setToolTip("Minimizar para barra compacta" if not self.is_collapsed else "Expandir painel")
        self.btn_collapse.clicked.connect(self.toggle_collapse)
        h_head.addWidget(self.btn_collapse)

        # Minimize to Tray
        self.btn_min = QPushButton("─")
        self.btn_min.setObjectName("btn_icon")
        self.btn_min.setFixedSize(22, 22)
        self.btn_min.clicked.connect(self.hide)
        h_head.addWidget(self.btn_min)

        self.root_layout.addLayout(h_head)

        # Tabs Navigation (Specialized Workspaces: Dev, Eng, Escrita, Estudos)
        self.tabs = QTabWidget(self)
        self.tabs.setDocumentMode(True)

        self.tab_dev = DevProductivityWidget(self)
        self.tabs.addTab(self.tab_dev, "💻 Dev")

        self.tab_eng = EngHardwareWidget(self)
        self.tabs.addTab(self.tab_eng, "⚙️ Eng")

        self.tab_writing = WritingProductivityWidget(self)
        self.tabs.addTab(self.tab_writing, "✍️ Escrita")

        self.tab_study = StudyWidget(self)
        self.tabs.addTab(self.tab_study, "🎓 Estudos")

        if hasattr(self, 'active_tab'):
            self.tabs.setCurrentIndex(min(self.tabs.count() - 1, max(0, self.active_tab)))
        self.tabs.currentChanged.connect(lambda idx: self._save_settings())

        self.root_layout.addWidget(self.tabs, 1)

        # Bottom Bar: Task Manager, ~/develop & QSizeGrip
        self.bottom_bar_widget = QWidget()
        h_bottom = QHBoxLayout(self.bottom_bar_widget)
        h_bottom.setContentsMargins(2, 2, 2, 2)
        h_bottom.setSpacing(6)

        btn_taskmgr = QPushButton("⚡ Task Manager")
        btn_taskmgr.setStyleSheet("font-size: 10px; padding: 3px 6px;")
        btn_taskmgr.clicked.connect(self._launch_taskmgr)
        h_bottom.addWidget(btn_taskmgr)

        btn_develop = QPushButton("📂 ~/develop")
        btn_develop.setStyleSheet("font-size: 10px; padding: 3px 6px;")
        btn_develop.clicked.connect(self._open_develop_folder)
        h_bottom.addWidget(btn_develop)

        h_bottom.addStretch()

        self.size_grip = QSizeGrip(self)
        self.size_grip.setToolTip("Arraste para redimensionar largura e altura")
        h_bottom.addWidget(self.size_grip)

        self.root_layout.addWidget(self.bottom_bar_widget)

    def _check_vm_status(self):
        try:
            res = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", "windows-fusion360"],
                capture_output=True, text=True, timeout=1.5
            )
            is_running = res.stdout.strip() == "true"
            if is_running:
                self.btn_vm_badge.setText("🟢 Win11 (Fusion)")
                self.btn_vm_badge.setStyleSheet("font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 6px; background-color: rgba(34, 197, 94, 0.2); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.4);")
            else:
                self.btn_vm_badge.setText("⚫ Win11")
                self.btn_vm_badge.setStyleSheet("font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 6px; background-color: rgba(35, 40, 52, 0.7); color: #94a3b8; border: 1px solid rgba(255, 255, 255, 0.08);")
        except Exception:
            pass

    def _on_vm_badge_clicked(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #1a1e27; border: 1px solid rgba(255, 255, 255, 0.1); color: #f1f5f9; padding: 4px; }
            QMenu::item { padding: 6px 14px; border-radius: 4px; font-size: 11px; }
            QMenu::item:selected { background-color: #0284c7; }
        """)

        act_rdp = menu.addAction("🖥️ Conectar Tela RDP (Remmina)")
        act_rdp.triggered.connect(lambda: subprocess.Popen([VM_SCRIPT, "conectar"]))

        act_web = menu.addAction("🌐 Abrir no Navegador (Web VNC)")
        act_web.triggered.connect(lambda: subprocess.Popen([VM_SCRIPT, "web"]))

        menu.addSeparator()

        act_start = menu.addAction("⚡ Iniciar VM Windows")
        act_start.triggered.connect(lambda: subprocess.Popen([VM_SCRIPT, "start"]))

        act_stop = menu.addAction("🛑 Desligar VM (Liberar RAM)")
        act_stop.triggered.connect(lambda: subprocess.Popen([VM_SCRIPT, "stop"]))

        menu.exec(self.btn_vm_badge.mapToGlobal(QPoint(0, self.btn_vm_badge.height())))

    def _position_on_screen(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.right() - self.saved_width - 18
        y = screen.top() + 38
        self.move(x, y)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._save_settings()

    def _open_web(self):
        subprocess.Popen(["xdg-open", "http://localhost:8090"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _launch_taskmgr(self):
        taskmgr_path = "/home/usuario/taskmgr_linux/taskmgr"
        if os.path.exists(taskmgr_path):
            subprocess.Popen([taskmgr_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(["gnome-system-monitor"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _open_develop_folder(self):
        subprocess.Popen(["xdg-open", "/home/usuario/develop"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_position is not None:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_position = None


class HUDTrayIcon(QSystemTrayIcon):
    def __init__(self, hud_window: DesktopHUDWindow, app: QApplication):
        super().__init__()
        self.hud_window = hud_window
        self.app = app

        self.setIcon(self._create_tray_icon())
        self.setToolTip("Dev & Hardware Desktop HUD")

        menu = QMenu()
        menu.setStyleSheet("""
            QMenu { background-color: #12141a; border: 1px solid rgba(255, 255, 255, 0.1); color: #f1f5f9; padding: 4px; }
            QMenu::item { padding: 6px 14px; border-radius: 4px; font-size: 11px; }
            QMenu::item:selected { background-color: #0284c7; }
        """)

        act_show = menu.addAction("👁️ Mostrar / Ocultar HUD")
        act_show.triggered.connect(self._toggle_hud)

        act_web = menu.addAction("🌐 Abrir Painel Web (localhost:8090)")
        act_web.triggered.connect(lambda: subprocess.Popen(["xdg-open", "http://localhost:8090"]))

        act_dev = menu.addAction("📂 Abrir ~/develop")
        act_dev.triggered.connect(lambda: subprocess.Popen(["xdg-open", "/home/usuario/develop"]))

        menu.addSeparator()

        act_quit = menu.addAction("✕ Encerrar HUD")
        act_quit.triggered.connect(self.app.quit)

        self.setContextMenu(menu)
        self.activated.connect(self._on_activated)
        self.show()

    def _create_tray_icon(self) -> QIcon:
        pix = QPixmap(32, 32)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#0284c7"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(2, 2, 28, 28, 8, 8)
        painter.setPen(QColor("#ffffff"))
        font = QFont("Segoe UI", 13, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QRect(0, 0, 32, 32), Qt.AlignmentFlag.AlignCenter, "⚡")
        painter.end()
        return QIcon(pix)

    def _toggle_hud(self):
        if self.hud_window.isVisible():
            self.hud_window.hide()
        else:
            self.hud_window.show()
            self.hud_window.raise_()
            self.hud_window.activateWindow()
            QTimer.singleShot(100, self.hud_window._apply_x11_layer)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_hud()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Desktop HUD")
    app.setQuitOnLastWindowClosed(False)

    window = DesktopHUDWindow()
    window.show()

    tray = HUDTrayIcon(window, app)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
