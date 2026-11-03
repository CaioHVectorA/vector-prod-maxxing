"""
Focus Mode & Real Network Distraction Blocker Manager
- Network-level domain blocking for WhatsApp, Instagram, Twitter/X, Reddit, TikTok, Facebook via GNOME PAC Proxy
- Silences GNOME notifications
- Minimizes or closes distracting windows and processes
- Manages study automation & timestamps
"""

import subprocess
import time
import os
import json

CONFIG_DIR = os.path.expanduser("~/.config/desktop-hud")
DATA_PATH = os.path.join(CONFIG_DIR, "data.json")
PAC_FILE = os.path.join(CONFIG_DIR, "focus.pac")

BLOCKED_DOMAINS = [
    "web.whatsapp.com",
    "whatsapp.com",
    "instagram.com",
    "www.instagram.com",
    "twitter.com",
    "x.com",
    "reddit.com",
    "www.reddit.com",
    "tiktok.com",
    "www.tiktok.com",
    "facebook.com",
    "www.facebook.com"
]

DISTRACTION_KEYWORDS = ["whatsapp", "instagram", "twitter", "reddit", "tiktok", "facebook"]


def generate_pac_file():
    """Generates a Proxy Auto-Configuration (PAC) script that blackholes distractions."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    conditions = " ||\n        ".join([f'dnsDomainIs(host, "{d}") || host === "{d}"' for d in BLOCKED_DOMAINS])
    pac_content = f"""// Desktop HUD Focus Mode PAC - Auto Generated
function FindProxyForURL(url, host) {{
    if ({conditions}) {{
        // Redirect blocked distractions to a closed port (instant connection drop)
        return "PROXY 127.0.0.1:9999; DIRECT";
    }}
    return "DIRECT";
}}
"""
    with open(PAC_FILE, "w", encoding="utf-8") as f:
        f.write(pac_content)
    return PAC_FILE


def set_network_block(enable: bool):
    """Enables or disables system-wide network blocking for distraction domains via GNOME proxy."""
    if enable:
        generate_pac_file()
        try:
            # Tell GNOME to use local PAC served by Desktop HUD Web server
            subprocess.run([
                "gsettings", "set", "org.gnome.system.proxy", "autoconfig-url",
                "http://localhost:8090/focus.pac"
            ], timeout=2.0)
            subprocess.run([
                "gsettings", "set", "org.gnome.system.proxy", "mode", "auto"
            ], timeout=2.0)
        except Exception:
            pass
    else:
        try:
            subprocess.run([
                "gsettings", "set", "org.gnome.system.proxy", "mode", "none"
            ], timeout=2.0)
        except Exception:
            pass


def set_gnome_notifications(enable: bool):
    """Enables or disables GNOME popup desktop notifications."""
    val = "true" if enable else "false"
    try:
        subprocess.run(["gsettings", "set", "org.gnome.desktop.notifications", "show-banners", val], timeout=2.0)
    except Exception:
        pass


def block_active_distractions():
    """Finds and minimizes/hides distracting windows like WhatsApp, Instagram, etc."""
    try:
        res = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True, timeout=1.5)
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                line_lower = line.lower()
                for kw in DISTRACTION_KEYWORDS:
                    if kw in line_lower:
                        parts = line.split(None, 4)
                        if parts:
                            win_id = parts[0]
                            # Minimize distracting window
                            subprocess.run(["xdotool", "windowminimize", win_id], timeout=1.0)
    except Exception:
        pass


def activate_focus_mode():
    """Engages complete focus mode: Network blocking + Notification mute + Distraction window minimization."""
    set_gnome_notifications(False)
    set_network_block(True)
    block_active_distractions()


def deactivate_focus_mode():
    """Restores normal mode: Lifts network block + Restores notifications."""
    set_gnome_notifications(True)
    set_network_block(False)


def record_study_session(disciplina_id: str):
    """Updates the last studied timestamp and increments daily study count in data.json."""
    if not os.path.exists(DATA_PATH):
        return
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        now_iso = time.strftime("%Y-%m-%dT%H:%M:%S")
        disciplinas = data.get("estudos", {}).get("disciplinas", [])
        for d in disciplinas:
            if d.get("id") == disciplina_id:
                d["ultimo_estudo"] = now_iso
                break

        # Increment questions/sessions count
        estudos = data.setdefault("estudos", {})
        estudos["questoes_feitas_hoje"] = estudos.get("questoes_feitas_hoje", 0) + 1

        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass
