"""
Glassmorphism Dark & Solid Desktop Stylesheet for Desktop HUD
"""

HUD_STYLESHEET = """
QWidget#hud_root {
    background-color: rgba(18, 20, 26, 0.90);
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-radius: 14px;
    color: #f1f5f9;
    font-family: "Segoe UI", "Segoe UI Variable Text", "Cantarell", "Ubuntu", sans-serif;
}

QWidget#hud_root_solid {
    background-color: #12141a;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 14px;
    color: #f1f5f9;
    font-family: "Segoe UI", "Segoe UI Variable Text", "Cantarell", "Ubuntu", sans-serif;
}

QFrame#card {
    background-color: rgba(28, 32, 42, 0.65);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 10px;
    padding: 8px;
}

QLabel {
    color: #f1f5f9;
}

QLabel#sec_title {
    font-size: 11px;
    font-weight: 700;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}

/* Clock */
QLabel#clock_time {
    font-size: 32px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: -0.5px;
}

QLabel#clock_date {
    font-size: 12px;
    font-weight: 500;
    color: #cbd5e1;
}

/* Tabs */
QTabWidget::pane {
    border: none;
    background: transparent;
    margin-top: 4px;
}

QTabBar::tab {
    background-color: rgba(25, 30, 42, 0.6);
    color: #94a3b8;
    font-weight: 600;
    font-size: 11px;
    padding: 5px 8px;
    border-radius: 6px;
    margin-right: 3px;
    border: 1px solid rgba(255, 255, 255, 0.04);
}

QTabBar::tab:selected {
    background-color: #0284c7;
    color: #ffffff;
    border-color: #38bdf8;
}

QTabBar::tab:hover:!selected {
    background-color: rgba(35, 42, 58, 0.8);
    color: #e2e8f0;
}

/* System telemetry */
QProgressBar {
    background-color: rgba(15, 17, 23, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 4px;
    height: 8px;
    text-align: center;
    color: transparent;
}

QProgressBar#cpu_bar::chunk {
    background-color: #38bdf8;
    border-radius: 3px;
}

QProgressBar#ram_bar::chunk {
    background-color: #818cf8;
    border-radius: 3px;
}

/* Buttons */
QPushButton {
    background-color: rgba(45, 52, 66, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    padding: 5px 10px;
    color: #e2e8f0;
    font-size: 11px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: rgba(60, 70, 88, 0.9);
    border-color: rgba(255, 255, 255, 0.18);
    color: #ffffff;
}

QPushButton:pressed {
    background-color: rgba(30, 35, 45, 0.9);
}

QPushButton#btn_action_accent {
    background-color: #0284c7;
    border: 1px solid #0369a1;
    color: #ffffff;
    font-weight: 600;
}

QPushButton#btn_action_accent:hover {
    background-color: #0ea5e9;
}

QPushButton#btn_icon {
    padding: 4px 6px;
    font-size: 11px;
    background-color: rgba(35, 40, 52, 0.7);
}

QPushButton#btn_icon:hover {
    background-color: rgba(56, 189, 248, 0.2);
    border-color: #38bdf8;
    color: #38bdf8;
}

QDoubleSpinBox, QSpinBox {
    background-color: rgba(20, 24, 32, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 4px;
    color: #f1f5f9;
    padding: 3px 6px;
    font-size: 11px;
    font-weight: 600;
}

QScrollArea {
    border: none;
    background: transparent;
}

QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 6px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: rgba(255, 255, 255, 0.15);
    min-height: 20px;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background: rgba(255, 255, 255, 0.30);
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QSizeGrip {
    width: 14px;
    height: 14px;
    background: transparent;
}
"""
