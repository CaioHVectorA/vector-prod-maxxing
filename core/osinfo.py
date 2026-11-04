"""Detecção de plataforma e identidade da máquina."""

import os
import platform as _platform
import socket
import sys
from pathlib import Path

IS_WINDOWS = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

HOSTNAME = socket.gethostname().lower()
OS_LABEL = f"{_platform.system()} {_platform.release()}"

# Script do container Docker com a VM Windows. Só existe na workstation Linux principal.
VM_SCRIPT = str(Path.home() / "windows-vm" / "windows.sh")
IS_VM_HOST = IS_LINUX and os.path.isfile(VM_SCRIPT)


def python_executable() -> str:
    """Python com console, adequado para rodar scripts filhos e ler a saída deles.

    ``pythonw.exe`` não tem stdout/stderr, então um filho iniciado com ele
    produz saída vazia. Trocamos pelo ``python.exe`` irmão.
    """
    exe = sys.executable or "python3"
    if IS_WINDOWS and os.path.basename(exe).lower() == "pythonw.exe":
        console = os.path.join(os.path.dirname(exe), "python.exe")
        if os.path.exists(console):
            return console
    return exe
