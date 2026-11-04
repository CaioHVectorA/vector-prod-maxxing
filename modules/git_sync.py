"""Shim de compatibilidade: delega para ``core.git_sync``."""

from core.git_sync import GitSyncManager, pull_only, sync_once as run_git_sync_once

__all__ = ["GitSyncManager", "pull_only", "run_git_sync_once"]
