#!/usr/bin/env python3
"""
HUD CLI Helper (hud_cli.py) for Antigravity 2.0 Chat <-> Desktop HUD Bidirectional Protocol
Usa ``core.study``, ``core.nodes``, ``core.storage`` e ``core.git_sync``.
"""

import argparse
import os
import sys
from datetime import datetime

base_dir = os.path.dirname(os.path.realpath(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from core import git_sync, nodes, paths, study
from core.osinfo import HOSTNAME
from core.storage import append_event


def cmd_log_study(args):
    paths.ensure_dirs()
    study.record_session(args.subject, questions=args.questions, topic=args.topic or "")
    print(f"[HUD-CLI] Estudo registrado: +{args.questions} questões em '{args.subject}' ({args.topic}).")


def cmd_set_exam(args):
    paths.ensure_dirs()
    ok = study.set_exam(args.subject, args.exam, grade=args.grade, date=args.date)
    if ok:
        print(f"[HUD-CLI] Prova '{args.exam}' de '{args.subject}' atualizada com sucesso.")
    else:
        print(f"[HUD-CLI] Disciplina '{args.subject}' não encontrada.")


def cmd_log_writing(args):
    paths.ensure_dirs()
    append_event("writing_sprint", words=args.words, chapter=args.chapter or "UVC")
    print(f"[HUD-CLI] Sessão de escrita registrada: {args.words} palavras em '{args.chapter}'.")


def cmd_ai_train(args):
    paths.ensure_dirs()
    if args.stop:
        ai_state = {
            "active": False,
            "manual_override": False,
            "project": args.project or "",
            "command": "",
            "progress_hint": args.info or "Concluído",
        }
        nodes.write_local_heartbeat(ai_override=ai_state)
        append_event("ai_train_stop", project=args.project, info=args.info)
        print(f"[HUD-CLI] Treino de IA finalizado em {HOSTNAME}: {args.info}")
    else:
        ai_state = {
            "active": True,
            "manual_override": True,
            "project": args.project or "Modelo IA",
            "command": args.cmd or "",
            "progress_hint": args.info or "Em andamento...",
            "started_at": datetime.now().isoformat(timespec="seconds"),
        }
        nodes.write_local_heartbeat(ai_override=ai_state)
        append_event("ai_train_start", project=args.project, info=args.info)
        print(f"[HUD-CLI] Treino de IA iniciado em {HOSTNAME}: {args.project} ({args.info})")


def cmd_sync(_args):
    paths.ensure_dirs()
    nodes.write_local_heartbeat()
    ok, msg = git_sync.sync_once(commit_prefix="chore(hud-cli): sync ecosystem data")
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
