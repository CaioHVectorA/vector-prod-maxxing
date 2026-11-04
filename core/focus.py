"""Modo foco: bloqueio de rede (PAC), silenciar notificações e minimizar distrações.

Backends por plataforma:
  * Linux/GNOME: ``gsettings`` (proxy + banners) e ``wmctrl``/``xdotool``.
  * Windows: registro do WinINET (AutoConfigURL) e ``EnumWindows`` via ctypes.
As configurações originais do usuário são salvas ao ativar e restauradas ao
desativar (o código antigo apagava o modo de proxy do usuário).
"""

import os
from typing import List

from core import paths, proc
from core.osinfo import IS_LINUX, IS_WINDOWS
from core.settings import WEB_PORT
from core.storage import read_json, write_json

BLOCKED_DOMAINS = [
    "web.whatsapp.com", "whatsapp.com", "instagram.com", "www.instagram.com",
    "twitter.com", "x.com", "reddit.com", "www.reddit.com",
    "tiktok.com", "www.tiktok.com", "facebook.com", "www.facebook.com",
]
DISTRACTION_KEYWORDS = ["whatsapp", "instagram", "twitter", "reddit", "tiktok", "facebook"]

PAC_URL = f"http://localhost:{WEB_PORT}/focus.pac"
_WININET_KEY = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"


def generate_pac_file() -> str:
    conditions = " ||\n        ".join(f'dnsDomainIs(host, "{d}") || host === "{d}"' for d in BLOCKED_DOMAINS)
    content = (
        "// Desktop HUD Focus Mode PAC - gerado automaticamente\n"
        "function FindProxyForURL(url, host) {\n"
        f"    if ({conditions}) {{\n"
        '        return "PROXY 127.0.0.1:9999; DIRECT";\n'  # porta fechada: conexão cai na hora
        "    }\n"
        '    return "DIRECT";\n'
        "}\n"
    )
    os.makedirs(paths.LOCAL_CONFIG_DIR, exist_ok=True)
    with open(paths.PAC_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    return paths.PAC_FILE


# --- Linux (GNOME) -----------------------------------------------------------

def _gsettings_get(schema: str, key: str) -> str:
    r = proc.run(["gsettings", "get", schema, key], timeout=3)
    return r.stdout.strip().strip("'") if r.ok else ""


def _gsettings_set(schema: str, key: str, value: str) -> None:
    proc.run(["gsettings", "set", schema, key, value], timeout=3)


def _linux_activate(state: dict) -> None:
    if not proc.which("gsettings"):
        return
    state["proxy_mode"] = _gsettings_get("org.gnome.system.proxy", "mode") or "none"
    state["autoconfig_url"] = _gsettings_get("org.gnome.system.proxy", "autoconfig-url")
    state["banners"] = _gsettings_get("org.gnome.desktop.notifications", "show-banners") or "true"
    _gsettings_set("org.gnome.system.proxy", "autoconfig-url", PAC_URL)
    _gsettings_set("org.gnome.system.proxy", "mode", "auto")
    _gsettings_set("org.gnome.desktop.notifications", "show-banners", "false")


def _linux_restore(state: dict) -> None:
    if not proc.which("gsettings"):
        return
    _gsettings_set("org.gnome.system.proxy", "mode", state.get("proxy_mode", "none"))
    _gsettings_set("org.gnome.system.proxy", "autoconfig-url", state.get("autoconfig_url", ""))
    _gsettings_set("org.gnome.desktop.notifications", "show-banners", state.get("banners", "true"))


def _linux_minimize(keywords: List[str]) -> None:
    if not (proc.which("wmctrl") and proc.which("xdotool")):
        return
    listing = proc.run(["wmctrl", "-l"], timeout=3)
    for line in listing.stdout.splitlines():
        if any(k in line.lower() for k in keywords):
            win_id = line.split(None, 1)[0]
            proc.run(["xdotool", "windowminimize", win_id], timeout=2)


# --- Windows -----------------------------------------------------------------

def _wininet_refresh() -> None:
    import ctypes
    wininet = ctypes.windll.wininet
    wininet.InternetSetOptionW(0, 39, 0, 0)  # INTERNET_OPTION_SETTINGS_CHANGED
    wininet.InternetSetOptionW(0, 37, 0, 0)  # INTERNET_OPTION_REFRESH


def _windows_activate(state: dict) -> None:
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _WININET_KEY, 0, winreg.KEY_READ | winreg.KEY_SET_VALUE) as key:
        for name in ("AutoConfigURL", "AutoDetect"):
            try:
                state[name] = list(winreg.QueryValueEx(key, name))
            except FileNotFoundError:
                state[name] = None
        winreg.SetValueEx(key, "AutoConfigURL", 0, winreg.REG_SZ, PAC_URL)
        winreg.SetValueEx(key, "AutoDetect", 0, winreg.REG_DWORD, 0)
    _wininet_refresh()


def _windows_restore(state: dict) -> None:
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _WININET_KEY, 0, winreg.KEY_SET_VALUE) as key:
        for name in ("AutoConfigURL", "AutoDetect"):
            saved = state.get(name)
            if saved:
                winreg.SetValueEx(key, name, 0, saved[1], saved[0])
            else:
                try:
                    winreg.DeleteValue(key, name)
                except FileNotFoundError:
                    pass
    _wininet_refresh()


def _windows_minimize(keywords: List[str]) -> None:
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def visit(hwnd, _lparam):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value.lower()
                if "desktop hud" not in title and any(k in title for k in keywords):
                    user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE
        return True

    user32.EnumWindows(enum_proc(visit), 0)


# --- API pública -------------------------------------------------------------

def activate() -> None:
    if read_json(paths.FOCUS_STATE_FILE):  # já ativo: não sobrescrever o estado original salvo
        return
    generate_pac_file()
    state: dict = {}
    try:
        if IS_WINDOWS:
            _windows_activate(state)
        elif IS_LINUX:
            _linux_activate(state)
        write_json(paths.FOCUS_STATE_FILE, state or {"active": True})
    finally:
        block_distractions()


def deactivate() -> None:
    state = read_json(paths.FOCUS_STATE_FILE)
    if state is None:
        return
    try:
        if IS_WINDOWS:
            _windows_restore(state)
        elif IS_LINUX:
            _linux_restore(state)
    finally:
        try:
            os.remove(paths.FOCUS_STATE_FILE)
        except OSError:
            pass


def block_distractions() -> None:
    if IS_WINDOWS:
        _windows_minimize(DISTRACTION_KEYWORDS)
    elif IS_LINUX:
        _linux_minimize(DISTRACTION_KEYWORDS)
