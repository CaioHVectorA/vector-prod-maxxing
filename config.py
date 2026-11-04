"""
Configuration settings for Dev & Hardware Desktop HUD
"""

from core.launchers import find_ide
from core.workspace import discover_develop_dir

DEVELOP_DIR = discover_develop_dir()
PREFERRED_IDE = find_ide() or "code"
FALLBACK_IDE = "code"

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
