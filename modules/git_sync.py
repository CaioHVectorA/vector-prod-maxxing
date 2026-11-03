"""
Automatic Git Synchronization Daemon (GitSyncDaemon) for vector-prod-maxxing
Features:
- Debounced auto-commit & push of portable data/ directory (45s after last change)
- Periodic background git pull --rebase --autostash every 3 minutes
- Non-blocking QThread execution so the HUD never freezes
- Supports both Qt GUI mode and headless CLI/daemon mode
"""

import os
import subprocess
import threading
import time
from datetime import datetime
from typing import Callable, Optional

from modules.env_resolver import REPO_DIR, HOSTNAME


def run_git_sync_once(commit_prefix: str = "chore(sync): auto-update data") -> tuple[bool, str]:
    """
    Stages any changes inside data/, commits if dirty, pulls with rebase/autostash, and pushes to origin.
    Safe to call from any background thread or CLI.
    """
    if not os.path.isdir(os.path.join(REPO_DIR, ".git")):
        return False, "Não é um repositório Git."

    try:
        # 1. Stage data/ changes
        subprocess.run(
            ["git", "-C", REPO_DIR, "add", "data/"],
            capture_output=True, text=True, timeout=10
        )

        # 2. Check if there are staged changes in data/
        diff_res = subprocess.run(
            ["git", "-C", REPO_DIR, "diff", "--cached", "--quiet"],
            capture_output=True, text=True, timeout=5
        )
        committed = False
        if diff_res.returncode != 0:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            msg = f"{commit_prefix} [{HOSTNAME} @ {ts}]"
            c_res = subprocess.run(
                ["git", "-C", REPO_DIR, "commit", "-m", msg],
                capture_output=True, text=True, timeout=12
            )
            committed = (c_res.returncode == 0)

        # 3. Pull with rebase & autostash so multi-PC changes merge cleanly
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
            # Abort rebase if conflict and report
            subprocess.run(["git", "-C", REPO_DIR, "rebase", "--abort"], capture_output=True, timeout=5)
            return False, f"Conflito no pull: {pull_res.stderr.strip()[:60]}"

        # 4. Push if we committed or if local branch is ahead of origin
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
                return False, f"Erro no push: {push_res.stderr.strip()[:60]}"
            return True, f"☁️ Sync enviado ({datetime.now().strftime('%H:%M')})"

        return True, f"☁️ Sincronizado ({datetime.now().strftime('%H:%M')})"
    except Exception as e:
        return False, f"Erro Git: {str(e)[:45]}"


class GitSyncManager:
    """
    Manages debounced commits and periodic pulls in a background thread.
    Works with or without PyQt6.
    """
    def __init__(self, on_status_change: Optional[Callable[[bool, str], None]] = None, debounce_sec: int = 45):
        self.on_status_change = on_status_change
        self.debounce_sec = debounce_sec
        self._debounce_timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()
        self._running = True
        self._is_syncing = False

        # Start periodic pull loop (every 180 seconds)
        self._pull_thread = threading.Thread(target=self._periodic_loop, daemon=True)
        self._pull_thread.start()

    def notify_data_changed(self):
        """Called when data.json or events.jsonl changes. Resets the 45s debounce timer."""
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
                self.on_status_change(True, "🔄 Sincronizando Git...")
            except Exception:
                pass
        ok, msg = run_git_sync_once()
        self._is_syncing = False
        if self.on_status_change:
            try:
                self.on_status_change(ok, msg)
            except Exception:
                pass

    def _periodic_loop(self):
        # Initial sync 5 seconds after startup
        time.sleep(5)
        self._execute_sync()
        while self._running:
            time.sleep(180)
            if not self._is_syncing:
                self._execute_sync()

    def stop(self):
        self._running = False
        with self._lock:
            if self._debounce_timer:
                self._debounce_timer.cancel()
