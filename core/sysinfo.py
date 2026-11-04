"""Telemetria da máquina local (CPU, RAM, GPU NVIDIA, treinos de IA) sem abrir consoles.

``psutil`` cobre Windows/Linux/Mac sem subprocess. O único processo externo é
``nvidia-smi``, rodado oculto e com cache, e só se o executável existir.
"""

import socket
import threading
import time
from typing import Optional, Tuple

from core import proc
from core.osinfo import IS_LINUX, IS_WINDOWS

try:
    import psutil
except ImportError:  # dependência opcional: sem ela, retornamos zeros em vez de quebrar
    psutil = None

_GPU_TTL = 20.0
_gpu_cache: Tuple[float, dict] = (0.0, {"available": False})
_gpu_lock = threading.Lock()

if psutil:
    psutil.cpu_percent(interval=None)  # primeira chamada só inicializa o contador

_TRAIN_KEYWORDS = (
    "train", "ppo", "dqn", "sac.py", "finetune", "fine_tune", "lora", "qlora",
    "ultralytics", "yolo", "torchrun", "accelerate", "deepspeed",
)
_PYTHON_NAMES = ("python", "pythonw", "uv", "torchrun", "accelerate", "deepspeed")


def cpu_percent(sample_interval: Optional[float] = None) -> float:
    if not psutil:
        return 0.0
    return round(psutil.cpu_percent(interval=sample_interval), 1)


def memory_gb() -> Tuple[float, float]:
    """Retorna (usada, total) em GB."""
    if psutil:
        vm = psutil.virtual_memory()
        return round((vm.total - vm.available) / 2**30, 1), round(vm.total / 2**30, 1)
    if IS_LINUX:
        try:
            info = {}
            with open("/proc/meminfo") as f:
                for line in f:
                    key, _, rest = line.partition(":")
                    info[key] = int(rest.split()[0])
            total, avail = info["MemTotal"], info["MemAvailable"]
            return round((total - avail) / 2**20, 1), round(total / 2**20, 1)
        except (OSError, KeyError, ValueError):
            pass
    return 0.0, 0.0


def local_ip() -> str:
    """IP de saída principal. O connect UDP não envia pacotes."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(0.5)
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def gpu_info() -> dict:
    global _gpu_cache
    with _gpu_lock:
        stamp, cached = _gpu_cache
        if time.monotonic() - stamp < _GPU_TTL:
            return cached

    info = {"available": False}
    if proc.which("nvidia-smi"):
        r = proc.run(
            ["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
             "--format=csv,noheader,nounits"],
            timeout=5,
        )
        if r.ok and r.stdout.strip():
            parts = [p.strip() for p in r.stdout.strip().splitlines()[0].split(",")]
            if len(parts) >= 5:
                try:
                    info = {
                        "available": True, "name": parts[0],
                        "util_percent": int(float(parts[1])),
                        "vram_used_mb": int(float(parts[2])),
                        "vram_total_mb": int(float(parts[3])),
                        "temp_c": int(float(parts[4])),
                    }
                except ValueError:
                    pass
    with _gpu_lock:
        _gpu_cache = (time.monotonic(), info)
    return info


def detect_ai_training() -> dict:
    """Procura um processo Python que pareça treino de modelo (heurística por nome/argumentos)."""
    idle = {"active": False, "manual_override": False, "project": "", "command": "", "progress_hint": ""}
    if not psutil:
        return idle
    me = psutil.Process().pid
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if p.info["pid"] == me:
                continue
            name = (p.info["name"] or "").lower()
            if not any(name.startswith(n) for n in _PYTHON_NAMES):
                continue
            cmd = " ".join(p.info["cmdline"] or []).lower()
            if "desktop-hud" in cmd or "vector-prod" in cmd or "hud_cli" in cmd:
                continue
            for kw in _TRAIN_KEYWORDS:
                if kw in cmd:
                    return {
                        "active": True, "manual_override": False, "project": kw.strip("._").upper(),
                        "command": " ".join(p.info["cmdline"] or [])[:80],
                        "progress_hint": "Auto-detectado",
                    }
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return idle
