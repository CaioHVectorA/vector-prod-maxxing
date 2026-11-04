"""Shim de compatibilidade para scripts externos que importem ``modules.env_resolver``."""

from core.agy_rule import install_rule as install_antigravity_global_rule
from core.launchers import (
    find_ide as get_antigravity_ide_bin,
    open_in_ide as open_in_antigravity,
    open_path as open_file_or_url,
    open_terminal as open_terminal_at,
)
from core.osinfo import (
    HOSTNAME,
    IS_LINUX,
    IS_MAC,
    IS_VM_HOST as IS_MAIN_LINUX_VM_HOST,
    IS_WINDOWS,
    OS_LABEL,
    VM_SCRIPT,
)
from core.paths import (
    DATA_DIR,
    DATA_FILE as DATA_PATH,
    EVENTS_FILE,
    LOCAL_CONFIG_DIR,
    LOCAL_UI_FILE,
    NODES_DIR,
    PINNED_FILE,
    QUESTOES_DIR,
    REPO_DIR as REPO_ROOT,
    ensure_dirs as ensure_directories,
)
from core.storage import load_local_ui, save_local_ui
from core.workspace import (
    discover_develop_dir,
    find_project_subdir,
    uri_to_path,
)

__all__ = [
    "IS_WINDOWS",
    "IS_LINUX",
    "IS_MAC",
    "HOSTNAME",
    "OS_LABEL",
    "REPO_ROOT",
    "DATA_DIR",
    "DATA_PATH",
    "EVENTS_FILE",
    "PINNED_FILE",
    "QUESTOES_DIR",
    "NODES_DIR",
    "LOCAL_CONFIG_DIR",
    "LOCAL_UI_FILE",
    "VM_SCRIPT",
    "IS_MAIN_LINUX_VM_HOST",
    "ensure_directories",
    "load_local_ui",
    "save_local_ui",
    "uri_to_path",
    "discover_develop_dir",
    "find_project_subdir",
    "get_antigravity_ide_bin",
    "open_file_or_url",
    "open_terminal_at",
    "open_in_antigravity",
    "install_antigravity_global_rule",
]
