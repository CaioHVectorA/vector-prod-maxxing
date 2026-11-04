#!/usr/bin/env python3
"""
Dev & Hardware Desktop HUD (Universal Cross-Platform Edition: Linux, Windows, macOS)
Features:
- SingleInstance lock (prevents duplicate HUD windows)
- Rotating logs & uncaught exception hook (safe under pythonw.exe)
- Background HeartbeatService & GitSyncManager (detached bot commits)
- Cross-platform window layering (wmctrl on Linux X11, Win32 SetWindowPos on Windows)
- Bidirectional AI-HUD communication protocol via QFileSystemWatcher
"""

import os
import sys

base_dir = os.path.dirname(os.path.realpath(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from PyQt6.QtCore import QFileSystemWatcher, QPoint, QRect, QTimer, Qt
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMenu,
    QPushButton,
    QSizeGrip,
    QSystemTrayIcon,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core import launchers, paths, proc
from core.agy_rule import install_rule
from core.git_sync import GitSyncManager
from core.logs import get_logger, setup_logging
from core.nodes import HeartbeatService, write_local_heartbeat
from core.osinfo import IS_LINUX, IS_VM_HOST, IS_WINDOWS, VM_SCRIPT
from core.settings import HUD_LOCK_PORT, WEB_PORT
from core.single_instance import SingleInstance
from core.storage import load_local_ui, save_local_ui
from core.workspace import discover_develop_dir
from modules.clock_widget import ClockWidget
from modules.dev_widget import DevProductivityWidget
from modules.eng_widget import EngHardwareWidget
from modules.study_widget import StudyWidget
from modules.writing_widget import WritingProductivityWidget
from styles import HUD_STYLESHEET

DEFAULT_WIDTH = 450
DEFAULT_HEIGHT = 760

log = get_logger("hud.main")


class DesktopHUDWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.is_pinned = True
        self.is_solid = False
        self.is_collapsed = False
        self.drag_position = None
        self.saved_height = DEFAULT_HEIGHT
        self.saved_width = DEFAULT_WIDTH

        paths.ensure_dirs()
        install_rule()

        self.heartbeat = HeartbeatService()
        self.heartbeat.start()

        self.git_sync = GitSyncManager(on_status=self._on_git_sync_status)

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

        if IS_VM_HOST:
            self.vm_timer = QTimer(self)
            self.vm_timer.timeout.connect(self._check_vm_status)
            self.vm_timer.start(5000)
            self._check_vm_status()

        self._setup_file_watcher()

    def _on_git_sync_status(self, success: bool, msg: str):
        if hasattr(self, "btn_sync"):
            self.btn_sync.setText(msg[:16])
            color = "#4ade80" if success else "#f87171"
            if "Sincronizando" in msg:
                color = "#38bdf8"
            self.btn_sync.setStyleSheet(f"font-size: 10px; padding: 3px 6px; color: {color};")
            self.btn_sync.setToolTip(f"Git Auto-Sync: {msg}")

    def _load_settings(self):
        self.saved_width = DEFAULT_WIDTH
        self.saved_height = DEFAULT_HEIGHT
        cfg = load_local_ui()
        self.is_solid = cfg.get("solid_background", False)
        self.is_pinned = cfg.get("is_pinned", True)
        self.is_collapsed = cfg.get("is_collapsed", False)
        self.active_tab = cfg.get("active_tab", 0)
        self.saved_width = max(360, min(950, cfg.get("window_width", DEFAULT_WIDTH)))
        self.saved_height = max(420, min(1150, cfg.get("window_height", DEFAULT_HEIGHT)))

    def _save_settings(self):
        cfg = {
            "solid_background": self.is_solid,
            "is_pinned": self.is_pinned,
            "is_collapsed": self.is_collapsed,
            "active_tab": self.tabs.currentIndex() if hasattr(self, "tabs") else 0,
            "window_width": self.width(),
        }
        if not self.is_collapsed:
            cfg["window_height"] = self.height()
        save_local_ui(cfg)

    def _setup_file_watcher(self):
        paths.ensure_dirs()
        self.watcher = QFileSystemWatcher(self)
        for path in (paths.DATA_FILE, paths.EVENTS_FILE):
            if not os.path.exists(path):
                try:
                    with open(path, "a", encoding="utf-8"):
                        pass
                except OSError:
                    pass
            if os.path.exists(path):
                self.watcher.addPath(path)
        self.watcher.fileChanged.connect(self._on_watched_file_changed)

    def _on_watched_file_changed(self, path: str):
        QTimer.singleShot(200, self._refresh_all_tabs)
        if hasattr(self, "git_sync"):
            self.git_sync.notify_data_changed()
        if os.path.exists(path) and path not in self.watcher.files():
            self.watcher.addPath(path)

    def _refresh_all_tabs(self):
        try:
            if hasattr(self, "tab_study"):
                self.tab_study.refresh_metrics()
            if hasattr(self, "tab_writing"):
                self.tab_writing.refresh()
            if hasattr(self, "tab_dev"):
                self.tab_dev.refresh_all()
        except Exception:
            pass

    def _update_window_flags(self):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
        if IS_WINDOWS and self.is_pinned:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def _apply_window_layer(self):
        if IS_LINUX and proc.which("wmctrl"):
            win_id = hex(int(self.winId()))
            proc.run(["wmctrl", "-i", "-r", win_id, "-b", "remove,below"], timeout=1.5)
            proc.run(["wmctrl", "-i", "-r", win_id, "-b", "add,skip_taskbar,skip_pager,sticky"], timeout=1.5)
            if self.is_pinned:
                proc.run(["wmctrl", "-i", "-r", win_id, "-b", "add,above"], timeout=1.5)
                self.raise_()
            else:
                proc.run(["wmctrl", "-i", "-r", win_id, "-b", "remove,above"], timeout=1.5)
                self.lower()
        elif IS_WINDOWS:
            try:
                import ctypes
                hwnd = int(self.winId())
                # HWND_TOPMOST = -1, HWND_NOTOPMOST = -2, SWP_NOMOVE|SWP_NOSIZE|SWP_NOACTIVATE = 0x0013
                insert_after = -1 if self.is_pinned else -2
                ctypes.windll.user32.SetWindowPos(hwnd, insert_after, 0, 0, 0, 0, 0x0013)
                if self.is_pinned:
                    self.raise_()
                else:
                    self.lower()
            except Exception:
                pass

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(150, self._apply_window_layer)

    def toggle_pin(self):
        self.is_pinned = not self.is_pinned
        self._apply_window_layer()
        if self.is_pinned:
            self.btn_pin.setText("📌")
            self.btn_pin.setToolTip("Fixado no Topo (clique para deixar na Área de Trabalho)")
            self.btn_pin.setStyleSheet("color: #38bdf8; background-color: rgba(56, 189, 248, 0.2);")
        else:
            self.btn_pin.setText("🖥️")
            self.btn_pin.setToolTip("Na Área de Trabalho (clique para fixar no topo)")
            self.btn_pin.setStyleSheet("color: #a855f7; background-color: rgba(168, 85, 247, 0.2);")
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

        h_head = QHBoxLayout()
        h_head.setContentsMargins(2, 0, 2, 0)
        h_head.setSpacing(6)

        self.clock_widget = ClockWidget(self)
        h_head.addWidget(self.clock_widget)

        self.btn_vm_badge = None
        if IS_VM_HOST:
            self.btn_vm_badge = QPushButton("⚫ Win11")
            self.btn_vm_badge.setStyleSheet(
                "font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 6px; "
                "background-color: rgba(35, 40, 52, 0.7); color: #94a3b8; border: 1px solid rgba(255, 255, 255, 0.08);"
            )
            self.btn_vm_badge.setToolTip("Status da VM Windows (Fusion 360)")
            self.btn_vm_badge.clicked.connect(self._on_vm_badge_clicked)
            h_head.addWidget(self.btn_vm_badge)

        h_head.addStretch()

        btn_web = QPushButton("🌐 Web")
        btn_web.setObjectName("btn_icon")
        btn_web.setToolTip(f"Abrir Centro de Comando Web 24/7 (localhost:{WEB_PORT})")
        btn_web.clicked.connect(self._open_web)
        h_head.addWidget(btn_web)

        self.btn_solid = QPushButton("🎨" if not self.is_solid else "⬛")
        self.btn_solid.setObjectName("btn_icon")
        self.btn_solid.setFixedSize(22, 22)
        self.btn_solid.setToolTip("Alternar entre Modo Sólido (Área de Trabalho) e Vidro Translúcido")
        self.btn_solid.clicked.connect(self.toggle_solid)
        h_head.addWidget(self.btn_solid)

        self.btn_pin = QPushButton("📌" if self.is_pinned else "🖥️")
        self.btn_pin.setObjectName("btn_icon")
        if self.is_pinned:
            self.btn_pin.setStyleSheet("color: #38bdf8; background-color: rgba(56, 189, 248, 0.2);")
        else:
            self.btn_pin.setStyleSheet("color: #a855f7; background-color: rgba(168, 85, 247, 0.2);")
        self.btn_pin.setFixedSize(22, 22)
        self.btn_pin.clicked.connect(self.toggle_pin)
        h_head.addWidget(self.btn_pin)

        self.btn_collapse = QPushButton("▲" if not self.is_collapsed else "▼")
        self.btn_collapse.setObjectName("btn_icon")
        self.btn_collapse.setFixedSize(22, 22)
        self.btn_collapse.setToolTip("Minimizar para barra compacta" if not self.is_collapsed else "Expandir painel")
        self.btn_collapse.clicked.connect(self.toggle_collapse)
        h_head.addWidget(self.btn_collapse)

        self.btn_min = QPushButton("─")
        self.btn_min.setObjectName("btn_icon")
        self.btn_min.setFixedSize(22, 22)
        self.btn_min.clicked.connect(self.hide)
        h_head.addWidget(self.btn_min)

        self.root_layout.addLayout(h_head)

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

        if hasattr(self, "active_tab"):
            self.tabs.setCurrentIndex(min(self.tabs.count() - 1, max(0, self.active_tab)))
        self.tabs.currentChanged.connect(lambda _idx: self._save_settings())

        self.root_layout.addWidget(self.tabs, 1)

        self.bottom_bar_widget = QWidget()
        h_bottom = QHBoxLayout(self.bottom_bar_widget)
        h_bottom.setContentsMargins(2, 2, 2, 2)
        h_bottom.setSpacing(6)

        btn_taskmgr = QPushButton("⚡ Task Manager")
        btn_taskmgr.setStyleSheet("font-size: 10px; padding: 3px 6px;")
        btn_taskmgr.clicked.connect(self._launch_taskmgr)
        h_bottom.addWidget(btn_taskmgr)

        dev_name = os.path.basename(discover_develop_dir())
        btn_develop = QPushButton(f"📂 {dev_name}")
        btn_develop.setStyleSheet("font-size: 10px; padding: 3px 6px;")
        btn_develop.clicked.connect(self._open_develop_folder)
        h_bottom.addWidget(btn_develop)

        self.btn_sync = QPushButton("☁️ Sync")
        self.btn_sync.setStyleSheet("font-size: 10px; padding: 3px 6px; color: #38bdf8;")
        self.btn_sync.setToolTip("Git Auto-Sync (clique para sincronizar agora)")
        self.btn_sync.clicked.connect(self.git_sync.sync_now_async)
        h_bottom.addWidget(self.btn_sync)

        h_bottom.addStretch()

        self.size_grip = QSizeGrip(self)
        self.size_grip.setToolTip("Arraste para redimensionar largura e altura")
        h_bottom.addWidget(self.size_grip)

        self.root_layout.addWidget(self.bottom_bar_widget)

    def _check_vm_status(self):
        if not IS_VM_HOST or not self.btn_vm_badge:
            return
        res = proc.run(["docker", "inspect", "-f", "{{.State.Running}}", "windows-fusion360"], timeout=1.5)
        is_running = res.stdout.strip() == "true"
        if is_running:
            self.btn_vm_badge.setText("🟢 Win11 (Fusion)")
            self.btn_vm_badge.setStyleSheet(
                "font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 6px; "
                "background-color: rgba(34, 197, 94, 0.2); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.4);"
            )
        else:
            self.btn_vm_badge.setText("⚫ Win11")
            self.btn_vm_badge.setStyleSheet(
                "font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 6px; "
                "background-color: rgba(35, 40, 52, 0.7); color: #94a3b8; border: 1px solid rgba(255, 255, 255, 0.08);"
            )

    def _on_vm_badge_clicked(self):
        if not IS_VM_HOST or not self.btn_vm_badge:
            return
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background-color: #1a1e27; border: 1px solid rgba(255, 255, 255, 0.1); color: #f1f5f9; padding: 4px; }"
            "QMenu::item { padding: 6px 14px; border-radius: 4px; font-size: 11px; }"
            "QMenu::item:selected { background-color: #0284c7; }"
        )

        act_rdp = menu.addAction("🖥️ Conectar Tela RDP (Remmina)")
        act_rdp.triggered.connect(lambda: proc.spawn([VM_SCRIPT, "conectar"]))

        act_web = menu.addAction("🌐 Abrir no Navegador (Web VNC)")
        act_web.triggered.connect(lambda: proc.spawn([VM_SCRIPT, "web"]))

        menu.addSeparator()

        act_start = menu.addAction("⚡ Iniciar VM Windows")
        act_start.triggered.connect(lambda: proc.spawn([VM_SCRIPT, "start"]))

        act_stop = menu.addAction("🛑 Desligar VM (Liberar RAM)")
        act_stop.triggered.connect(lambda: proc.spawn([VM_SCRIPT, "stop"]))

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
        launchers.open_path(f"http://localhost:{WEB_PORT}")

    def _launch_taskmgr(self):
        if IS_WINDOWS:
            proc.spawn(["taskmgr.exe"])
            return
        taskmgr_path = "/home/usuario/taskmgr_linux/taskmgr"
        if os.path.exists(taskmgr_path):
            proc.spawn([taskmgr_path])
        elif proc.which("gnome-system-monitor"):
            proc.spawn(["gnome-system-monitor"])

    def _open_develop_folder(self):
        launchers.open_path(discover_develop_dir())

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
        menu.setStyleSheet(
            "QMenu { background-color: #12141a; border: 1px solid rgba(255, 255, 255, 0.1); color: #f1f5f9; padding: 4px; }"
            "QMenu::item { padding: 6px 14px; border-radius: 4px; font-size: 11px; }"
            "QMenu::item:selected { background-color: #0284c7; }"
        )

        act_show = menu.addAction("👁️ Mostrar / Ocultar HUD")
        act_show.triggered.connect(self._toggle_hud)

        act_web = menu.addAction(f"🌐 Abrir Painel Web (localhost:{WEB_PORT})")
        act_web.triggered.connect(lambda: launchers.open_path(f"http://localhost:{WEB_PORT}"))

        act_dev = menu.addAction("📂 Abrir Pasta de Projetos")
        act_dev.triggered.connect(lambda: launchers.open_path(discover_develop_dir()))

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
            QTimer.singleShot(100, self.hud_window._apply_window_layer)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_hud()


def main():
    setup_logging("hud")

    if "--headless-node" in sys.argv:
        log.info("Iniciando modo Headless Node Daemon...")
        install_rule()
        write_local_heartbeat()
        sync_mgr = GitSyncManager()
        import time

        try:
            while True:
                time.sleep(30)
                write_local_heartbeat()
        except KeyboardInterrupt:
            sync_mgr.stop()
            log.info("Headless daemon finalizado.")
        sys.exit(0)

    instance_lock = SingleInstance(HUD_LOCK_PORT)
    if not instance_lock.acquire():
        log.info("Outra instância do Desktop HUD já está em execução. Encerrando.")
        sys.exit(0)

    app = QApplication(sys.argv)
    app.setApplicationName("Desktop HUD")
    app.setQuitOnLastWindowClosed(False)

    window = DesktopHUDWindow()
    window.show()

    _tray = HUDTrayIcon(window, app)

    exit_code = app.exec()
    instance_lock.release()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
