"""Shim de compatibilidade: delega para ``core.focus`` e ``core.study``."""

from core.focus import (
    BLOCKED_DOMAINS,
    DISTRACTION_KEYWORDS,
    PAC_URL,
    activate as activate_focus_mode,
    block_distractions as block_active_distractions,
    deactivate as deactivate_focus_mode,
    generate_pac_file,
)
from core.study import record_session as record_study_session

__all__ = [
    "BLOCKED_DOMAINS",
    "DISTRACTION_KEYWORDS",
    "PAC_URL",
    "generate_pac_file",
    "activate_focus_mode",
    "deactivate_focus_mode",
    "block_active_distractions",
    "record_study_session",
]
