"""Unit tests for hud_cli.py (Vector-Prod-Maxxing v2 Antigravity CLI)."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import hud_cli
from core import paths


@pytest.fixture
def isolated_env(monkeypatch, tmp_path):
    """Redirect data paths to a temporary copy so real repo data is untouched."""
    data_dir = tmp_path / "data"
    questoes_dir = data_dir / "questoes"
    questoes_dir.mkdir(parents=True)

    shutil.copy(REPO_ROOT / "data" / "data.json", data_dir / "data.json")
    shutil.copy(REPO_ROOT / "data" / "projects.json", data_dir / "projects.json")
    (data_dir / "events.jsonl").write_text("", encoding="utf-8")

    monkeypatch.setattr(paths, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(paths, "DATA_FILE", str(data_dir / "data.json"))
    monkeypatch.setattr(paths, "EVENTS_FILE", str(data_dir / "events.jsonl"))
    monkeypatch.setattr(paths, "NODES_DIR", str(data_dir / "nodes"))
    monkeypatch.setattr(hud_cli, "PROJECTS_FILE", str(data_dir / "projects.json"))
    monkeypatch.setattr(hud_cli, "QUESTOES_DIR", str(questoes_dir))
    return tmp_path


def _run_main(monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", ["hud_cli.py", *argv])
    hud_cli.main()


def test_log_study_updates_subject_topic_and_events(isolated_env, monkeypatch, capsys):
    _run_main(
        monkeypatch,
        [
            "log-study",
            "--subject",
            "fisica3",
            "--questions",
            "4",
            "--reading-min",
            "35",
            "--pages",
            "12",
            "--topic",
            "Lei de Gauss",
        ],
    )
    out = capsys.readouterr().out
    assert "Física III" in out
    assert "+4 questões" in out
    assert "+35 min leitura" in out

    data = json.loads((isolated_env / "data" / "data.json").read_text(encoding="utf-8"))
    f3 = next(d for d in data["semesters"]["2027.1"]["disciplinas"] if d["id"] == "fisica3")
    assert f3["ultimo_estudo"] is not None
    assert f3["ultima_leitura"] is not None
    gauss_topic = next(t for t in f3["topicos"] if "Gauss" in t["titulo"])
    assert gauss_topic["questoes_resolvidas"] == 4
    assert gauss_topic["status"] == "lendo"

    events = [
        json.loads(line)
        for line in (isolated_env / "data" / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(events) == 1
    assert events[0]["type"] == "study_session"
    assert events[0]["mode"] == "misto"
    assert events[0]["reading_min"] == 35
    assert events[0]["pages"] == 12


def test_add_questions_imports_and_deduplicates(isolated_env, monkeypatch, capsys):
    q_file = isolated_env / "incoming.json"
    q_file.write_text(
        json.dumps(
            [
                {
                    "id": "em_ai_1",
                    "topico": "Equações de Maxwell",
                    "dificuldade": "dificil",
                    "enunciado": "Mostre $\\nabla \\times \\vec{E} = -\\frac{\\partial \\vec{B}}{\\partial t}$.",
                    "dica": "Use Lei de Faraday.",
                    "gabarito": "Aplicando Stokes...",
                }
            ]
        ),
        encoding="utf-8",
    )

    _run_main(monkeypatch, ["add-questions", "--subject", "eletromagnetismo", "--file", str(q_file)])
    out = capsys.readouterr().out
    assert "+1 novas" in out

    # Mark existing question as acertei and re-import same ID -> status must be preserved
    bank_path = isolated_env / "data" / "questoes" / "eletromagnetismo.json"
    bank = json.loads(bank_path.read_text(encoding="utf-8"))
    bank[0]["status"] = "acertei"
    bank[0]["attempts"] = 2
    bank_path.write_text(json.dumps(bank), encoding="utf-8")

    _run_main(monkeypatch, ["add-questions", "--subject", "eletromagnetismo", "--file", str(q_file)])
    out2 = capsys.readouterr().out
    assert "1 atualizadas" in out2

    bank_after = json.loads(bank_path.read_text(encoding="utf-8"))
    assert len(bank_after) == 1
    assert bank_after[0]["status"] == "acertei"
    assert bank_after[0]["attempts"] == 2


def test_set_exam_and_update_topic(isolated_env, monkeypatch, capsys):
    _run_main(
        monkeypatch,
        [
            "set-exam",
            "--subject",
            "sinais_sistemas",
            "--exam",
            "p1",
            "--grade",
            "8.5",
            "--date",
            "2027-04-20",
        ],
    )
    _run_main(
        monkeypatch,
        [
            "set-exam",
            "--subject",
            "sinais_sistemas",
            "--exam",
            "trabalho",
            "--grade",
            "9.0",
            "--peso",
            "0.5",
        ],
    )
    _run_main(
        monkeypatch,
        [
            "update-topic",
            "--subject",
            "sinais_sistemas",
            "--topic",
            "Convolução",
            "--status",
            "dominado",
            "--reading-done",
        ],
    )

    data = json.loads((isolated_env / "data" / "data.json").read_text(encoding="utf-8"))
    ss = next(d for d in data["semesters"]["2027.1"]["disciplinas"] if d["id"] == "sinais_sistemas")
    p1 = next(a for a in ss["avaliacoes"] if a["id"] == "p1")
    assert p1["nota"] == 8.5
    assert p1["data"] == "2027-04-20"
    trab = next(a for a in ss["avaliacoes"] if a["id"] == "trabalho")
    assert trab["nota"] == 9.0
    assert trab["peso"] == 0.5
    conv = next(t for t in ss["topicos"] if "Convolução" in t["titulo"])
    assert conv["status"] == "dominado"
    assert conv["leitura_concluida"] is True


def test_log_project_and_stats(isolated_env, monkeypatch, capsys):
    _run_main(
        monkeypatch,
        [
            "log-project",
            "--project",
            "rl-robot",
            "--category",
            "robotics",
            "--duration",
            "50",
            "--summary",
            "Ajuste de recompensa PPO",
            "--next-action",
            "Rodar 5M steps",
        ],
    )
    projs = json.loads((isolated_env / "data" / "projects.json").read_text(encoding="utf-8"))
    rl = next(p for p in projs if p["id"] == "rl-robot")
    assert rl["next_action"] == "Rodar 5M steps"

    _run_main(monkeypatch, ["log-study", "--subject", "resmat", "--reading-min", "45", "--questions", "2"])
    capsys.readouterr()

    _run_main(monkeypatch, ["stats"])
    stats_out = json.loads(capsys.readouterr().out)
    assert stats_out["active_semester"] == "2027.1"
    assert stats_out["today"]["reading_min"] == 45
    assert stats_out["today"]["questions"] == 2
    assert len(stats_out["subjects"]) == 7
