#!/usr/bin/env python3
"""
Vector-Prod-Maxxing CLI (hud_cli.py) — Protocolo Bidirecional Antigravity <-> App Tauri.
Permite ao Antigravity registrar sessões de leitura/exercícios, importar listas de questões
geradas por IA, atualizar notas/ementa, registrar sessões de projetos/robótica e consultar métricas.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Optional

base_dir = os.path.dirname(os.path.realpath(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from core import git_sync, nodes, paths
from core.osinfo import HOSTNAME
from core.storage import append_event, iter_events, read_json, update_json, write_json

PROJECTS_FILE = os.path.join(paths.DATA_DIR, "projects.json")
QUESTOES_DIR = os.path.join(paths.DATA_DIR, "questoes")


def _find_subject_v2(data: dict, subject_id: str, semester: Optional[str] = None) -> tuple[Optional[str], Optional[dict]]:
    semesters = data.get("semesters", {})
    search_order = []
    if semester and semester in semesters:
        search_order.append(semester)
    active = data.get("active_semester")
    if active and active in semesters and active not in search_order:
        search_order.append(active)
    for k in semesters:
        if k not in search_order:
            search_order.append(k)

    target = subject_id.strip().lower()
    for sem_id in search_order:
        for d in semesters[sem_id].get("disciplinas", []):
            if d.get("id", "").lower() == target or target in d.get("nome", "").lower():
                return sem_id, d
    return None, None


def cmd_log_study(args):
    paths.ensure_dirs()
    now_iso = datetime.now().isoformat(timespec="seconds")
    questions = max(0, int(args.questions or 0))
    reading_min = max(0, int(args.reading_min or 0))
    pages = max(0, int(args.pages or 0))
    duration_min = max(0, int(args.duration or 0)) or reading_min
    mode = args.mode
    if not mode:
        if reading_min > 0 and questions > 0:
            mode = "misto"
        elif reading_min > 0:
            mode = "leitura"
        else:
            mode = "exercicios"

    found_name = args.subject

    def mutate(data: dict) -> None:
        nonlocal found_name
        _, subj = _find_subject_v2(data, args.subject, args.semester)
        if subj:
            found_name = subj.get("nome", args.subject)
            subj["ultimo_estudo"] = now_iso
            if reading_min > 0 or pages > 0:
                subj["ultima_leitura"] = now_iso
            if args.topic:
                for t in subj.get("topicos", []):
                    if args.topic.lower() in t.get("titulo", "").lower() or t.get("id", "").lower() == args.topic.lower():
                        t["questoes_resolvidas"] = int(t.get("questoes_resolvidas", 0)) + questions
                        if reading_min > 0 and t.get("status") == "nao_iniciado":
                            t["status"] = "lendo"
                        elif questions > 0 and t.get("status") in ("nao_iniciado", "lendo"):
                            t["status"] = "praticando"

    update_json(paths.DATA_FILE, mutate, default={})
    append_event(
        "study_session",
        subject=args.subject,
        questions=questions,
        reading_min=reading_min,
        pages=pages,
        duration_min=duration_min,
        mode=mode,
        topic=args.topic or "",
    )
    print(
        f"[VECTOR-CLI] Estudo registrado em '{found_name}': "
        f"+{questions} questões, +{reading_min} min leitura ({pages} págs), modo={mode}."
    )


def cmd_add_questions(args):
    paths.ensure_dirs()
    os.makedirs(QUESTOES_DIR, exist_ok=True)
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            incoming = json.load(f)
    else:
        raw = sys.stdin.read().strip()
        if not raw:
            print("[VECTOR-CLI] Erro: passe --file <caminho.json> ou envie JSON via stdin.", file=sys.stderr)
            sys.exit(1)
        incoming = json.loads(raw)

    if isinstance(incoming, dict):
        incoming = [incoming]
    if not isinstance(incoming, list):
        print("[VECTOR-CLI] Erro: o JSON deve ser uma lista de questões.", file=sys.stderr)
        sys.exit(1)

    qpath = os.path.join(QUESTOES_DIR, f"{args.subject}.json")
    existing = read_json(qpath, [])
    if not isinstance(existing, list):
        existing = []

    by_id = {q.get("id"): idx for idx, q in enumerate(existing) if q.get("id")}
    added = 0
    updated = 0
    for idx, q in enumerate(incoming):
        if not isinstance(q, dict) or not q.get("enunciado"):
            continue
        qid = q.get("id") or f"{args.subject}_ai_{int(datetime.now().timestamp())}_{idx}"
        normalized = {
            "id": qid,
            "topico": q.get("topico", "Geral"),
            "dificuldade": q.get("dificuldade", "media"),
            "enunciado": q["enunciado"],
            "dica": q.get("dica", ""),
            "gabarito": q.get("gabarito", ""),
            "status": q.get("status", "pendente"),
            "attempts": int(q.get("attempts", 0)),
        }
        if qid in by_id:
            prev = existing[by_id[qid]]
            normalized["status"] = prev.get("status", normalized["status"])
            normalized["attempts"] = prev.get("attempts", normalized["attempts"])
            existing[by_id[qid]] = normalized
            updated += 1
        else:
            existing.append(normalized)
            by_id[qid] = len(existing) - 1
            added += 1

    write_json(qpath, existing)
    append_event("questions_imported", subject=args.subject, added=added, updated=updated)
    print(f"[VECTOR-CLI] Banco '{args.subject}.json' atualizado: +{added} novas, {updated} atualizadas (total={len(existing)}).")


def cmd_set_exam(args):
    paths.ensure_dirs()
    found = {"ok": False}

    def mutate(data: dict) -> None:
        _, subj = _find_subject_v2(data, args.subject, args.semester)
        if not subj:
            return
        avaliacoes = subj.setdefault("avaliacoes", [])
        target = None
        for av in avaliacoes:
            if av.get("id", "").lower() == args.exam.lower() or av.get("nome", "").lower() == args.exam.lower():
                target = av
                break
        if target is None:
            target = {
                "id": args.exam.lower(),
                "nome": args.exam.upper(),
                "peso": float(args.peso if args.peso is not None else 1.0),
                "nota": None,
                "data": None,
            }
            avaliacoes.append(target)
        if args.grade is not None:
            target["nota"] = float(args.grade)
        if args.date is not None:
            target["data"] = args.date
        if args.peso is not None:
            target["peso"] = float(args.peso)
        found["ok"] = True

    update_json(paths.DATA_FILE, mutate, default={})
    if found["ok"]:
        append_event("exam_update", subject=args.subject, exam=args.exam, grade=args.grade, date=args.date)
        print(f"[VECTOR-CLI] Avaliação '{args.exam}' de '{args.subject}' atualizada.")
    else:
        print(f"[VECTOR-CLI] Disciplina '{args.subject}' não encontrada.", file=sys.stderr)
        sys.exit(1)


def cmd_update_topic(args):
    paths.ensure_dirs()
    found = {"ok": False, "title": ""}

    def mutate(data: dict) -> None:
        _, subj = _find_subject_v2(data, args.subject, args.semester)
        if not subj:
            return
        for t in subj.get("topicos", []):
            if t.get("id", "").lower() == args.topic.lower() or args.topic.lower() in t.get("titulo", "").lower():
                if args.status:
                    t["status"] = args.status
                if args.reading_done is not None:
                    t["leitura_concluida"] = args.reading_done
                found["ok"] = True
                found["title"] = t.get("titulo", "")
                return

    update_json(paths.DATA_FILE, mutate, default={})
    if found["ok"]:
        append_event("topic_update", subject=args.subject, topic=found["title"], status=args.status)
        print(f"[VECTOR-CLI] Tópico '{found['title']}' atualizado.")
    else:
        print(f"[VECTOR-CLI] Tópico '{args.topic}' não encontrado em '{args.subject}'.", file=sys.stderr)
        sys.exit(1)


def cmd_log_project(args):
    paths.ensure_dirs()
    duration_min = max(0, int(args.duration or 30))
    if args.next_action:
        def mutate(projs: Any) -> Any:
            if not isinstance(projs, list):
                return projs
            for p in projs:
                if p.get("id", "").lower() == args.project.lower() or p.get("repo_name", "").lower() == args.project.lower():
                    p["next_action"] = args.next_action
            return projs
        update_json(PROJECTS_FILE, mutate, default=[])

    append_event(
        "project_session",
        project=args.project,
        category=args.category,
        duration_min=duration_min,
        summary=args.summary or "",
    )
    print(f"[VECTOR-CLI] Sessão de projeto registrada: '{args.project}' ({duration_min} min) — {args.summary}")


def cmd_stats(_args):
    paths.ensure_dirs()
    data = read_json(paths.DATA_FILE, {})
    active_sem = data.get("active_semester", "2027.1")
    sem = data.get("semesters", {}).get(active_sem, {})
    disciplinas = sem.get("disciplinas", [])

    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    week_ago = (now - timedelta(days=7)).timestamp()

    q_today = 0
    r_today = 0
    q_week = 0
    r_week = 0
    per_subj: dict[str, dict[str, int]] = {}

    for ev in iter_events(since_ts=week_ago):
        ts = ev.get("ts") or ev.get("timestamp") or ""
        q = int(ev.get("questions") or 0)
        r = int(ev.get("reading_min") or 0)
        subj = ev.get("subject")
        if ts.startswith(today_str):
            q_today += q
            r_today += r
        q_week += q
        r_week += r
        if subj:
            bucket = per_subj.setdefault(subj, {"questions": 0, "reading_min": 0})
            bucket["questions"] += q
            bucket["reading_min"] += r

    summary = {
        "active_semester": active_sem,
        "today": {"questions": q_today, "reading_min": r_today, "goals": data.get("daily_goals", {})},
        "last_7_days": {"questions": q_week, "reading_min": r_week},
        "subjects": [
            {
                "id": d["id"],
                "nome": d["nome"],
                "prioridade": d.get("prioridade"),
                "ultimo_estudo": d.get("ultimo_estudo"),
                "ultima_leitura": d.get("ultima_leitura"),
                "week_questions": per_subj.get(d["id"], {}).get("questions", 0),
                "week_reading_min": per_subj.get(d["id"], {}).get("reading_min", 0),
            }
            for d in disciplinas
        ],
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


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
        print(f"[VECTOR-CLI] Treino de IA finalizado em {HOSTNAME}: {args.info}")
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
        print(f"[VECTOR-CLI] Treino de IA iniciado em {HOSTNAME}: {args.project} ({args.info})")


def cmd_sync(_args):
    paths.ensure_dirs()
    nodes.write_local_heartbeat()
    ok, msg = git_sync.sync_once(commit_prefix="chore(vector-cli): sync data")
    print(f"[VECTOR-CLI] {msg} (success={ok})")


def main():
    parser = argparse.ArgumentParser(description="Vector-Prod-Maxxing v2 CLI (Antigravity <-> Tauri App)")
    sub = parser.add_subparsers(dest="subcmd")

    p_study = sub.add_parser("log-study", help="Registrar sessão de estudo (exercícios e/ou leitura)")
    p_study.add_argument("--subject", required=True, help="ID da matéria (ex: fisica3, sinais_sistemas, eletromagnetismo, circuitos_ca, resmat, fisica_exp3, lab_ca)")
    p_study.add_argument("--questions", type=int, default=0, help="Número de questões resolvidas")
    p_study.add_argument("--reading-min", type=int, default=0, help="Minutos de leitura teórica")
    p_study.add_argument("--pages", type=int, default=0, help="Páginas lidas")
    p_study.add_argument("--duration", type=int, default=0, help="Duração total em minutos")
    p_study.add_argument("--mode", default="", choices=["", "exercicios", "leitura", "misto", "revisao"])
    p_study.add_argument("--topic", default="", help="Tópico estudado")
    p_study.add_argument("--semester", default=None)

    p_addq = sub.add_parser("add-questions", help="Importar lista de questões geradas por IA para data/questoes/<subject>.json")
    p_addq.add_argument("--subject", required=True)
    p_addq.add_argument("--file", default=None, help="Arquivo JSON (se omitido, lê de stdin)")

    p_exam = sub.add_parser("set-exam", help="Atualizar ou criar avaliação/nota/data")
    p_exam.add_argument("--subject", required=True)
    p_exam.add_argument("--exam", required=True, help="Ex: p1, p2, p3, vs, rel1")
    p_exam.add_argument("--grade", type=float, default=None)
    p_exam.add_argument("--date", default=None, help="YYYY-MM-DD")
    p_exam.add_argument("--peso", type=float, default=None)
    p_exam.add_argument("--semester", default=None)

    p_topic = sub.add_parser("update-topic", help="Atualizar status de um tópico da ementa")
    p_topic.add_argument("--subject", required=True)
    p_topic.add_argument("--topic", required=True, help="ID ou parte do título do tópico")
    p_topic.add_argument("--status", choices=["nao_iniciado", "lendo", "praticando", "dominado"], default=None)
    p_topic.add_argument("--reading-done", action="store_true", default=None)
    p_topic.add_argument("--semester", default=None)

    p_proj = sub.add_parser("log-project", help="Registrar sessão de código/robótica/hardware")
    p_proj.add_argument("--project", required=True)
    p_proj.add_argument("--category", default="code", choices=["code", "robotics", "hardware"])
    p_proj.add_argument("--duration", type=int, default=30)
    p_proj.add_argument("--summary", default="")
    p_proj.add_argument("--next-action", default=None)

    sub.add_parser("stats", help="Imprimir resumo JSON de consistência, metas e matérias")

    p_ai = sub.add_parser("ai-train", help="Atualizar status de treino de IA")
    p_ai.add_argument("--start", action="store_true")
    p_ai.add_argument("--stop", action="store_true")
    p_ai.add_argument("--project", default="AI-Model")
    p_ai.add_argument("--cmd", default="")
    p_ai.add_argument("--info", default="")

    sub.add_parser("sync", help="Sincronizar dados com o GitHub")

    args = parser.parse_args()
    handlers = {
        "log-study": cmd_log_study,
        "add-questions": cmd_add_questions,
        "set-exam": cmd_set_exam,
        "update-topic": cmd_update_topic,
        "log-project": cmd_log_project,
        "stats": cmd_stats,
        "ai-train": cmd_ai_train,
        "sync": cmd_sync,
    }
    fn = handlers.get(args.subcmd)
    if fn:
        fn(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
