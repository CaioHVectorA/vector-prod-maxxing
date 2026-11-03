"""
Multi-Environment & AI Training Nodes Monitor (modules/nodes_widget.py)
Features:
- Local node heartbeat collector (writes data/nodes/<hostname>.json)
- Cross-platform CPU, RAM, NVIDIA GPU (nvidia-smi VRAM/Util/Temp) & AI Training process auto-detection
- Visual PyQt6 card showing all registered environments (Linux Host, Windows PC, Remote AI Training Rigs)
- 1-Click Remote Control launcher (SSH, RDP/Remmina, RustDesk, AnyDesk, Parsec, or Web URL)
"""

import os
import re
import json
import glob
import socket
import shutil
import subprocess
from datetime import datetime
from typing import Dict, List, Optional

from modules.env_resolver import (
    NODES_DIR, HOSTNAME, OS_LABEL, IS_WINDOWS, IS_LINUX,
    discover_develop_dir, open_file_or_url, open_terminal_at, ensure_directories
)


def _get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _get_cpu_ram_telemetry() -> tuple[float, float, float]:
    """Returns (cpu_percent, ram_used_gb, ram_total_gb) without external dependencies."""
    cpu_pct = 0.0
    ram_used = 0.0
    ram_total = 0.0

    if IS_LINUX:
        try:
            load1, _, _ = os.getloadavg()
            cores = os.cpu_count() or 1
            cpu_pct = round(min(100.0, (load1 / cores) * 100.0), 1)
        except Exception:
            pass
        try:
            with open("/proc/meminfo", "r") as f:
                mem = f.read()
            m_tot = re.search(r"MemTotal:\s+(\d+)", mem)
            m_avail = re.search(r"MemAvailable:\s+(\d+)", mem)
            if m_tot and m_avail:
                tot_kb = int(m_tot.group(1))
                avail_kb = int(m_avail.group(1))
                ram_total = round(tot_kb / 1048576, 1)
                ram_used = round((tot_kb - avail_kb) / 1048576, 1)
        except Exception:
            pass
    elif IS_WINDOWS:
        try:
            res = subprocess.run(
                ["wmic", "cpu", "get", "loadpercentage", "/value"],
                capture_output=True, text=True, timeout=1.5
            )
            m = re.search(r"LoadPercentage=(\d+)", res.stdout)
            if m:
                cpu_pct = float(m.group(1))
        except Exception:
            pass
        try:
            res = subprocess.run(
                ["wmic", "OS", "get", "FreePhysicalMemory,TotalVisibleMemorySize", "/value"],
                capture_output=True, text=True, timeout=1.5
            )
            m_free = re.search(r"FreePhysicalMemory=(\d+)", res.stdout)
            m_tot = re.search(r"TotalVisibleMemorySize=(\d+)", res.stdout)
            if m_free and m_tot:
                tot_kb = int(m_tot.group(1))
                free_kb = int(m_free.group(1))
                ram_total = round(tot_kb / 1048576, 1)
                ram_used = round((tot_kb - free_kb) / 1048576, 1)
        except Exception:
            pass

    return cpu_pct, ram_used, ram_total


def _get_gpu_telemetry() -> dict:
    """Queries nvidia-smi if available on Linux or Windows."""
    if not shutil.which("nvidia-smi"):
        return {"available": False}
    try:
        res = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                "--format=csv,noheader,nounits"
            ],
            capture_output=True, text=True, timeout=1.5
        )
        if res.returncode == 0 and res.stdout.strip():
            line = res.stdout.strip().splitlines()[0]
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 5:
                return {
                    "available": True,
                    "name": parts[0],
                    "util_percent": int(float(parts[1])),
                    "vram_used_mb": int(float(parts[2])),
                    "vram_total_mb": int(float(parts[3])),
                    "temp_c": int(float(parts[4]))
                }
    except Exception:
        pass
    return {"available": False}


def _detect_ai_training_process(existing_training: Optional[dict] = None) -> dict:
    """
    Auto-detects active Python AI/ML training scripts or preserves manually logged AI training state.
    """
    # If manually set active via hud_cli.py, preserve it unless overridden
    if existing_training and existing_training.get("manual_override") and existing_training.get("active"):
        return existing_training

    keywords = (
        "train", "ppo", "sac", "dqn", "rl_", "finetune", "fine_tune",
        "lora", "qlora", "ultralytics", "yolo", "torchrun", "accelerate", "deepspeed"
    )
    if IS_LINUX:
        try:
            res = subprocess.run(
                ["ps", "-eo", "pid,pcpu,comm,args", "--no-headers"],
                capture_output=True, text=True, timeout=1.2
            )
            for line in res.stdout.splitlines():
                lower = line.lower()
                if ("python" in lower or "uv " in lower or "torchrun" in lower) and "desktop-hud" not in lower:
                    for kw in keywords:
                        if kw in lower:
                            parts = line.strip().split(None, 3)
                            cmd_str = parts[3] if len(parts) >= 4 else line.strip()
                            return {
                                "active": True,
                                "manual_override": False,
                                "project": kw.upper(),
                                "command": cmd_str[:80],
                                "progress_hint": f"CPU {parts[1]}% (Auto-detectado)",
                                "started_at": datetime.now().isoformat(timespec="seconds")
                            }
        except Exception:
            pass
    return {
        "active": False,
        "manual_override": False,
        "project": "",
        "command": "",
        "progress_hint": ""
    }


def update_local_node_heartbeat(custom_ai_training: Optional[dict] = None) -> dict:
    """Updates data/nodes/<hostname>.json with current telemetry."""
    ensure_directories()
    node_file = os.path.join(NODES_DIR, f"{HOSTNAME}.json")

    existing = {}
    if os.path.exists(node_file):
        try:
            with open(node_file, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = {}

    cpu_pct, ram_used, ram_total = _get_cpu_ram_telemetry()
    gpu_info = _get_gpu_telemetry()

    if custom_ai_training is not None:
        ai_info = custom_ai_training
    else:
        ai_info = _detect_ai_training_process(existing.get("ai_training"))

    role_default = "Workstation Principal (Linux)" if HOSTNAME == "policorp" else (
        "Ambiente Windows" if IS_WINDOWS else "Node / AI Training Rig"
    )

    payload = {
        "hostname": HOSTNAME,
        "display_name": existing.get("display_name", f"{HOSTNAME.capitalize()}"),
        "role": existing.get("role", role_default),
        "os": OS_LABEL,
        "platform": "windows" if IS_WINDOWS else ("linux" if IS_LINUX else "other"),
        "ip": _get_local_ip(),
        "last_seen": datetime.now().isoformat(timespec="seconds"),
        "develop_dir": discover_develop_dir(),
        "cpu_percent": cpu_pct,
        "ram_used_gb": ram_used,
        "ram_total_gb": ram_total,
        "gpu": gpu_info,
        "ai_training": ai_info,
        "remote_control": existing.get("remote_control", {
            "type": "local" if HOSTNAME == "policorp" else ("rdp" if IS_WINDOWS else "ssh"),
            "target": f"{_get_local_ip()}"
        })
    }

    try:
        with open(node_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    return payload


def ensure_sample_remote_environments():
    """
    Seeds placeholder environment profiles if only 1 node exists, so the user immediately sees
    their multi-environment layout (Linux Host + Windows Env + AI Training Rig) and can edit or overwrite them
    as soon as they clone vector-prod-maxxing on those machines.
    """
    ensure_directories()
    existing_files = glob.glob(os.path.join(NODES_DIR, "*.json"))
    if len(existing_files) > 1:
        return

    samples = [
        {
            "hostname": "windows-workstation",
            "display_name": "Windows PC (Dev & CAD)",
            "role": "Ambiente Windows Nativo",
            "os": "Windows 11 Pro",
            "platform": "windows",
            "ip": "192.168.1.20",
            "last_seen": "",
            "develop_dir": "C:\\Users\\usuario\\develop",
            "cpu_percent": 0.0,
            "ram_used_gb": 0.0,
            "ram_total_gb": 32.0,
            "gpu": {"available": True, "name": "GPU Dedicada", "util_percent": 0, "vram_used_mb": 0, "vram_total_mb": 12288, "temp_c": 0},
            "ai_training": {"active": False, "project": "", "command": "", "progress_hint": "Aguardando sync..."},
            "remote_control": {"type": "rdp", "target": "192.168.1.20"}
        },
        {
            "hostname": "ai-rig-01",
            "display_name": "AI Training Rig #1 (Remote)",
            "role": "Treinamento IA & RL",
            "os": "Linux / Windows GPU Node",
            "platform": "linux",
            "ip": "192.168.1.50",
            "last_seen": "",
            "develop_dir": "~/develop",
            "cpu_percent": 0.0,
            "ram_used_gb": 0.0,
            "ram_total_gb": 64.0,
            "gpu": {"available": True, "name": "NVIDIA CUDA Node", "util_percent": 0, "vram_used_mb": 0, "vram_total_mb": 24576, "temp_c": 0},
            "ai_training": {"active": False, "project": "", "command": "", "progress_hint": "Clone vector-prod-maxxing na máquina"},
            "remote_control": {"type": "ssh", "target": "usuario@192.168.1.50"}
        }
    ]
    for s in samples:
        p = os.path.join(NODES_DIR, f"{s['hostname']}.json")
        if not os.path.exists(p):
            try:
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(s, f, indent=2, ensure_ascii=False)
            except Exception:
                pass


def load_all_nodes() -> List[Dict]:
    ensure_directories()
    ensure_sample_remote_environments()
    update_local_node_heartbeat()

    nodes = []
    now = datetime.now()
    for path in sorted(glob.glob(os.path.join(NODES_DIR, "*.json"))):
        try:
            with open(path, "r", encoding="utf-8") as f:
                n = json.load(f)
            is_local = (n.get("hostname", "").lower() == HOSTNAME)
            n["is_local"] = is_local

            last_seen_str = n.get("last_seen", "")
            online = is_local
            if last_seen_str and not is_local:
                try:
                    dt = datetime.fromisoformat(last_seen_str)
                    online = (now - dt).total_seconds() < 600  # 10 min window
                except Exception:
                    online = False
            n["online"] = online
            nodes.append(n)
        except Exception:
            pass

    # Sort local machine first, then online machines, then by display_name
    nodes.sort(key=lambda x: (x.get("is_local", False), x.get("online", False), x.get("display_name", "")), reverse=True)
    return nodes


def trigger_remote_control(node: dict):
    """Launches the configured remote control client for a remote node."""
    rc = node.get("remote_control", {})
    rc_type = rc.get("type", "ssh").lower()
    target = rc.get("target", node.get("ip", ""))

    if rc_type == "ssh":
        if IS_WINDOWS:
            subprocess.Popen(f'start cmd.exe /K "ssh {target}"', shell=True)
        else:
            for term in ["gnome-terminal", "x-terminal-emulator", "konsole"]:
                if shutil.which(term):
                    if term == "gnome-terminal":
                        subprocess.Popen([term, "--", "ssh", target])
                    else:
                        subprocess.Popen([term, "-e", f"ssh {target}"])
                    return
    elif rc_type == "rdp":
        if IS_WINDOWS:
            subprocess.Popen(["mstsc", f"/v:{target}"])
        elif shutil.which("remmina"):
            subprocess.Popen(["remmina", "-c", f"rdp://{target}"])
        else:
            open_file_or_url(f"rdp://{target}")
    elif rc_type == "rustdesk" and shutil.which("rustdesk"):
        subprocess.Popen(["rustdesk", "--connect", target])
    elif rc_type == "anydesk" and shutil.which("anydesk"):
        subprocess.Popen(["anydesk", target])
    elif rc_type == "web" or target.startswith("http"):
        open_file_or_url(target)
    else:
        open_terminal_at(os.path.expanduser("~"))


# Optional PyQt6 Widget (only imported when running GUI)
try:
    from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget
    from PyQt6.QtCore import QTimer

    class EnvironmentsMonitorWidget(QFrame):
        """Compact collapsible multi-environment & AI training rig telemetry widget."""
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

            # Header
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

            nodes = load_all_nodes()
            online_count = sum(1 for n in nodes if n.get("online"))
            self.lbl_title.setText(f"🌐 ENVIRONMENTS & RIGS IA ({online_count}/{len(nodes)} ONLINE)")

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

                # Metrics summary
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
                    btn_rc.setToolTip(f"Conectar via {n.get('remote_control', {}).get('type', 'remote').upper()} ({n.get('ip', '')})")
                    btn_rc.clicked.connect(lambda _, node_obj=n: trigger_remote_control(node_obj))
                    h_top.addWidget(btn_rc)

                v_row.addLayout(h_top)

                # AI Training active badge or workspace info
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
