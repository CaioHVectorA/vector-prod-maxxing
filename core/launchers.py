"""Abrir arquivos, URLs, terminais e a IDE de forma portátil."""

import os
import shutil
import webbrowser
from functools import lru_cache
from pathlib import Path
from typing import Optional

from core import proc
from core.osinfo import IS_LINUX, IS_MAC, IS_WINDOWS


def open_path(target: str) -> bool:
    """Abre arquivo, pasta ou URL com o programa padrão do sistema."""
    if target.startswith(("http://", "https://")):
        return webbrowser.open(target)
    try:
        if IS_WINDOWS:
            os.startfile(target)  # type: ignore[attr-defined]  # não cria processo nem janela
            return True
        return proc.spawn(["open" if IS_MAC else "xdg-open", target])
    except OSError:
        return False


@lru_cache(maxsize=1)
def find_ide() -> Optional[str]:
    """Antigravity IDE, com fallback para VS Code."""
    for cmd in ("antigravity-ide", "agy", "antigravity"):
        found = shutil.which(cmd)
        if found:
            return found
    home = Path.home()
    candidates = [home / ".local" / "bin" / "antigravity-ide", Path("/usr/local/bin/antigravity-ide")]
    if IS_WINDOWS:
        local = Path(os.environ.get("LOCALAPPDATA") or home / "AppData" / "Local")
        candidates += [
            local / "Programs" / "Antigravity IDE" / "Antigravity IDE.exe",
            local / "Programs" / "Antigravity" / "Antigravity.exe",
        ]
    for c in candidates:
        if c.exists():
            return str(c)
    return shutil.which("code")


def open_in_ide(path: str) -> bool:
    ide = find_ide()
    return bool(ide) and proc.spawn([ide, path])


def open_terminal(path: str) -> bool:
    """Abre um terminal interativo em ``path`` (aqui a janela é desejada)."""
    cwd = path if os.path.isdir(path) else str(Path.home())
    if IS_WINDOWS:
        if shutil.which("wt.exe"):
            return proc.spawn(["wt.exe", "-d", cwd])
        return proc.spawn(["cmd.exe", "/K"], cwd=cwd, new_console=True)
    if IS_MAC:
        return proc.spawn(["open", "-a", "Terminal", cwd])
    for argv in (
        ["gnome-terminal", f"--working-directory={cwd}"],
        ["x-terminal-emulator", "--working-directory", cwd],
        ["konsole", "--workdir", cwd],
        ["xfce4-terminal", f"--working-directory={cwd}"],
    ):
        if shutil.which(argv[0]):
            return proc.spawn(argv, cwd=cwd)
    return False


def open_terminal_command(argv: list) -> bool:
    """Abre um terminal executando ``argv`` (ex.: ssh). Não passa por shell."""
    if IS_WINDOWS:
        if shutil.which("wt.exe"):
            return proc.spawn(["wt.exe", *argv])
        return proc.spawn(["cmd.exe", "/K", *argv], new_console=True)
    if IS_LINUX:
        for term, sep in (("gnome-terminal", "--"), ("konsole", "-e"), ("xfce4-terminal", "-x"), ("x-terminal-emulator", "-e")):
            if shutil.which(term):
                return proc.spawn([term, sep, *argv])
    return False


def notify(title: str, message: str) -> bool:
    """Notificação nativa quando disponível. No Windows a UI usa a bandeja do Qt."""
    if IS_LINUX and shutil.which("notify-send"):
        return proc.run(["notify-send", title, message], timeout=3).ok
    if IS_MAC:
        clean = lambda s: s.replace('"', "'").replace("\\", "")  # noqa: E731 - evita quebrar o AppleScript
        script = f'display notification "{clean(message)}" with title "{clean(title)}"'
        return proc.run(["osascript", "-e", script], timeout=3).ok
    return False
