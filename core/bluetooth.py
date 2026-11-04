"""Bluetooth via ``bluetoothctl`` (BlueZ). Só funciona no Linux.

Em outras plataformas todas as funções devolvem ``(False, mensagem)`` / listas
vazias, e ``supported()`` permite à UI avisar o usuário em vez de falhar.
"""

import re
from typing import List, Tuple

from core import proc
from core.osinfo import IS_LINUX

_MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")
UNSUPPORTED_MESSAGE = "Controle Bluetooth pelo painel só está disponível no Linux (bluetoothctl)."


def supported() -> bool:
    return IS_LINUX and bool(proc.which("bluetoothctl"))


def is_valid_mac(mac: str) -> bool:
    return bool(mac) and bool(_MAC_RE.match(mac))


def _ctl(*args: str, timeout: float = 5.0) -> proc.CmdResult:
    return proc.run(["bluetoothctl", *args], timeout=timeout)


def _unblock() -> None:
    rfkill = proc.which("rfkill") or "/usr/sbin/rfkill"
    proc.run([rfkill, "unblock", "bluetooth"], timeout=3)


def status() -> dict:
    if not supported():
        return {"powered": False, "name": "", "supported": False, "error": UNSUPPORTED_MESSAGE}
    r = _ctl("show", timeout=3)
    name = ""
    for line in r.stdout.splitlines():
        if line.strip().startswith("Name:"):
            name = line.split("Name:", 1)[1].strip()
    return {"powered": "Powered: yes" in r.stdout, "name": name, "supported": True}


def _device_icon(name: str, info: str) -> str:
    low, info_low = name.lower(), info.lower()
    if "audio" in info_low or "headset" in info_low or any(k in low for k in ("tws", "bt510", "m10", "buds", "jbl", "airpods")):
        return "audio"
    if "mouse" in low:
        return "mouse"
    if "controller" in low:
        return "controller"
    return "generic"


def devices() -> List[dict]:
    if not supported():
        return []
    out = []
    for line in _ctl("devices", timeout=4).stdout.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) < 3 or parts[0] != "Device":
            continue
        mac, name = parts[1], parts[2]
        info = _ctl("info", mac, timeout=3).stdout
        rssi = re.search(r"RSSI:\s*(-?\d+)", info)
        out.append({
            "mac": mac, "name": name,
            "connected": "Connected: yes" in info,
            "paired": "Paired: yes" in info,
            "icon": _device_icon(name, info),
            "rssi": int(rssi.group(1)) if rssi else None,
        })
    return out


def set_power(on: bool) -> Tuple[bool, str]:
    if not supported():
        return False, UNSUPPORTED_MESSAGE
    if on:
        _unblock()
    r = _ctl("power", "on" if on else "off", timeout=4)
    return r.ok or "succeeded" in r.stdout.lower(), r.output


def scan(seconds: int = 5) -> List[dict]:
    if not supported():
        return []
    _unblock()
    _ctl("power", "on", timeout=4)
    _ctl("--timeout", str(seconds), "scan", "on", timeout=seconds + 3)
    return devices()


def _device_action(verb: str, mac: str, timeout: float) -> proc.CmdResult:
    return _ctl(verb, mac, timeout=timeout)


def connect(mac: str) -> Tuple[bool, str]:
    if not supported():
        return False, UNSUPPORTED_MESSAGE
    msg = _device_action("connect", mac, 10).output
    ok = "Connection successful" in msg
    return ok, "Conectado com sucesso!" if ok else f"Falha ao conectar: {msg.strip()}"


def disconnect(mac: str) -> Tuple[bool, str]:
    if not supported():
        return False, UNSUPPORTED_MESSAGE
    r = _device_action("disconnect", mac, 6)
    ok = r.ok or "successful" in r.output.lower()
    return ok, "Desconectado!" if ok else r.output


def pair(mac: str) -> Tuple[bool, str]:
    if not supported():
        return False, UNSUPPORTED_MESSAGE
    r = _device_action("pair", mac, 10)
    ok = r.ok or "Pairing successful" in r.output
    return ok, "Pareado com sucesso!" if ok else r.output
