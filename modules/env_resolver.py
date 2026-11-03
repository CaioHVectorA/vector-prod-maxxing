"""
Environment & Cross-Platform Resolver for vector-prod-maxxing (Desktop HUD)
Handles:
- OS & Hostname detection (Linux vs Windows, Main Linux VM Host check)
- Dynamic auto-discovery of the primary code workspace ('develop' folder) by scoring .git and node_modules density
- Portable data/ directory vs machine-specific local_ui.json separation
- Cross-platform IDE, terminal, and file opener helpers
- Automatic installation of the Antigravity 2.0 Global Rule so the AI Chat naturally syncs with the HUD
"""

import os
import sys
import json
import socket
import shutil
import sqlite3
import platform
import subprocess
from pathlib import Path
from typing import Optional

IS_WINDOWS = sys.platform.startswith("win")
IS_LINUX = sys.platform.startswith("linux")
IS_MAC = sys.platform.startswith("darwin")

HOSTNAME = socket.gethostname().lower()
OS_LABEL = f"{platform.system()} ({platform.release()})"

# Root of the vector-prod-maxxing repository
REPO_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
PORTABLE_DATA_DIR = os.path.join(REPO_DIR, "data")
NODES_DIR = os.path.join(PORTABLE_DATA_DIR, "nodes")
QUESTOES_DIR = os.path.join(PORTABLE_DATA_DIR, "questoes")

# Machine-local config directory (ignored by git, stores monitor X/Y/size and cached develop path)
if IS_WINDOWS:
    LOCAL_CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "desktop-hud")
else:
    LOCAL_CONFIG_DIR = os.path.expanduser("~/.config/desktop-hud")

LOCAL_UI_PATH = os.path.join(LOCAL_CONFIG_DIR, "local_ui.json")

# Portable files (inside repo data/)
DATA_PATH = os.path.join(PORTABLE_DATA_DIR, "data.json")
EVENTS_FILE = os.path.join(PORTABLE_DATA_DIR, "events.jsonl")
PINNED_FILE = os.path.join(PORTABLE_DATA_DIR, "pinned_projects.json")

# VM Script (only exists on the main Linux workstation 'policorp')
VM_SCRIPT = "/home/usuario/windows-vm/windows.sh"
IS_MAIN_LINUX_VM_HOST = bool(IS_LINUX and (HOSTNAME == "policorp" or os.path.exists(VM_SCRIPT)))


def ensure_directories():
    os.makedirs(PORTABLE_DATA_DIR, exist_ok=True)
    os.makedirs(NODES_DIR, exist_ok=True)
    os.makedirs(QUESTOES_DIR, exist_ok=True)
    os.makedirs(LOCAL_CONFIG_DIR, exist_ok=True)


def load_local_ui() -> dict:
    ensure_directories()
    if os.path.exists(LOCAL_UI_PATH):
        try:
            with open(LOCAL_UI_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # Fallback: read from data.json settings if migrating
    if os.path.exists(DATA_PATH):
        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("settings", {})
        except Exception:
            pass
    return {}


def save_local_ui(updates: dict):
    ensure_directories()
    current = load_local_ui()
    current.update(updates)
    try:
        with open(LOCAL_UI_PATH, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def score_workspace_candidate(candidate_path: str) -> int:
    """
    Scores a candidate parent directory by counting immediate subdirectories
    that contain .git (+3), node_modules (+2), or project manifests (+1).
    """
    if not candidate_path or not os.path.isdir(candidate_path):
        return 0
    score = 0
    try:
        entries = os.scandir(candidate_path)
    except Exception:
        return 0

    count = 0
    for entry in entries:
        if count > 150:
            break
        if not entry.is_dir(follow_symlinks=False) or entry.name.startswith("."):
            continue
        count += 1
        sub = entry.path
        try:
            if os.path.isdir(os.path.join(sub, ".git")):
                score += 3
            if os.path.isdir(os.path.join(sub, "node_modules")):
                score += 2
            if (
                os.path.isfile(os.path.join(sub, "pyproject.toml"))
                or os.path.isfile(os.path.join(sub, "package.json"))
                or os.path.isfile(os.path.join(sub, ".hud.json"))
                or os.path.isfile(os.path.join(sub, "Cargo.toml"))
            ):
                score += 1
        except Exception:
            pass
    return score


def get_antigravity_db_path() -> str:
    return os.path.expanduser("~/.gemini/antigravity/conversation_summaries.db")


def get_antigravity_storage_path() -> str:
    if IS_WINDOWS:
        appdata = os.environ.get("APPDATA", os.path.expanduser("~/AppData/Roaming"))
        return os.path.join(appdata, "Antigravity IDE", "User", "globalStorage", "storage.json")
    elif IS_MAC:
        return os.path.expanduser("~/Library/Application Support/Antigravity IDE/User/globalStorage/storage.json")
    return os.path.expanduser("~/.config/Antigravity IDE/User/globalStorage/storage.json")


def discover_develop_dir(force_rescan: bool = False) -> str:
    """
    Dynamically discovers the user's primary development directory across Linux/Windows
    by evaluating .git and node_modules density across candidate folders and Antigravity DB.
    """
    local_cfg = load_local_ui()
    cached = local_cfg.get("develop_dir")
    if not force_rescan and cached and os.path.isdir(cached):
        return cached

    home = str(Path.home())
    candidates = set()

    # 1. Parent of the current repository itself (e.g., if repo was cloned inside ~/develop/vector-prod-maxxing)
    repo_parent = os.path.dirname(REPO_DIR)
    if os.path.isdir(repo_parent) and os.path.abspath(repo_parent) != os.path.abspath(home):
        candidates.add(repo_parent)

    # 2. Common developer folder names in Home
    common_names = [
        "develop", "Develop", "dev", "Dev", "projects", "Projects",
        "repos", "Repos", "workspace", "Workspace", "code", "Code",
        "source/repos", "Documents/GitHub", "Documents/projects", "Documents/develop"
    ]
    for name in common_names:
        p = os.path.join(home, name)
        if os.path.isdir(p):
            candidates.add(p)

    # 3. All top-level folders in Home (excluding hidden/system ones)
    skip_dirs = {
        "AppData", "Application Data", "Library", "Downloads", "Pictures",
        "Music", "Videos", "Public", "Templates", "Desktop", "Área de trabalho",
        "snap", "anaconda3", "miniconda3", "venv", ".venv", "node_modules"
    }
    try:
        for entry in os.scandir(home):
            if entry.is_dir(follow_symlinks=False) and not entry.name.startswith(".") and entry.name not in skip_dirs:
                candidates.add(entry.path)
    except Exception:
        pass

    # 4. Windows root drives (C:\, D:\, E:\)
    if IS_WINDOWS:
        for drive in ["C:\\", "D:\\", "E:\\"]:
            if os.path.isdir(drive):
                for name in ["develop", "dev", "projects", "repos", "workspace", "code"]:
                    p = os.path.join(drive, name)
                    if os.path.isdir(p):
                        candidates.add(p)

    # 5. Extract parent folders from Antigravity conversation_summaries.db
    ag_db = get_antigravity_db_path()
    if os.path.exists(ag_db):
        try:
            conn = sqlite3.connect(ag_db)
            c = conn.cursor()
            c.execute("SELECT workspace_uris FROM conversation_summaries LIMIT 100")
            for (uris_raw,) in c.fetchall():
                try:
                    uris = json.loads(uris_raw) if uris_raw else []
                except Exception:
                    uris = [uris_raw] if uris_raw else []
                for uri in uris:
                    if isinstance(uri, str) and uri.startswith("file://"):
                        wpath = uri.replace("file://", "")
                        if IS_WINDOWS and wpath.startswith("/") and len(wpath) > 2 and wpath[2] == ":":
                            wpath = wpath[1:]
                        parent = os.path.dirname(wpath)
                        if os.path.isdir(parent) and os.path.abspath(parent) != os.path.abspath(home):
                            candidates.add(parent)
            conn.close()
        except Exception:
            pass

    best_dir = os.path.join(home, "develop")
    best_score = -1

    for cand in candidates:
        sc = score_workspace_candidate(cand)
        if sc > best_score:
            best_score = sc
            best_dir = cand

    if best_score <= 0 and not os.path.isdir(best_dir):
        best_dir = home

    save_local_ui({"develop_dir": best_dir, "develop_score": best_score})
    return best_dir


def find_project_subdir(project_name: str) -> str:
    """Finds a specific project (like UVC, Pfisicas, mp3) inside the discovered develop dir."""
    dev_dir = discover_develop_dir()
    direct = os.path.join(dev_dir, project_name)
    if os.path.isdir(direct):
        return direct
    # Case-insensitive lookup inside dev_dir
    if os.path.isdir(dev_dir):
        target_lower = project_name.lower()
        try:
            for item in os.listdir(dev_dir):
                if item.lower() == target_lower:
                    full = os.path.join(dev_dir, item)
                    if os.path.isdir(full):
                        return full
        except Exception:
            pass
    return direct


def get_antigravity_ide_bin() -> Optional[str]:
    """Resolves the Antigravity IDE executable across Linux and Windows."""
    for cmd in ["antigravity-ide", "agy"]:
        which_path = shutil.which(cmd)
        if which_path:
            return which_path

    candidates = [
        os.path.expanduser("~/.local/bin/antigravity-ide"),
        "/usr/local/bin/antigravity-ide",
        "/usr/bin/antigravity-ide",
    ]
    if IS_WINDOWS:
        local_app = os.environ.get("LOCALAPPDATA", os.path.expanduser("~/AppData/Local"))
        candidates.extend([
            os.path.join(local_app, "Programs", "Antigravity IDE", "antigravity-ide.exe"),
            os.path.join(local_app, "Programs", "Antigravity", "antigravity.exe"),
            shutil.which("code") or ""
        ])

    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None


def open_file_or_url(target: str):
    """Opens a file, folder, or URL using the native OS handler."""
    try:
        if IS_WINDOWS:
            os.startfile(target)  # type: ignore[attr-defined]
        elif IS_MAC:
            subprocess.Popen(["open", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(["xdg-open", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def open_terminal_at(path: str):
    """Opens a native terminal window in the specified directory."""
    if not os.path.isdir(path):
        path = os.path.expanduser("~")
    try:
        if IS_WINDOWS:
            if shutil.which("wt.exe"):
                subprocess.Popen(["wt.exe", "-d", path])
            else:
                subprocess.Popen(f'start cmd.exe /K "cd /d {path}"', shell=True)
        elif IS_MAC:
            subprocess.Popen(["open", "-a", "Terminal", path])
        else:
            for term in [
                ["gnome-terminal", f"--working-directory={path}"],
                ["x-terminal-emulator", "--working-directory", path],
                ["konsole", "--workdir", path],
                ["xfce4-terminal", f"--working-directory={path}"],
            ]:
                if shutil.which(term[0]):
                    subprocess.Popen(term, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return
    except Exception:
        pass


def open_in_antigravity(path: str) -> bool:
    ide_bin = get_antigravity_ide_bin()
    if ide_bin and os.path.exists(ide_bin):
        try:
            subprocess.Popen([ide_bin, path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False
    return False


def install_antigravity_global_rule():
    """
    Ensures ~/.gemini/config/rules/vector_hud.md is installed and up to date on whatever
    PC runs the HUD, so Antigravity 2.0 chat sessions automatically know where the repo
    and hud_cli.py live on this machine.
    """
    try:
        rules_dir = os.path.expanduser("~/.gemini/config/rules")
        os.makedirs(rules_dir, exist_ok=True)
        rule_file = os.path.join(rules_dir, "vector_hud.md")
        hud_cli_path = os.path.join(REPO_DIR, "hud_cli.py")
        py_exec = sys.executable or "python3"

        content = f"""# Vector-Prod-Maxxing (Desktop HUD & Antigravity 2.0 Ecosystem Protocol)

You are connected to the user's **`vector-prod-maxxing`** Desktop HUD & Productivity Ecosystem on host `{HOSTNAME}` (`{OS_LABEL}`).

- **Repository Root**: `{REPO_DIR}`
- **Portable Data File**: `{DATA_PATH}`
- **Append-Only Events Ledger**: `{EVENTS_FILE}`
- **Nodes Telemetry Directory**: `{NODES_DIR}`
- **HUD CLI Helper**: `{hud_cli_path}`

## Automatic Chat-to-HUD Synchronization Rules

Whenever the user interacts with you in Antigravity 2.0 Chat about any of the following topics, you **MUST** automatically update the HUD data (either by calling `{py_exec} "{hud_cli_path}" ...` or by editing `{DATA_PATH}` / `{EVENTS_FILE}`) without waiting to be asked:

1. **College Studies (UFF — Cálculo III, Física II, Métodos Numéricos, Sistemas de Computação, Física Experimental II)**:
   - When the user solves questions, studies a topic, or finishes an exercise in chat:
     Run: `{py_exec} "{hud_cli_path}" log-study --subject <calculo3|fisica2|met_numericos|sis_computacao|fisica_exp2> --questions <N> --topic "<topic>"`
   - When the user mentions an exam date or grade change:
     Run: `{py_exec} "{hud_cli_path}" set-exam --subject <id> --exam <p1|p2|p3|vs|testes> --grade <val> --date <YYYY-MM-DD>`

2. **Creative Writing (UVC / Red Right Hand)**:
   - When drafting, editing, or planning chapters in UVC:
     Run: `{py_exec} "{hud_cli_path}" log-writing --words <N> --chapter "<name>"`

3. **AI Training / Remote Node Tasks**:
   - When starting or finishing an AI training run, RL simulation, or benchmark on this environment:
     - Start: `{py_exec} "{hud_cli_path}" ai-train --start --project "<project>" --info "<details>"`
     - Stop: `{py_exec} "{hud_cli_path}" ai-train --stop --info "<summary>"`

4. **Immediate UI & GitHub Sync**:
   - The Desktop HUD watches `{DATA_PATH}` and `{EVENTS_FILE}` via `QFileSystemWatcher` and updates its UI within 200ms.
   - Its `GitSyncDaemon` automatically commits and pushes changes in `data/` to GitHub (`CaioHVectorA/vector-prod-maxxing`), or you can trigger an immediate sync with `{py_exec} "{hud_cli_path}" sync`.
"""
        with open(rule_file, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception:
        pass
