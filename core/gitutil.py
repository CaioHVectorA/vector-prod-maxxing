"""Operações git baratas e seguras para rodar em background.

O scan antigo executava ~7 comandos git por repositório a cada 25 s. Aqui um
snapshot custa 2–3 comandos e fica em cache por ``CACHE_TTL`` segundos.
"""

import os
import re
import threading
import time
from dataclasses import asdict, dataclass
from typing import Dict, Optional, Tuple

from core import proc
from core.proc import CmdResult

CACHE_TTL = 45.0
DEFAULT_TIMEOUT = 15.0  # git no Windows (antivírus) é lento; 0,8 s dava falso negativo

# Nunca esperar credencial num terminal invisível: falha rápido em vez de travar.
_GIT_ENV = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C"}

_STAT_RE = {
    "add": re.compile(r"(\d+) insertion"),
    "del": re.compile(r"(\d+) deletion"),
}


def git(repo: str, *args: object, timeout: float = DEFAULT_TIMEOUT, env: Optional[dict] = None) -> CmdResult:
    return proc.run(["git", "-C", repo, *args], timeout=timeout, env=env or _GIT_ENV)


def is_repo(path: str) -> bool:
    return os.path.exists(os.path.join(path, ".git"))


def parse_shortstat(text: str) -> Tuple[int, int]:
    return (
        sum(int(x) for x in _STAT_RE["add"].findall(text)),
        sum(int(x) for x in _STAT_RE["del"].findall(text)),
    )


def current_branch(repo: str) -> str:
    r = git(repo, "branch", "--show-current", timeout=8)
    return r.stdout.strip() if r.ok else ""


@dataclass
class RepoSnapshot:
    path: str
    name: str
    is_git: bool = True
    branch: str = ""
    dirty: int = 0
    uncommitted_add: int = 0
    uncommitted_del: int = 0
    today_add: int = 0
    today_del: int = 0
    week_add: int = 0
    week_del: int = 0
    last_commit_ts: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


_cache: Dict[Tuple[str, int], Tuple[float, RepoSnapshot]] = {}
_cache_lock = threading.Lock()


def repo_snapshot(path: str, since_ts: float, *, use_cache: bool = True) -> RepoSnapshot:
    """Estado do repositório e linhas alteradas desde ``since_ts`` e nos últimos 7 dias."""
    name = os.path.basename(path.rstrip("/\\"))
    if not is_repo(path):
        return RepoSnapshot(path=path, name=name, is_git=False)

    key = (path, int(since_ts))
    now = time.monotonic()
    if use_cache:
        with _cache_lock:
            hit = _cache.get(key)
            if hit and now - hit[0] < CACHE_TTL:
                return hit[1]

    snap = RepoSnapshot(path=path, name=name)

    # 1) branch + arquivos pendentes numa chamada só
    status = git(path, "status", "--porcelain=v1", "-b")
    if status.ok:
        lines = status.stdout.splitlines()
        if lines and lines[0].startswith("## "):
            head = lines[0][3:]
            head = head.removeprefix("No commits yet on ")
            snap.branch = re.split(r"\.\.\.|\s", head, maxsplit=1)[0]
            lines = lines[1:]
        snap.dirty = len([ln for ln in lines if ln.strip()])

    # 2) mudanças ainda não commitadas (só se houver algo pendente)
    if snap.dirty:
        diff = git(path, "diff", "--shortstat", "HEAD")
        if diff.ok:
            snap.uncommitted_add, snap.uncommitted_del = parse_shortstat(diff.stdout)

    # 3) commits dos últimos 7 dias; cada um vem com seu timestamp para separar "hoje"
    log = git(path, "log", "--since=7.days.ago", "--shortstat", "--format=@%ct")
    commit_ts = 0.0
    if log.ok:
        for line in log.stdout.splitlines():
            if line.startswith("@"):
                commit_ts = float(line[1:] or 0)
                snap.last_commit_ts = max(snap.last_commit_ts, commit_ts)
            elif "changed" in line:
                add, dele = parse_shortstat(line)
                snap.week_add += add
                snap.week_del += dele
                if commit_ts >= since_ts:
                    snap.today_add += add
                    snap.today_del += dele
    if not snap.last_commit_ts:  # repositório parado há mais de 7 dias
        last = git(path, "log", "-1", "--format=%ct", timeout=8)
        if last.ok and last.stdout.strip().isdigit():
            snap.last_commit_ts = float(last.stdout.strip())

    snap.today_add += snap.uncommitted_add
    snap.today_del += snap.uncommitted_del

    with _cache_lock:
        _cache[key] = (now, snap)
    return snap
