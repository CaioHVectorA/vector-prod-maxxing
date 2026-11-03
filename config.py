"""
Configuration settings for Dev & Hardware Desktop HUD
"""

from modules.env_resolver import discover_develop_dir, get_antigravity_ide_bin

DEVELOP_DIR = discover_develop_dir()
PREFERRED_IDE = get_antigravity_ide_bin() or "/home/usuario/.local/bin/antigravity-ide"
FALLBACK_IDE = "code"
TERMINAL_CMD = "gnome-terminal --working-directory={path}"

# Window dimensions and placement
HUD_WIDTH = 360
HUD_MAX_HEIGHT = 1050
SCREEN_MARGIN_RIGHT = 18
SCREEN_MARGIN_TOP = 38

# Polling intervals (milliseconds)
CLOCK_INTERVAL_MS = 1000
HARDWARE_INTERVAL_MS = 2000
SYSTEM_INTERVAL_MS = 1500
PROJECTS_INTERVAL_MS = 6000
