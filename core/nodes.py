"""Environments (máquinas) e telemetria do nó local.

Telemetria viva é sempre local (``data/nodes/<hostname>.json``, ignorado pelo git,
para não gerar commits a cada 30 s). Outras máquinas vêm do registro versionado
``data/environments.json`` e aparecem sem telemetria até haver um transporte
(ex.: consultar o servidor web do outro PC).
"""

import os
import re
import threading
from datetime import datetime
from typing import Dict, List, Optional

from core import launchers, paths, proc, sysinfo
from core.osinfo import HOSTNAME, IS_WINDOWS, OS_LABEL, IS_VM_HOST
from core.storage import read_json, write_json
from core.workspace import discover_develop_dir

HEARTBEAT_INTERVAL = 30.0
_SAFE_TARGET = re.compile(r"^[A-Za-z0-9_.@:\-\[\]]+$")


def _node_file() -> str:
    return os.path.join(paths.NODES_DIR, f"{HOSTNAME}.json")


def _default_role() -> str:
    if IS_VM_HOST:
        return "Workstation Principal (Linux)"
    return "Ambiente Windows" if IS_WINDOWS else "Node Linux / Treino IA"


def collect_local_node(ai_override: Optional[dict] = None, sample_interval: Optional[float] = None) -> dict:
    previous = read_json(_node_file(), {}) or {}
    used, total = sysinfo.memory_gb()
    ip = sysinfo.local_ip()

    if ai_override is not None:
        ai = ai_override
    elif previous.get("ai_training", {}).get("manual_override") and previous["ai_training"].get("active"):
        ai = previous["ai_training"]  # treino registrado manualmente continua até alguém parar
    else:
        ai = sysinfo.detect_ai_training()

    return {
        "hostname": HOSTNAME,
        "display_name": previous.get("display_name", HOSTNAME.capitalize()),
        "role": previous.get("role", _default_role()),
        "os": OS_LABEL,
        "platform": "windows" if IS_WINDOWS else "linux",
        "ip": ip,
        "last_seen": datetime.now().isoformat(timespec="seconds"),
        "develop_dir": discover_develop_dir(),
        "cpu_percent": sysinfo.cpu_percent(sample_interval),
        "ram_used_gb": used,
        "ram_total_gb": total,
        "gpu": sysinfo.gpu_info(),
        "ai_training": ai,
        "remote_control": previous.get("remote_control", {"type": "local", "target": ip}),
    }


def write_local_heartbeat(ai_override: Optional[dict] = None, sample_interval: Optional[float] = None) -> dict:
    node = collect_local_node(ai_override, sample_interval)
    try:
        write_json(_node_file(), node)
    except OSError:
        pass
    return node


class HeartbeatService:
    """Atualiza a telemetria local em background (nunca na thread da GUI)."""

    def __init__(self, interval: float = HEARTBEAT_INTERVAL):
        self._interval = interval
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._loop, name="heartbeat", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        while not self._stop.is_set():
            write_local_heartbeat()
            self._stop.wait(self._interval)


def load_environments() -> List[Dict]:
    """Máquina local (com telemetria) + ambientes registrados em ``data/environments.json``."""
    local = read_json(_node_file(), None) or write_local_heartbeat()
    local = {**local, "is_local": True, "online": True}

    registry = read_json(paths.ENVIRONMENTS_FILE, []) or []
    others = []
    for entry in registry:
        if not isinstance(entry, dict) or str(entry.get("hostname", "")).lower() == HOSTNAME:
            continue
        others.append({
            "display_name": entry.get("hostname", "?"),
            "role": "Ambiente registrado",
            "platform": "linux",
            "gpu": {"available": False},
            "ai_training": {"active": False},
            **entry,
            "is_local": False,
            "online": False,  # sem telemetria remota
            "no_telemetry": True,
        })
    return [local, *others]


def find_environment(hostname: str) -> Optional[Dict]:
    return next((e for e in load_environments() if e.get("hostname") == hostname), None)


def trigger_remote_control(node: dict) -> bool:
    """Abre o cliente de acesso remoto configurado para o ambiente."""
    rc = node.get("remote_control") or {}
    kind = str(rc.get("type", "ssh")).lower()
    target = str(rc.get("target") or node.get("ip") or "")

    if kind == "web":
        return target.startswith(("http://", "https://")) and launchers.open_path(target)
    if not _SAFE_TARGET.match(target) or target.startswith("-"):
        return False  # impede injeção de opções (ex.: -oProxyCommand=...)

    if kind == "ssh":
        return launchers.open_terminal_command(["ssh", "--", target])
    if kind == "rdp":
        if IS_WINDOWS:
            return proc.spawn(["mstsc", f"/v:{target}"])
        if proc.which("remmina"):
            return proc.spawn(["remmina", "-c", f"rdp://{target}"])
        return False
    if kind in ("rustdesk", "anydesk") and proc.which(kind):
        return proc.spawn([kind, "--connect", target] if kind == "rustdesk" else [kind, target])
    return False
