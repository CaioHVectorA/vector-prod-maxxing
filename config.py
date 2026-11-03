"""
Configuration settings for Dev & Hardware Desktop HUD
"""

import os

DEVELOP_DIR = os.path.expanduser("~/develop")
PREFERRED_IDE = "/home/usuario/.local/bin/antigravity-ide"
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
