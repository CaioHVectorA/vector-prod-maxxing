---
name: vector-hud-sync
description: Synchronizes Antigravity 2.0 chat sessions with the user's vector-prod-maxxing Desktop HUD and multi-environment telemetry (UFF college studies, UVC writing sprints, AI training rigs, and GitHub auto-sync). Use whenever the user studies, solves questions, updates exam dates/grades, writes UVC chapters, or runs AI training across Linux/Windows environments.
---

# Vector-Prod-Maxxing HUD Synchronization Skill

This skill connects your Antigravity 2.0 conversation directly to the user's Desktop HUD (`vector-prod-maxxing`).

## How the Ecosystem Works
1. **Portable Data (`data/data.json`, `data/events.jsonl`, `data/nodes/<hostname>.json`)**:
   - Stored inside the repository's `data/` folder and watched live by the PyQt6 HUD via `QFileSystemWatcher`.
   - Any edit to `data/data.json` or `data/events.jsonl` refreshes the desktop widget on screen within 200ms.
   - `GitSyncManager` automatically commits and pushes changes in `data/` to `https://github.com/CaioHVectorA/vector-prod-maxxing`.

2. **CLI Helper (`hud_cli.py`)**:
   - Run `python3 hud_cli.py --help` in the repository root to log study questions, exam updates, writing sprints, or AI training progress on the active node.
