"""
Automatic Git Synchronization Daemon (GitSyncDaemon) for vector-prod-maxxing
Features:
- Completely detached Bot identity (GIT_AUTHOR_EMAIL=bot@vector-hud.internal)
  so GitHub NEVER counts or attributes these commits to the user's personal GitHub account/profile.
- Periodic background check only PULLS (never commits on a timer).
- Auto-commit ONLY triggers 45s after real study, exam, or writing data changes.
- Never commits live node telemetry (CPU/RAM heartbeats).
"""

import os
import subprocess
import threading
import time
from datetime import datetime
from typing import Callable, Optional

from modules.env_resolver import REPO_DIR, HOSTNAME

BOT_NAME = "Vector HUD Bot"
BOT_EMAIL = "bot@vector-hud.internal"


def _get_git_env() -> dict:
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = BOT_NAME
    env["GIT_AUTHOR_EMAIL"] = BOT_EMAIL
    env["GIT_COMMITTER_NAME"] = BOT_NAME
    env["GIT_COMMITTER_EMAIL"] = BOT_EMAIL
    return env


def run_git_pull_only() -> tuple[bool, str]:
    """Pulls latest changes with rebase/autostash without creating any commits."""
    if not os.path.isdir(os.path.join(REPO_DIR, ".git")):
        return False, "Não é um repositório Git."
    try:
        branch_res = subprocess.run(
            ["git", "-C", REPO_DIR, "branch", "--show-current"],
            capture_output=True, text=True, timeout=5
        )
        branch = branch_res.stdout.strip() or "master"

        pull_res = subprocess.run(
            ["git", "-C", REPO_DIR, "pull", "--rebase", "--autostash", "origin", branch],
            capture_output=True, text=True, timeout=30
        )
        if pull_res.returncode != 0:
            subprocess.run(["git", "-C", REPO_DIR, "rebase", "--abort"], capture_output=True, timeout=5)
            return False, f"Aviso pull: {pull_res.stderr.strip()[:50]}"
        return True, "Atualizado"
    except Exception as e:
        return False, f"Erro pull: {str(e)[:40]}"


def run_git_sync_once(commit_prefix: str = "chore(data): sync metrics") -> tuple[bool, str]:
    """
    Stages only persistent data files (data.json, events.jsonl, pinned_projects.json, questoes/).
    Commits using a detached Bot author email (never attributed to the user's GitHub profile).
    Pulls with rebase and pushes to origin.
    """
    if not os.path.isdir(os.path.join(REPO_DIR, ".git")):
        return False, "Não é um repositório Git."

    try:
        # 1. Stage ONLY persistent study, writing, and config files (never ephemeral nodes telemetry)
        stage_targets = [
            "data/data.json",
            "data/events.jsonl",
            "data/pinned_projects.json",
            "data/questoes"
        ]
        existing_targets = [t for t in stage_targets if os.path.exists(os.path.join(REPO_DIR, t))]
        if existing_targets:
            subprocess.run(
                ["git", "-C", REPO_DIR, "add"] + existing_targets,
                capture_output=True, text=True, timeout=10
            )

        # 2. Check if anything is staged
        diff_res = subprocess.run(
            ["git", "-C", REPO_DIR, "diff", "--cached", "--quiet"],
            capture_output=True, text=True, timeout=5
        )
        committed = False
        if diff_res.returncode != 0:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            msg = f"{commit_prefix} [{HOSTNAME} @ {ts}]"
            git_env = _get_git_env()
            c_res = subprocess.run(
                [
                    "git", "-C", REPO_DIR, "commit",
                    f"--author={BOT_NAME} <{BOT_EMAIL}>",
                    "-m", msg
                ],
                capture_output=True, text=True, timeout=12, env=git_env
            )
            committed = (c_res.returncode == 0)

        # 3. Pull with rebase & autostash
        branch_res = subprocess.run(
            ["git", "-C", REPO_DIR, "branch", "--show-current"],
            capture_output=True, text=True, timeout=5
        )
        branch = branch_res.stdout.strip() or "master"

        pull_res = subprocess.run(
            ["git", "-C", REPO_DIR, "pull", "--rebase", "--autostash", "origin", branch],
            capture_output=True, text=True, timeout=30
        )
        if pull_res.returncode != 0:
            subprocess.run(["git", "-C", REPO_DIR, "rebase", "--abort"], capture_output=True, timeout=5)
            return False, f"Aviso rebase: {pull_res.stderr.strip()[:50]}"

        # 4. Push if local branch is ahead of origin
        status_res = subprocess.run(
            ["git", "-C", REPO_DIR, "status", "-sb"],
            capture_output=True, text=True, timeout=5
        )
        needs_push = committed or ("ahead" in status_res.stdout)

        if needs_push:
            push_res = subprocess.run(
                ["git", "-C", REPO_DIR, "push", "origin", branch],
                capture_output=True, text=True, timeout=35
            )
            if push_res.returncode != 0:
                return False, f"Erro push: {push_res.stderr.strip()[:50]}"
            return True, f"☁️ Sync OK ({datetime.now().strftime('%H:%M')})"

        return True, f"☁️ Sincronizado ({datetime.now().strftime('%H:%M')})"
    except Exception as e:
        return False, f"Erro Git: {str(e)[:45]}"


class GitSyncManager:
    """
    Manages debounced commits (only when data changes) and periodic pulls (never commits on timer).
    Uses Bot author so no commits are counted towards the user's GitHub account.
    """
    def __init__(self, on_status_change: Optional[Callable[[bool, str], None]] = None, debounce_sec: int = 45):
        self.on_status_change = on_status_change
        self.debounce_sec = debounce_sec
        self._debounce_timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()
        self._running = True
        self._is_syncing = False

        # Periodic background pull thread (every 3 minutes, only pulls, never commits)
        self._pull_thread = threading.Thread(target=self._periodic_pull_loop, daemon=True)
        self._pull_thread.start()

    def notify_data_changed(self):
        """Called ONLY when data.json or events.jsonl changes. Resets debounce timer."""
        with self._lock:
            if self._debounce_timer is not None:
                self._debounce_timer.cancel()
            self._debounce_timer = threading.Timer(self.debounce_sec, self.sync_now_async)
            self._debounce_timer.daemon = True
            self._debounce_timer.start()

    def sync_now_async(self):
        if self._is_syncing:
            return
        t = threading.Thread(target=self._execute_sync, daemon=True)
        t.start()

    def _execute_sync(self):
        if self._is_syncing:
            return
        self._is_syncing = True
        if self.on_status_change:
            try:
                self.on_status_change(True, "🔄 Sincronizando...")
            except Exception:
                pass
        ok, msg = run_git_sync_once()
        self._is_syncing = False
        if self.on_status_change:
            try:
                self.on_status_change(ok, msg)
            except Exception:
                pass

    def _periodic_pull_loop(self):
        time.sleep(5)
        run_git_pull_only()
        while self._running:
            time.sleep(180)
            if not self._is_syncing:
                run_git_pull_only()

    def stop(self):
        self._running = False
        with self._lock:
            if self._debounce_timer:
                self._debounce_timer.cancel()
