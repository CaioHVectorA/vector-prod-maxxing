#!/usr/bin/env python3
"""
HUD CLI Helper (hud_cli.py) for Antigravity 2.0 Chat <-> Desktop HUD Bidirectional Protocol
Allows the AI agent (or user in terminal) to log study sessions, update exam dates/grades,
log writing sprints, register AI training jobs on remote/local rigs, and trigger GitHub auto-sync.
"""

import os
import sys
import json
import argparse
from datetime import datetime

base_dir = os.path.dirname(os.path.realpath(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from modules.env_resolver import DATA_PATH, EVENTS_FILE, HOSTNAME, ensure_directories
from modules.nodes_widget import update_local_node_heartbeat
from modules.git_sync import run_git_sync_once


def append_event(event_type: str, details: dict):
    ensure_directories()
    record = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "env": HOSTNAME,
        "type": event_type,
        **details
    }
    with open(EVENTS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def cmd_log_study(args):
    ensure_directories()
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {"estudos": {"questoes_feitas_hoje": 0, "disciplinas": []}}

    estudos = data.setdefault("estudos", {})
    estudos["questoes_feitas_hoje"] = int(estudos.get("questoes_feitas_hoje", 0)) + args.questions

    now_iso = datetime.now().isoformat(timespec="seconds")
    for d in estudos.get("disciplinas", []):
        if d.get("id") == args.subject or args.subject.lower() in d.get("nome", "").lower():
            d["ultimo_estudo"] = now_iso

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    append_event("study_session", {
        "subject": args.subject,
        "questions": args.questions,
        "topic": args.topic or ""
    })
    print(f"[HUD-CLI] Estudo registrado: +{args.questions} questões em '{args.subject}' ({args.topic}).")


def cmd_set_exam(args):
    ensure_directories()
    if not os.path.exists(DATA_PATH):
        print("[HUD-CLI] data.json não encontrado.")
        return
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    updated = False
    for d in data.get("estudos", {}).get("disciplinas", []):
        if d.get("id") == args.subject or args.subject.lower() in d.get("nome", "").lower():
            if args.grade is not None:
                d[args.exam.lower()] = float(args.grade)
            if args.date:
                d[f"data_{args.exam.lower()}"] = args.date
            updated = True

    if updated:
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        append_event("exam_update", {
            "subject": args.subject,
            "exam": args.exam,
            "grade": args.grade,
            "date": args.date
        })
        print(f"[HUD-CLI] Prova '{args.exam}' de '{args.subject}' atualizada com sucesso.")
    else:
        print(f"[HUD-CLI] Disciplina '{args.subject}' não encontrada.")


def cmd_log_writing(args):
    append_event("writing_sprint", {
        "words": args.words,
        "chapter": args.chapter or "UVC"
    })
    print(f"[HUD-CLI] Sessão de escrita registrada: {args.words} palavras em '{args.chapter}'.")


def cmd_ai_train(args):
    if args.stop:
        ai_state = {
            "active": False,
            "manual_override": False,
            "project": args.project or "",
            "command": "",
            "progress_hint": args.info or "Concluído"
        }
        update_local_node_heartbeat(custom_ai_training=ai_state)
        append_event("ai_train_stop", {"project": args.project, "info": args.info})
        print(f"[HUD-CLI] Treino de IA finalizado em {HOSTNAME}: {args.info}")
    else:
        ai_state = {
            "active": True,
            "manual_override": True,
            "project": args.project or "Modelo IA",
            "command": args.cmd or "",
            "progress_hint": args.info or "Em andamento...",
            "started_at": datetime.now().isoformat(timespec="seconds")
        }
        update_local_node_heartbeat(custom_ai_training=ai_state)
        append_event("ai_train_start", {"project": args.project, "info": args.info})
        print(f"[HUD-CLI] Treino de IA iniciado em {HOSTNAME}: {args.project} ({args.info})")


def cmd_sync(_args):
    update_local_node_heartbeat()
    ok, msg = run_git_sync_once(commit_prefix="chore(hud-cli): sync ecosystem data")
    print(f"[HUD-CLI] {msg} (success={ok})")


def main():
    parser = argparse.ArgumentParser(description="Vector-Prod-Maxxing HUD CLI Helper for Antigravity 2.0")
    sub = parser.add_subparsers(dest="subcmd")

    p_study = sub.add_parser("log-study", help="Log solved study questions and update subject timestamp")
    p_study.add_argument("--subject", required=True, help="calculo3, fisica2, met_numericos, sis_computacao, fisica_exp2")
    p_study.add_argument("--questions", type=int, default=1, help="Number of questions solved")
    p_study.add_argument("--topic", default="", help="Topic studied")

    p_exam = sub.add_parser("set-exam", help="Update exam grade or exam date")
    p_exam.add_argument("--subject", required=True)
    p_exam.add_argument("--exam", required=True, help="p1, p2, p3, vs, testes")
    p_exam.add_argument("--grade", type=float, default=None)
    p_exam.add_argument("--date", default=None, help="YYYY-MM-DD")

    p_write = sub.add_parser("log-writing", help="Log creative writing session")
    p_write.add_argument("--words", type=int, default=0)
    p_write.add_argument("--chapter", default="UVC")

    p_ai = sub.add_parser("ai-train", help="Update AI training status on current node")
    p_ai.add_argument("--start", action="store_true")
    p_ai.add_argument("--stop", action="store_true")
    p_ai.add_argument("--project", default="AI-Model")
    p_ai.add_argument("--cmd", default="")
    p_ai.add_argument("--info", default="")

    sub.add_parser("sync", help="Trigger immediate heartbeat + Git pull/commit/push")

    args = parser.parse_args()
    if args.subcmd == "log-study":
        cmd_log_study(args)
    elif args.subcmd == "set-exam":
        cmd_set_exam(args)
    elif args.subcmd == "log-writing":
        cmd_log_writing(args)
    elif args.subcmd == "ai-train":
        cmd_ai_train(args)
    elif args.subcmd == "sync":
        cmd_sync(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
