"""Helpers de tempo. O "dia de trabalho" começa às 06:00, não à meia-noite."""

from datetime import datetime, timedelta

WORKDAY_START_HOUR = 6


def workday_start(now: datetime = None) -> datetime:
    now = now or datetime.now()
    start = now.replace(hour=WORKDAY_START_HOUR, minute=0, second=0, microsecond=0)
    return start if now >= start else start - timedelta(days=1)


def workday_key(now: datetime = None) -> str:
    """Identificador (YYYY-MM-DD) do dia de trabalho corrente."""
    return workday_start(now).strftime("%Y-%m-%d")


def time_ago(seconds: float) -> str:
    if seconds < 60:
        return "agora"
    if seconds < 3600:
        return f"{int(seconds // 60)}min atrás"
    if seconds < 86400:
        return f"{int(seconds // 3600)}h atrás"
    if seconds < 86400 * 30:
        return f"{int(seconds // 86400)}d atrás"
    return f"{int(seconds // (86400 * 30))}mês atrás"
