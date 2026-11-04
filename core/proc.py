"""Único ponto de criação de processos do HUD.

Por que isso existe: o HUD roda no Windows via ``pythonw.exe`` (sem console).
Quando um processo GUI cria um filho *console* (git, nvidia-smi, python...) sem
``CREATE_NO_WINDOW``, o Windows abre uma janela de terminal para ele. Com timers
disparando dezenas de comandos, o resultado eram terminais piscando sem parar.

Todas as funções aqui:
  * escondem a janela no Windows;
  * fecham o stdin (``pythonw`` não tem stdin válido, o que quebra ``subprocess``);
  * decodificam como UTF-8 (o padrão cp1252 do Windows estoura com a saída do git);
  * nunca lançam exceção: falhas viram ``CmdResult`` com ``returncode != 0``.
"""

import shutil
import subprocess
from dataclasses import dataclass
from typing import Mapping, Optional, Sequence

from core.osinfo import IS_WINDOWS

# Flags do Win32 (definidas à mão para o módulo importar também em Linux/Mac).
_CREATE_NEW_CONSOLE = 0x00000010
_CREATE_NEW_PROCESS_GROUP = 0x00000200
_CREATE_NO_WINDOW = 0x08000000

Command = Sequence[object]


@dataclass(frozen=True)
class CmdResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    @property
    def output(self) -> str:
        """stdout, ou stderr quando stdout está vazio (conveniente para mensagens)."""
        return self.stdout or self.stderr


def _argv(cmd: Command) -> list:
    return [str(c) for c in cmd]


def _hidden_window_kwargs() -> dict:
    if not IS_WINDOWS:
        return {}
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = subprocess.SW_HIDE
    return {"creationflags": _CREATE_NO_WINDOW, "startupinfo": startup}


def which(name: str) -> Optional[str]:
    return shutil.which(name)


def run(
    cmd: Command,
    *,
    timeout: float = 5.0,
    cwd: Optional[str] = None,
    env: Optional[Mapping[str, str]] = None,
    input_text: Optional[str] = None,
) -> CmdResult:
    """Executa e espera. Nunca abre janela e nunca lança exceção."""
    kwargs = _hidden_window_kwargs()
    if input_text is None:
        kwargs["stdin"] = subprocess.DEVNULL
    try:
        cp = subprocess.run(
            _argv(cmd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=cwd,
            env=env,
            input=input_text,
            **kwargs,
        )
        return CmdResult(cp.returncode, cp.stdout or "", cp.stderr or "")
    except subprocess.TimeoutExpired as e:
        out = e.stdout if isinstance(e.stdout, str) else ""
        return CmdResult(124, out, "", timed_out=True, error=f"timeout após {timeout}s")
    except FileNotFoundError as e:
        return CmdResult(127, error=f"comando não encontrado: {e.filename or cmd[0]}")
    except OSError as e:
        return CmdResult(126, error=str(e))


def popen_piped(
    cmd: Command,
    *,
    cwd: Optional[str] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Optional[subprocess.Popen]:
    """Inicia um processo com stdout+stderr combinados num pipe de texto.

    Para saídas longas com progresso (esptool, avrdude). Retorna ``None`` se o
    executável não existir.
    """
    try:
        return subprocess.Popen(
            _argv(cmd),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            cwd=cwd,
            env=env,
            **_hidden_window_kwargs(),
        )
    except OSError:
        return None


def spawn(
    cmd: Command,
    *,
    cwd: Optional[str] = None,
    env: Optional[Mapping[str, str]] = None,
    new_console: bool = False,
) -> bool:
    """Dispara e esquece (editores, terminais, scripts de longa duração).

    ``new_console=True`` é para abrir um terminal que o usuário vai usar: aí a
    janela é desejada e as saídas padrão não são redirecionadas.
    """
    kwargs: dict = {"cwd": cwd, "env": env}
    if IS_WINDOWS:
        flags = _CREATE_NEW_PROCESS_GROUP
        flags |= _CREATE_NEW_CONSOLE if new_console else _CREATE_NO_WINDOW
        kwargs["creationflags"] = flags
    else:
        kwargs["start_new_session"] = True
    if not new_console:
        kwargs.update(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        subprocess.Popen(_argv(cmd), **kwargs)
        return True
    except OSError:
        return False
