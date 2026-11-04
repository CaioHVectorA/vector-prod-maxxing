"""Projetos: união de workspaces do Antigravity com repositórios da pasta de projetos.

Antes esta lógica existia duas vezes (``dev_widget`` e ``server``), com campos
diferentes. Agora há uma fonte única; GUI e web consomem o mesmo formato.
"""

import os
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List

from core import paths
from core.gitutil import repo_snapshot
from core.storage import read_json, write_json
from core.timeutil import workday_start
from core.workspace import antigravity_workspaces, discover_develop_dir, list_repos

_SCAN_WORKERS = 4


def load_pinned() -> List[str]:
    data = read_json(paths.PINNED_FILE, [])
    return [str(x) for x in data] if isinstance(data, list) else []


def save_pinned(names: List[str]) -> None:
    write_json(paths.PINNED_FILE, list(names))


def toggle_pinned(name: str) -> List[str]:
    pinned = load_pinned()
    if name in pinned:
        pinned.remove(name)
    else:
        pinned.insert(0, name)
    save_pinned(pinned)
    return pinned


def _collect_projects() -> Dict[str, dict]:
    projects = antigravity_workspaces()
    for path in list_repos(discover_develop_dir()):
        name = os.path.basename(path)
        projects.setdefault(name, {
            "name": name, "path": path, "last_activity": "", "last_title": "",
            "convo_count": 0, "total_steps": 0,
        })
    return projects


def scan_projects() -> dict:
    """Retorna ``{"projects": [...], "stats": {...}}`` com git status de cada projeto."""
    since = workday_start().timestamp()
    pinned = set(load_pinned())
    projects = _collect_projects()

    with ThreadPoolExecutor(max_workers=_SCAN_WORKERS) as pool:
        snaps = list(pool.map(lambda p: repo_snapshot(p["path"], since), projects.values()))

    result, totals = [], {"today_add": 0, "today_del": 0, "week_add": 0, "week_del": 0}
    for info, snap in zip(projects.values(), snaps):
        merged = {**info, **snap.to_dict()}
        merged["name"], merged["path"] = info["name"], info["path"]  # snapshot não sobrescreve identidade
        merged["is_pinned"] = info["name"] in pinned or info["path"] in pinned
        merged["touched_today"] = bool(snap.today_add or snap.today_del or snap.last_commit_ts >= since)
        merged["branch"] = snap.branch or ("main" if snap.is_git else "")
        for k in totals:
            totals[k] += getattr(snap, k)
        result.append(merged)

    result.sort(
        key=lambda p: (p["is_pinned"], p["touched_today"], p.get("convo_count", 0), p.get("last_commit_ts", 0)),
        reverse=True,
    )
    return {"projects": result, "stats": {**totals, "total_projects": len(result)}}


def scan_repos() -> List[dict]:
    """Repositórios da pasta de projetos (aba "Repos & Eng" da web)."""
    since = workday_start().timestamp()
    paths_ = list_repos(discover_develop_dir())
    with ThreadPoolExecutor(max_workers=_SCAN_WORKERS) as pool:
        snaps = list(pool.map(lambda p: repo_snapshot(p, since), paths_))
    out = []
    for path, snap in zip(paths_, snaps):
        has_diff = snap.uncommitted_add or snap.uncommitted_del
        out.append({
            "name": snap.name,
            "path": path,
            "has_hud": os.path.exists(os.path.join(path, ".hud.json")),
            "uncommitted": snap.dirty,
            "diff_lines": {"add": snap.uncommitted_add, "del": snap.uncommitted_del} if has_diff else None,
        })
    return out
