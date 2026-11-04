"""Leitura/escrita de JSON com escrita atômica, estado local da UI e ledger de eventos.

HUD, servidor web e CLI escrevem nos mesmos arquivos. A escrita atômica
(arquivo temporário + ``os.replace``) evita que algum deles leia um JSON pela metade.
"""

import json
import os
import tempfile
import threading
from datetime import datetime
from typing import Any, Callable, Iterator, Optional

from core import paths
from core.osinfo import HOSTNAME

_lock = threading.RLock()


def read_json(path: str, default: Any = None) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_json(path: str, data: Any, indent: Optional[int] = 2) -> None:
    """Escrita atômica. Levanta ``OSError`` se não conseguir gravar."""
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", suffix=".json", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def update_json(path: str, mutate: Callable[[Any], Any], default: Any = None) -> Any:
    """Lê, aplica ``mutate(data)`` (que pode alterar in-place ou retornar novo valor) e grava."""
    with _lock:
        data = read_json(path, default)
        if data is None:
            data = {} if default is None else default
        result = mutate(data)
        data = data if result is None else result
        write_json(path, data)
        return data


# --- Estado local da UI (por máquina; não versionado) -------------------------

def load_local_ui() -> dict:
    return read_json(paths.LOCAL_UI_FILE, {}) or {}


def save_local_ui(updates: dict) -> None:
    with _lock:
        current = load_local_ui()
        current.update(updates)
        try:
            write_json(paths.LOCAL_UI_FILE, current)
        except OSError:
            pass  # estado de janela nunca deve derrubar o app


# --- Ledger de eventos (append-only, versionado) ------------------------------

def append_event(event_type: str, **fields: Any) -> dict:
    record = {"ts": datetime.now().isoformat(timespec="seconds"), "env": HOSTNAME, "type": event_type, **fields}
    with _lock:
        os.makedirs(os.path.dirname(paths.EVENTS_FILE), exist_ok=True)
        with open(paths.EVENTS_FILE, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def iter_events(since_ts: float = 0.0) -> Iterator[dict]:
    """Itera eventos a partir de ``since_ts`` (epoch). Aceita o formato legado
    (``timestamp``/``words_added``) e normaliza para ``ts``/``words``."""
    try:
        f = open(paths.EVENTS_FILE, "r", encoding="utf-8")
    except OSError:
        return
    with f:
        for line in f:
            try:
                ev = json.loads(line)
                raw_ts = ev.get("ts") or ev.get("timestamp") or ""
                ts = datetime.fromisoformat(raw_ts).timestamp()
            except (ValueError, TypeError, AttributeError):
                continue
            if ts < since_ts:
                continue
            if "words" not in ev and "words_added" in ev:
                ev["words"] = ev["words_added"]
            ev["_epoch"] = ts
            yield ev
