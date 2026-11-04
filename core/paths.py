"""Caminhos do projeto.

Dados portáteis vivem em ``data/`` (versionados). Estado específico da máquina
(posição da janela, cache de pasta de projetos, logs) vive fora do repositório.
Todas as constantes são ``str`` para funcionar com ``os.path`` e Qt sem conversões.
"""

import os
from pathlib import Path

from core.osinfo import IS_MAC, IS_WINDOWS

REPO_DIR = str(Path(__file__).resolve().parent.parent)
WEB_DIR = os.path.join(REPO_DIR, "web")
FIRMWARES_DIR = os.path.join(REPO_DIR, "firmwares")

DATA_DIR = os.path.join(REPO_DIR, "data")
DATA_FILE = os.path.join(DATA_DIR, "data.json")
EVENTS_FILE = os.path.join(DATA_DIR, "events.jsonl")
PINNED_FILE = os.path.join(DATA_DIR, "pinned_projects.json")
ENVIRONMENTS_FILE = os.path.join(DATA_DIR, "environments.json")
QUESTOES_DIR = os.path.join(DATA_DIR, "questoes")
NODES_DIR = os.path.join(DATA_DIR, "nodes")  # telemetria local; ignorada pelo git


def _local_config_dir() -> str:
    if IS_WINDOWS:
        base = os.environ.get("APPDATA") or str(Path.home())
    elif IS_MAC:
        base = str(Path.home() / "Library" / "Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return os.path.join(base, "desktop-hud")


LOCAL_CONFIG_DIR = _local_config_dir()
LOCAL_UI_FILE = os.path.join(LOCAL_CONFIG_DIR, "local_ui.json")
FOCUS_STATE_FILE = os.path.join(LOCAL_CONFIG_DIR, "focus_state.json")
PAC_FILE = os.path.join(LOCAL_CONFIG_DIR, "focus.pac")
LOG_DIR = os.path.join(LOCAL_CONFIG_DIR, "logs")

CALC_DIR = os.path.join(str(Path.home()), "Downloads", "calc")


def ensure_dirs() -> None:
    for d in (DATA_DIR, NODES_DIR, QUESTOES_DIR, LOCAL_CONFIG_DIR, LOG_DIR):
        os.makedirs(d, exist_ok=True)
