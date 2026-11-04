"""Log em arquivo. Essencial no Windows: ``pythonw`` engole qualquer traceback."""

import logging
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path

from core import paths

_configured = False


def setup_logging(name: str = "hud", console: bool = False) -> logging.Logger:
    global _configured
    logger = logging.getLogger("hud")
    if _configured:
        return logger
    _configured = True

    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s [%(threadName)s] %(message)s")
    try:
        Path(paths.LOG_DIR).mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(Path(paths.LOG_DIR) / f"{name}.log", maxBytes=512_000, backupCount=2, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except OSError:
        pass
    if console:
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        logger.addHandler(sh)

    def _log_uncaught(exc_type, exc, tb):
        if not issubclass(exc_type, KeyboardInterrupt):
            logger.critical("Exceção não tratada", exc_info=(exc_type, exc, tb))

    sys.excepthook = _log_uncaught
    threading.excepthook = lambda a: logger.critical(
        "Exceção na thread %s", getattr(a.thread, "name", "?"), exc_info=(a.exc_type, a.exc_value, a.exc_traceback)
    )
    return logger


def get_logger(suffix: str = "") -> logging.Logger:
    return logging.getLogger("hud" + (f".{suffix}" if suffix else ""))
