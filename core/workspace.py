"""Descoberta da pasta de projetos e dos workspaces do Antigravity.

A pasta onde o usuário guarda os repositórios pode ter qualquer nome em cada
máquina. Elegemos a candidata com mais subpastas que são repositórios
(``.git``) ou projetos Node (``node_modules``), e guardamos em ``local_ui.json``.
"""

import json
import os
import sqlite3
import time
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

from core import paths
from core.osinfo import IS_MAC, IS_WINDOWS
from core.storage import load_local_ui, read_json, save_local_ui

# Pastas que nunca são "a pasta de projetos" e podem ser lentas/caras de varrer
# (OneDrive baixa arquivos sob demanda no Windows).
_SKIP_NAMES = {
    "appdata", "application data", "library", "downloads", "pictures", "music", "videos",
    "public", "templates", "desktop", "área de trabalho", "snap", "anaconda3", "miniconda3",
    "node_modules", "venv", "windows-vm", "windows",
}
_COMMON_NAMES = (
    "develop", "dev", "projects", "repos", "workspace", "code", "src",
    "source/repos", "Documents/GitHub", "Documents/projects", "Documents/develop",
)
_SCAN_BUDGET_SECONDS = 4.0
_MAX_SUBDIRS_PER_CANDIDATE = 200


def uri_to_path(uri: str) -> Optional[str]:
    """``file:///C:/x%20y`` -> ``C:\\x y`` (Windows) e ``file:///home/x`` -> ``/home/x``."""
    if not isinstance(uri, str) or not uri.startswith("file:"):
        return None
    parsed = urlparse(uri)
    path = url2pathname(unquote(parsed.path))
    if IS_WINDOWS and parsed.netloc:  # UNC: file://server/share
        path = f"\\\\{parsed.netloc}{path}"
    return path or None


# --- Antigravity --------------------------------------------------------------

def antigravity_db_path() -> str:
    return str(Path.home() / ".gemini" / "antigravity" / "conversation_summaries.db")


def antigravity_storage_path() -> str:
    if IS_WINDOWS:
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    elif IS_MAC:
        base = str(Path.home() / "Library" / "Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return os.path.join(base, "Antigravity IDE", "User", "globalStorage", "storage.json")


def antigravity_workspaces() -> Dict[str, dict]:
    """Workspaces conhecidos do Antigravity, indexados por nome da pasta.

    Une o banco de conversas (com contagem de sessões) e o ``storage.json`` da IDE.
    """
    home = os.path.normcase(str(Path.home()))
    found: Dict[str, dict] = {}

    def usable(path: Optional[str]) -> bool:
        return bool(path) and os.path.isdir(path) and os.path.normcase(path) != home

    db = antigravity_db_path()
    if os.path.exists(db):
        try:
            conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=2)
            try:
                rows = conn.execute(
                    "SELECT workspace_uris, title, last_modified_time, step_count "
                    "FROM conversation_summaries ORDER BY last_modified_time DESC"
                ).fetchall()
            finally:
                conn.close()
        except sqlite3.Error:
            rows = []
        for uris_raw, title, last_mod, steps in rows:
            try:
                uris = json.loads(uris_raw) if uris_raw else []
            except ValueError:
                uris = [uris_raw] if uris_raw else []
            for uri in uris:
                path = uri_to_path(uri)
                if not usable(path):
                    continue
                name = os.path.basename(path.rstrip("/\\"))
                entry = found.setdefault(name, {
                    "name": name, "path": path, "last_activity": last_mod or "",
                    "last_title": title or "", "convo_count": 0, "total_steps": 0,
                })
                entry["convo_count"] += 1
                entry["total_steps"] += steps or 0

    storage = read_json(antigravity_storage_path(), {}) or {}
    for uri in (storage.get("profileAssociations", {}) or {}).get("workspaces", {}) or {}:
        path = uri_to_path(uri)
        if usable(path):
            name = os.path.basename(path.rstrip("/\\"))
            found.setdefault(name, {
                "name": name, "path": path, "last_activity": "", "last_title": "",
                "convo_count": 0, "total_steps": 0,
            })
    return found


# --- Descoberta da pasta de projetos -----------------------------------------

def _is_repo(path: str) -> bool:
    return os.path.exists(os.path.join(path, ".git"))  # .git também pode ser arquivo (worktree)


def score_workspace_candidate(candidate: str, deadline: float = float("inf")) -> int:
    """+3 por subpasta com ``.git``, +2 com ``node_modules``, +1 com manifesto de projeto."""
    score = 0
    try:
        entries = list(os.scandir(candidate))
    except OSError:
        return 0
    for entry in entries[:_MAX_SUBDIRS_PER_CANDIDATE]:
        if time.monotonic() > deadline:
            break
        try:
            if not entry.is_dir(follow_symlinks=False) or entry.name.startswith("."):
                continue
        except OSError:
            continue
        sub = entry.path
        if _is_repo(sub):
            score += 3
        if os.path.isdir(os.path.join(sub, "node_modules")):
            score += 2
        if any(os.path.isfile(os.path.join(sub, m)) for m in ("pyproject.toml", "package.json", "Cargo.toml", ".hud.json")):
            score += 1
    return score


def _candidate_dirs() -> Iterable[str]:
    home = Path.home()
    seen = set()

    def add(p) -> Optional[str]:
        p = str(p)
        key = os.path.normcase(os.path.abspath(p))
        if key in seen or not os.path.isdir(p) or key == os.path.normcase(str(home)):
            return None
        seen.add(key)
        return p

    parent_of_repo = Path(paths.REPO_DIR).parent
    for p in [parent_of_repo, *(home / n for n in _COMMON_NAMES)]:
        if add(p):
            yield str(p)
    try:
        for entry in os.scandir(home):
            if entry.is_dir(follow_symlinks=False) and not entry.name.startswith(".") \
                    and entry.name.lower() not in _SKIP_NAMES and not entry.name.lower().startswith("onedrive"):
                if add(entry.path):
                    yield entry.path
    except OSError:
        pass
    if IS_WINDOWS:
        for drive in ("C:\\", "D:\\", "E:\\"):
            for n in ("develop", "dev", "projects", "repos", "workspace", "code"):
                if add(os.path.join(drive, n)):
                    yield os.path.join(drive, n)
    for ws in antigravity_workspaces().values():
        if add(os.path.dirname(ws["path"])):
            yield os.path.dirname(ws["path"])


@lru_cache(maxsize=1)
def discover_develop_dir() -> str:
    """Pasta de projetos desta máquina. Resultado cacheado em memória e em ``local_ui.json``."""
    cached = load_local_ui().get("develop_dir")
    if cached and os.path.isdir(cached):
        return cached

    deadline = time.monotonic() + _SCAN_BUDGET_SECONDS
    best_dir, best_score = str(Path.home() / "develop"), 0
    for cand in _candidate_dirs():
        if time.monotonic() > deadline:
            break
        sc = score_workspace_candidate(cand, deadline)
        if sc > best_score:
            best_dir, best_score = cand, sc
    if best_score == 0 and not os.path.isdir(best_dir):
        best_dir = str(Path.home())
    save_local_ui({"develop_dir": best_dir, "develop_score": best_score})
    return best_dir


def forget_develop_dir() -> None:
    """Força nova descoberta (ex.: usuário mudou de pasta)."""
    save_local_ui({"develop_dir": None})
    discover_develop_dir.cache_clear()


def list_repos(root: Optional[str] = None) -> List[str]:
    root = root or discover_develop_dir()
    try:
        names = sorted(os.listdir(root))
    except OSError:
        return []
    return [os.path.join(root, n) for n in names if _is_repo(os.path.join(root, n))]


def find_project_subdir(project_name: str) -> str:
    """Localiza ``<develop>/<project_name>`` ignorando maiúsculas/minúsculas."""
    root = discover_develop_dir()
    direct = os.path.join(root, project_name)
    if os.path.isdir(direct):
        return direct
    try:
        for item in os.listdir(root):
            if item.lower() == project_name.lower() and os.path.isdir(os.path.join(root, item)):
                return os.path.join(root, item)
    except OSError:
        pass
    return direct
