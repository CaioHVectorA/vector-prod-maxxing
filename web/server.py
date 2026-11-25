#!/usr/bin/env python3
"""
24/7 Localhost Web Dashboard Server for Desktop HUD (web/server.py)
Delega toda lógica de negócios para ``core.*`` (zero chamadas diretas a subprocess).
"""

import json
import mimetypes
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from urllib.parse import unquote, urlsplit

BASE_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core import (
    bluetooth,
    focus,
    git_sync,
    gitutil,
    launchers,
    nodes,
    paths,
    projects,
    study,
    writing,
)
from core.logs import get_logger, setup_logging
from core.settings import WEB_HOST, WEB_PORT
from core.storage import read_json, write_json
from core.workspace import discover_develop_dir

log = get_logger("hud.web")

mimetypes.add_type("text/markdown; charset=utf-8", ".md")
mimetypes.add_type("application/pdf", ".pdf")


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class HUDRequestHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status: int = 200, content_type: str = "application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _send_json(self, payload, status: int = 200):
        self._set_headers(status, "application/json; charset=utf-8")
        self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_GET(self):
        route = urlsplit(self.path).path

        if route in ("/", "/index.html"):
            self._serve_file(os.path.join(paths.WEB_DIR, "index.html"), "text/html; charset=utf-8")
        elif route == "/simulador-fisica":
            self.send_response(302)
            self.send_header("Location", "/simulador-fisica/")
            self.end_headers()
        elif route.startswith("/simulador-fisica/"):
            rel = unquote(route[len("/simulador-fisica/"):]).lstrip("/") or "index.html"
            self._serve_static_under(paths.SIMULADOR_FISICA_DIR, rel)
        elif route.startswith("/estudos/"):
            rel = unquote(route[len("/estudos/"):]).lstrip("/")
            self._serve_static_under(paths.ESTUDOS_DIR, rel)
        elif route == "/focus.pac":
            if not os.path.exists(paths.PAC_FILE):
                focus.generate_pac_file()
            self._serve_file(paths.PAC_FILE, "application/x-ns-proxy-autoconfig")
        elif route == "/api/data":
            self._send_json(study.ensure_current_day())
        elif route == "/api/repos":
            self._send_json(projects.scan_repos())
        elif route == "/api/antigravity/projects":
            self._send_json(projects.scan_projects().get("projects", []))
        elif route == "/api/projects/pinned":
            self._send_json(projects.load_pinned())
        elif route == "/api/writing":
            self._send_json(writing.scan_writing())
        elif route == "/api/bluetooth/status":
            self._send_json(bluetooth.status())
        elif route == "/api/bluetooth/devices":
            self._send_json(bluetooth.devices())
        elif route == "/api/calc/files":
            self._serve_calc_files()
        elif route == "/api/fisica/files":
            self._serve_fisica_files()
        elif route == "/api/nodes":
            self._send_json({"status": "ok", "nodes": nodes.load_environments()})
        else:
            self._set_headers(404, "text/plain")
            self.wfile.write(b"Not Found")

    def do_POST(self):
        route = urlsplit(self.path).path
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            payload = {}

        if route == "/api/data":
            write_json(paths.DATA_FILE, payload)
            self._send_json({"status": "ok"})
        elif route == "/api/study/log":
            subject = str(payload.get("subject", "fisica2")).strip() or "fisica2"
            questions = max(0, int(payload.get("questions", 1)))
            topic = str(payload.get("topic", "")).strip()
            ok = study.record_session(subject, questions=questions, topic=topic)
            self._send_json({"status": "ok", "matched": ok, "questions": questions})
        elif route == "/api/projects/pinned":
            items = payload.get("projects", [])
            projects.save_pinned(items)
            self._send_json({"status": "ok", "count": len(items)})
        elif route == "/api/focus/start":
            focus.activate()
            self._send_json({"status": "ok", "focus": True})
        elif route == "/api/focus/stop":
            focus.deactivate()
            self._send_json({"status": "ok", "focus": False})
        elif route == "/api/git/push":
            self._handle_push(payload)
        elif route == "/api/git/sync":
            nodes.write_local_heartbeat()
            ok, msg = git_sync.sync_once()
            self._send_json({"status": "ok" if ok else "error", "message": msg})
        elif route in ("/api/open-ide", "/api/antigravity/open"):
            path = payload.get("path", "")
            if path and os.path.exists(path):
                launchers.open_in_ide(path)
            self._send_json({"status": "ok"})
        elif route == "/api/antigravity/terminal":
            path = payload.get("path", "")
            if path and os.path.exists(path):
                launchers.open_terminal(path)
            self._send_json({"status": "ok"})
        elif route == "/api/nodes/remote":
            ok = nodes.trigger_remote_control(payload)
            self._send_json({"status": "ok" if ok else "error"})
        elif route == "/api/writing/chapter":
            self._handle_create_chapter(payload)
        elif route == "/api/bluetooth/power":
            ok, msg = bluetooth.set_power(bool(payload.get("power", True)))
            self._send_json({"status": "ok" if ok else "error", "message": msg})
        elif route == "/api/bluetooth/scan":
            self._send_json(bluetooth.scan(seconds=5))
        elif route == "/api/bluetooth/connect":
            self._handle_bt_action(payload, bluetooth.connect)
        elif route == "/api/bluetooth/disconnect":
            self._handle_bt_action(payload, bluetooth.disconnect)
        elif route == "/api/bluetooth/pair":
            self._handle_bt_action(payload, bluetooth.pair)
        elif route in ("/api/calc/open", "/api/fisica/open"):
            self._handle_calc_open(payload)
        else:
            self._set_headers(404, "text/plain")
            self.wfile.write(b"Not Found")

    def _serve_static_under(self, base_dir: str, rel_path: str):
        base_real = os.path.realpath(base_dir)
        target_real = os.path.realpath(os.path.join(base_real, rel_path))
        if not (target_real == base_real or target_real.startswith(base_real + os.sep)):
            self._set_headers(403, "text/plain")
            self.wfile.write(b"Forbidden")
            return
        if os.path.isdir(target_real):
            target_real = os.path.join(target_real, "index.html")
        ctype, _ = mimetypes.guess_type(target_real)
        if not ctype:
            ctype = "application/octet-stream"
        elif (ctype.startswith("text/") or ctype == "application/json") and "charset=" not in ctype:
            ctype = f"{ctype}; charset=utf-8"
        self._serve_file(target_real, ctype)

    def _serve_file(self, filepath: str, content_type: str):
        if os.path.exists(filepath):
            with open(filepath, "rb") as f:
                content = f.read()
            self._set_headers(200, content_type)
            self.wfile.write(content)
        else:
            self._set_headers(404, "text/plain")
            self.wfile.write(b"File not found")

    def _serve_fisica_files(self):
        exams_meta = read_json(os.path.join(paths.SIMULADOR_FISICA_DIR, "exams.json"), []) or []
        by_pdf = {os.path.basename(e.get("pdfUrl", "")): e for e in exams_meta}
        items = []
        if os.path.isdir(paths.FISICA_P3_DIR):
            for fname in sorted(os.listdir(paths.FISICA_P3_DIR), reverse=True):
                if not fname.lower().endswith(".pdf"):
                    continue
                fp = os.path.join(paths.FISICA_P3_DIR, fname)
                meta = by_pdf.get(fname, {})
                try:
                    size_kb = round(os.path.getsize(fp) / 1024, 1)
                except OSError:
                    size_kb = 0.0
                items.append(
                    {
                        "id": meta.get("id", fname.replace(".pdf", "")),
                        "name": fname,
                        "semester": meta.get("semester", ""),
                        "path": fp,
                        "pdf_url": f"/estudos/fisica-2/P3/{fname}",
                        "size_kb": size_kb,
                        "total_pages": meta.get("totalPages", 0),
                        "total_questions": meta.get("totalQuestions", 15),
                        "has_gabarito": bool(meta.get("gabarito")),
                        "note": meta.get("note", ""),
                    }
                )
        self._send_json(items)

    def _handle_create_chapter(self, payload: dict):
        title = str(payload.get("title", "")).strip()
        if not title:
            self._send_json({"error": "Title required"}, status=400)
            return
        filepath = writing.create_chapter(title)
        self._send_json({"status": "ok", "filename": os.path.basename(filepath), "path": filepath})

    def _handle_bt_action(self, payload: dict, fn):
        mac = str(payload.get("mac", "")).strip()
        if not bluetooth.is_valid_mac(mac):
            self._send_json({"error": "MAC address inválido"}, status=400)
            return
        ok, msg = fn(mac)
        self._send_json({"status": "ok" if ok else "error", "message": msg})

    def _serve_calc_files(self):
        files_data = []
        if os.path.exists(paths.CALC_DIR):
            for root, _dirs, files in os.walk(paths.CALC_DIR):
                rel = os.path.relpath(root, paths.CALC_DIR)
                for f in sorted(files):
                    fp = os.path.join(root, f)
                    try:
                        size_kb = round(os.path.getsize(fp) / 1024, 1)
                    except OSError:
                        size_kb = 0.0
                    files_data.append(
                        {
                            "name": f,
                            "category": rel if rel != "." else "Geral",
                            "path": fp,
                            "size_kb": size_kb,
                            "is_pdf": f.endswith(".pdf"),
                        }
                    )
        self._send_json(files_data)

    def _handle_calc_open(self, payload: dict):
        path = payload.get("path", "")
        if path and os.path.exists(path):
            launchers.open_path(path)
            self._send_json({"status": "ok", "opened": path})
        else:
            self._send_json({"error": "File not found"}, status=404)

    def _handle_push(self, payload: dict):
        repo_name = payload.get("repo", "")
        if not repo_name:
            self._send_json({"error": "repo missing"}, status=400)
            return
        repo_path = os.path.join(discover_develop_dir(), repo_name)
        branch = gitutil.current_branch(repo_path) or "main"
        res = gitutil.git(repo_path, "push", "origin", branch, timeout=25.0)
        self._send_json(
            {
                "status": "ok" if res.ok else "error",
                "message": res.stdout if res.ok else (res.error or res.output),
            }
        )

    def log_message(self, format, *args):
        pass


def run_server():
    setup_logging("web")
    paths.ensure_dirs()
    try:
        server = ThreadingHTTPServer((WEB_HOST, WEB_PORT), HUDRequestHandler)
    except OSError as exc:
        log.info("Servidor Web na porta %s já está em execução (%s).", WEB_PORT, exc)
        return
    log.info("Desktop HUD Web Server 24/7 rodando em http://localhost:%s", WEB_PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
