"""
Multi-Environment & AI Training Nodes Monitor (modules/nodes_widget.py)
Delega toda coleta de telemetria e acesso remoto para ``core.nodes`` (sem subprocess direto).
"""

from typing import Dict, List, Optional

from core.nodes import (
    load_environments,
    trigger_remote_control,
    write_local_heartbeat,
)


def update_local_node_heartbeat(custom_ai_training: Optional[dict] = None) -> dict:
    """Compatibilidade: atualiza o heartbeat local usando ``core.nodes``."""
    return write_local_heartbeat(ai_override=custom_ai_training)


def load_all_nodes() -> List[Dict]:
    """Compatibilidade: carrega ambientes locais e registrados via ``core.nodes``."""
    return load_environments()


try:
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

    class EnvironmentsMonitorWidget(QFrame):
        """Widget colapsável de ambientes & rigs de treinamento IA."""

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setObjectName("card")
            self.setStyleSheet(
                "QFrame#card { background-color: rgba(20, 24, 32, 0.78); "
                "border: 1px solid rgba(56, 189, 248, 0.18); border-radius: 8px; padding: 5px; }"
            )
            self.is_expanded = True

            self.main_layout = QVBoxLayout(self)
            self.main_layout.setContentsMargins(6, 5, 6, 5)
            self.main_layout.setSpacing(4)

            h_head = QHBoxLayout()
            self.lbl_title = QLabel("🌐 ENVIRONMENTS & RIGS DE TREINO IA")
            self.lbl_title.setStyleSheet("font-size: 9px; font-weight: 800; color: #38bdf8;")
            h_head.addWidget(self.lbl_title)
            h_head.addStretch()

            self.btn_toggle = QPushButton("▲")
            self.btn_toggle.setObjectName("btn_icon")
            self.btn_toggle.setFixedSize(18, 18)
            self.btn_toggle.setToolTip("Recolher/Expandir Environments")
            self.btn_toggle.clicked.connect(self._toggle_expand)
            h_head.addWidget(self.btn_toggle)
            self.main_layout.addLayout(h_head)

            self.nodes_container = QWidget()
            self.nodes_layout = QVBoxLayout(self.nodes_container)
            self.nodes_layout.setContentsMargins(0, 0, 0, 0)
            self.nodes_layout.setSpacing(4)
            self.main_layout.addWidget(self.nodes_container)

            self.timer = QTimer(self)
            self.timer.timeout.connect(self.refresh_nodes)
            self.timer.start(20000)
            self.refresh_nodes()

        def _toggle_expand(self):
            self.is_expanded = not self.is_expanded
            self.nodes_container.setVisible(self.is_expanded)
            self.btn_toggle.setText("▲" if self.is_expanded else "▼")

        def refresh_nodes(self):
            while self.nodes_layout.count() > 0:
                item = self.nodes_layout.takeAt(0)
                w = item.widget()
                if w:
                    w.deleteLater()

            nodes = load_environments()
            online_count = sum(1 for n in nodes if n.get("online"))
            self.lbl_title.setText(f"🌐 ENVIRONMENTS & RIGS IA ({online_count}/{len(nodes)} ATIVOS)")

            for n in nodes:
                row = QFrame()
                row.setStyleSheet(
                    "background-color: rgba(15, 18, 25, 0.75); "
                    "border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 5px; padding: 3px 5px;"
                )
                v_row = QVBoxLayout(row)
                v_row.setContentsMargins(4, 3, 4, 3)
                v_row.setSpacing(2)

                h_top = QHBoxLayout()
                h_top.setSpacing(4)

                os_icon = "🪟" if n.get("platform") == "windows" else "🐧"
                status_dot = "🟢" if n.get("online") else "⚫"
                local_tag = " <span style='color:#38bdf8; font-size:8px;'>[ESTE PC]</span>" if n.get("is_local") else ""

                lbl_name = QLabel(f"{status_dot} {os_icon} <b>{n.get('display_name', n.get('hostname'))}</b>{local_tag}")
                lbl_name.setStyleSheet("font-size: 10px; color: #f1f5f9;")
                h_top.addWidget(lbl_name)
                h_top.addStretch()

                if n.get("no_telemetry"):
                    metrics_str = f"{n.get('role', 'Remoto')} · {n.get('ip', '')}"
                else:
                    cpu = n.get("cpu_percent", 0.0)
                    ram_u = n.get("ram_used_gb", 0.0)
                    ram_t = n.get("ram_total_gb", 0.0)
                    gpu = n.get("gpu", {})
                    metrics_str = f"CPU {cpu:.0f}% · RAM {ram_u:.1f}/{ram_t:.0f}G"
                    if gpu.get("available"):
                        vram_g = gpu.get("vram_used_mb", 0) / 1024.0
                        metrics_str += f" · 🎮 GPU {gpu.get('util_percent', 0)}% ({vram_g:.1f}G)"

                lbl_metrics = QLabel(metrics_str)
                lbl_metrics.setStyleSheet("font-size: 9px; color: #94a3b8;")
                h_top.addWidget(lbl_metrics)

                if not n.get("is_local"):
                    btn_rc = QPushButton("🔗 Remote")
                    btn_rc.setStyleSheet(
                        "background-color: rgba(168, 85, 247, 0.2); border: 1px solid rgba(168, 85, 247, 0.4); "
                        "color: #d8b4fe; font-size: 8px; font-weight: 700; padding: 1px 5px; border-radius: 3px;"
                    )
                    rc_type = n.get("remote_control", {}).get("type", "remote").upper()
                    btn_rc.setToolTip(f"Conectar via {rc_type} ({n.get('ip', '')})")
                    btn_rc.clicked.connect(lambda _, node_obj=n: trigger_remote_control(node_obj))
                    h_top.addWidget(btn_rc)

                v_row.addLayout(h_top)

                ai = n.get("ai_training", {})
                if ai.get("active"):
                    lbl_ai = QLabel(
                        f"🧠 <b>Treinando IA:</b> <span style='color:#4ade80;'>{ai.get('project', 'Run')}</span> "
                        f"— {ai.get('progress_hint', ai.get('command', ''))}"
                    )
                    lbl_ai.setStyleSheet("font-size: 9px; color: #bbf7d0;")
                    v_row.addWidget(lbl_ai)
                else:
                    dev_folder = n.get("develop_dir", "")
                    hint = ai.get("progress_hint", "")
                    sub_txt = f"📂 {dev_folder}" + (f" · {hint}" if hint else "")
                    lbl_sub = QLabel(sub_txt)
                    lbl_sub.setStyleSheet("font-size: 8px; color: #64748b;")
                    v_row.addWidget(lbl_sub)

                self.nodes_layout.addWidget(row)

except ImportError:
    pass
