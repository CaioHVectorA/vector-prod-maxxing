"""Registro de estudos, provas e notas (antes duplicado entre CLI e GUI)."""

from datetime import datetime, timedelta
from typing import Optional

from core import paths
from core.storage import append_event, read_json, update_json
from core.timeutil import workday_key


def _find_subject(subjects: list, ident: str) -> Optional[dict]:
    ident = ident.lower()
    for d in subjects:
        if d.get("id", "").lower() == ident:
            return d
    for d in subjects:
        if ident in d.get("nome", "").lower():
            return d
    return None


def _roll_day(estudos: dict) -> bool:
    """Ajusta contador diário e sequência quando o dia de trabalho (06:00) muda.

    Retorna True se ``estudos`` foi alterado. Dados antigos sem ``dia_ref`` são
    apenas marcados com o dia atual, sem zerar nada (migração).
    """
    today = workday_key()
    last = estudos.get("dia_ref")
    if last == today:
        return False
    if last is None:
        estudos["dia_ref"] = today
        estudos["streak_contado_hoje"] = estudos.get("questoes_feitas_hoje", 0) > 0
        return True
    yesterday = workday_key(datetime.now() - timedelta(days=1))
    if not (last == yesterday and estudos.get("questoes_feitas_hoje", 0) > 0):
        estudos["streak_dias"] = 0
    estudos["questoes_feitas_hoje"] = 0
    estudos["dia_ref"] = today
    estudos["streak_contado_hoje"] = False
    return True


def ensure_current_day() -> dict:
    """Garante que os contadores diários valem para hoje; retorna ``data.json`` atualizado.

    Chamar antes de exibir os contadores, para ontem não aparecer como "hoje".
    """
    data = read_json(paths.DATA_FILE, {})
    if not isinstance(data, dict):
        data = {}
    probe = dict(data.get("estudos", {}))
    if probe and _roll_day(probe):
        def _mutate(d: dict) -> dict:
            if not isinstance(d, dict):
                return data
            _roll_day(d.setdefault("estudos", {}))
            return d
        return update_json(paths.DATA_FILE, _mutate, default={})
    return data


def record_session(subject: str, questions: int = 1, topic: str = "") -> bool:
    """Soma questões feitas hoje, marca o último estudo da matéria e registra o evento.

    Retorna False se a matéria não existe (o evento ainda é registrado).
    """
    found = {"ok": False}

    def mutate(data: dict) -> None:
        estudos = data.setdefault("estudos", {})
        _roll_day(estudos)
        estudos["questoes_feitas_hoje"] = estudos.get("questoes_feitas_hoje", 0) + questions
        if questions > 0 and not estudos.get("streak_contado_hoje"):
            estudos["streak_dias"] = estudos.get("streak_dias", 0) + 1
            estudos["streak_contado_hoje"] = True
        d = _find_subject(estudos.get("disciplinas", []), subject)
        if d:
            d["ultimo_estudo"] = datetime.now().isoformat(timespec="seconds")
            found["ok"] = True

    update_json(paths.DATA_FILE, mutate, default={})
    append_event("study_session", subject=subject, questions=questions, topic=topic)
    return found["ok"]


def set_exam(subject: str, exam: str, grade: Optional[float] = None, date: Optional[str] = None) -> bool:
    exam = exam.lower()
    found = {"ok": False}

    def mutate(data: dict) -> None:
        d = _find_subject(data.get("estudos", {}).get("disciplinas", []), subject)
        if not d:
            return
        if grade is not None:
            d[exam] = float(grade)
        if date:
            d[f"data_{exam}"] = date
        found["ok"] = True

    update_json(paths.DATA_FILE, mutate, default={})
    if found["ok"]:
        append_event("exam_update", subject=subject, exam=exam, grade=grade, date=date)
    return found["ok"]
