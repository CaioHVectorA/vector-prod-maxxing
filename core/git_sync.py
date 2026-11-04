"""Sincronização com o GitHub apenas para mudanças relevantes nos dados.

Garantias:
  * commits assinados pelo bot (``bot@vector-hud.internal``), que o GitHub não
    associa ao perfil pessoal, então não aparecem no gráfico de contribuições;
  * só ``data/`` persistente é versionado (telemetria em ``data/nodes`` é ignorada);
  * debounce de 45 s + intervalo mínimo de 15 min entre commits automáticos;
  * o pull periódico nunca mexe na árvore de trabalho se houver mudanças locais
    fora de ``data/`` (não bagunça o código que você está editando);
  * após falha de push, espera 10 min antes de tentar de novo (evita pop-ups
    repetidos do gerenciador de credenciais).
"""

import threading
import time
from datetime import datetime
from typing import Callable, List, Optional, Tuple

from core import paths
from core.gitutil import current_branch, git, is_repo
from core.osinfo import HOSTNAME
from core.settings import BOT_EMAIL, BOT_NAME

DEBOUNCE_SECONDS = 45
MIN_COMMIT_INTERVAL = 15 * 60
PULL_INTERVAL = 3 * 60
FAILURE_BACKOFF = 10 * 60

_TRACKED = ["data/data.json", "data/events.jsonl", "data/pinned_projects.json",
            "data/environments.json", "data/questoes"]

StatusCallback = Callable[[bool, str], None]
Result = Tuple[bool, str]


def _bot_commit_args(message: str) -> List[str]:
    return [
        "-c", f"user.name={BOT_NAME}", "-c", f"user.email={BOT_EMAIL}", "-c", "commit.gpgsign=false",
        "commit", f"--author={BOT_NAME} <{BOT_EMAIL}>", "-m", message,
    ]


def _dirty_outside_data(repo: str) -> bool:
    r = git(repo, "status", "--porcelain=v1", "--untracked-files=no")
    return any(ln[3:] and not ln[3:].startswith("data/") for ln in r.stdout.splitlines())


def _behind_ahead(repo: str, branch: str) -> Tuple[int, int]:
    r = git(repo, "rev-list", "--left-right", "--count", f"origin/{branch}...HEAD", timeout=10)
    try:
        behind, ahead = r.stdout.split()
        return int(behind), int(ahead)
    except ValueError:
        return 0, 0


def sync_once(commit_prefix: str = "chore(data): sync") -> Result:
    """Commit dos dados (se houver), integra o remoto e envia. Seguro em qualquer thread."""
    repo = paths.REPO_DIR
    if not is_repo(repo):
        return False, "Não é um repositório git"

    branch = current_branch(repo) or "master"
    fetch = git(repo, "fetch", "origin", branch, timeout=40)
    if not fetch.ok:
        return False, f"Sem acesso ao GitHub: {(fetch.error or fetch.stderr).strip()[:60]}"

    import os
    git(repo, "add", "--", *[t for t in _TRACKED if os.path.exists(os.path.join(repo, t))])
    committed = False
    if git(repo, "diff", "--cached", "--quiet").returncode != 0:
        msg = f"{commit_prefix} [{HOSTNAME} @ {datetime.now():%Y-%m-%d %H:%M}]"
        committed = git(repo, *_bot_commit_args(msg), timeout=20).ok

    behind, ahead = _behind_ahead(repo, branch)
    if behind:
        if _dirty_outside_data(repo):
            return False, "Pendente: há alterações locais no código"
        if not git(repo, "pull", "--rebase", f"origin", branch, timeout=60).ok:
            git(repo, "rebase", "--abort")
            return False, "Conflito ao integrar dados (resolva manualmente)"
        ahead = _behind_ahead(repo, branch)[1]

    if ahead or committed:
        push = git(repo, "push", "origin", branch, timeout=60)
        if not push.ok:
            return False, f"Falha no push: {(push.error or push.stderr).strip()[:60]}"
        return True, f"Sincronizado {datetime.now():%H:%M}"
    return True, f"Atualizado {datetime.now():%H:%M}"


def pull_only() -> Result:
    """Traz atualizações sem criar commits. Pula se houver código local modificado."""
    repo = paths.REPO_DIR
    if not is_repo(repo):
        return False, "Não é um repositório git"
    branch = current_branch(repo) or "master"
    if not git(repo, "fetch", "origin", branch, timeout=40).ok:
        return False, "Sem acesso ao GitHub"
    behind, ahead = _behind_ahead(repo, branch)
    if not behind:
        return True, "Atualizado"
    if ahead or _dirty_outside_data(repo):
        return False, "Remoto à frente: aguardando sync"
    ok = git(repo, "merge", "--ff-only", f"origin/{branch}", timeout=30).ok
    return ok, "Atualizado" if ok else "Falha ao atualizar"


class GitSyncManager:
    def __init__(self, on_status: Optional[StatusCallback] = None):
        self._on_status = on_status
        self._lock = threading.Lock()
        self._timer: Optional[threading.Timer] = None
        self._running = True
        self._syncing = False
        self._last_commit_at = 0.0
        self._blocked_until = 0.0
        threading.Thread(target=self._pull_loop, name="git-pull", daemon=True).start()

    def _emit(self, ok: bool, msg: str) -> None:
        if self._on_status:
            try:
                self._on_status(ok, msg)
            except Exception:
                pass

    def notify_data_changed(self) -> None:
        """Agenda um commit: 45 s após a última mudança, respeitando o intervalo mínimo."""
        delay = max(DEBOUNCE_SECONDS, self._last_commit_at + MIN_COMMIT_INTERVAL - time.monotonic())
        with self._lock:
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(delay, self._auto_sync)
            self._timer.daemon = True
            self._timer.start()

    def _auto_sync(self) -> None:
        if time.monotonic() >= self._blocked_until:
            self._run(automatic=True)

    def sync_now_async(self) -> None:
        """Sync manual (botão): ignora intervalo mínimo e backoff."""
        threading.Thread(target=self._run, kwargs={"automatic": False}, name="git-sync", daemon=True).start()

    def _run(self, automatic: bool) -> None:
        with self._lock:
            if self._syncing:
                return
            self._syncing = True
        self._emit(True, "Sincronizando…")
        try:
            ok, msg = sync_once()
        finally:
            self._syncing = False
        if ok:
            self._last_commit_at = time.monotonic()
            self._blocked_until = 0.0
        elif automatic:
            self._blocked_until = time.monotonic() + FAILURE_BACKOFF
        self._emit(ok, msg)

    def _pull_loop(self) -> None:
        time.sleep(8)
        while self._running:
            if not self._syncing:
                ok, msg = pull_only()
                if not ok:
                    self._emit(False, msg)
            time.sleep(PULL_INTERVAL)

    def stop(self) -> None:
        self._running = False
        with self._lock:
            if self._timer:
                self._timer.cancel()
