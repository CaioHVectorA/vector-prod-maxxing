#!/usr/bin/env python3
"""
24/7 Localhost Web Dashboard Server for Desktop HUD
Runs on port 8090, serving config, study planner, engineering projects, Antigravity workspaces,
Cálculo III contents, Bluetooth device scanner/connection panel, writing, and focus controls.
"""

import os
import json
import sqlite3
import subprocess
import re
import glob
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from datetime import datetime, timedelta

PORT = 8090
CONFIG_DIR = os.path.expanduser("~/.config/desktop-hud")
DATA_PATH = os.path.join(CONFIG_DIR, "data.json")
PINNED_FILE = os.path.join(CONFIG_DIR, "pinned_projects.json")
PAC_FILE = os.path.join(CONFIG_DIR, "focus.pac")
DEVELOP_DIR = os.path.expanduser("~/develop")
UVC_DIR = os.path.join(DEVELOP_DIR, "UVC")
CALC_DIR = os.path.expanduser("~/Downloads/calc")
ANTIGRAVITY_DB = os.path.expanduser("~/.gemini/antigravity/conversation_summaries.db")
STORAGE_JSON = os.path.expanduser("~/.config/Antigravity IDE/User/globalStorage/storage.json")
IDE_BIN = "/home/usuario/.local/bin/antigravity-ide"
WEB_DIR = os.path.dirname(os.path.realpath(__file__))

import sys
BASE_DIR = os.path.dirname(WEB_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from modules.focus_manager import activate_focus_mode, deactivate_focus_mode, generate_pac_file


def get_daily_cutoff_iso() -> str:
    now = datetime.now()
    if now.hour >= 6:
        cutoff = now.replace(hour=6, minute=0, second=0, microsecond=0)
    else:
        cutoff = (now - timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)
    return cutoff.strftime("%Y-%m-%d %H:%M:%S")


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class HUDRequestHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self._serve_file(os.path.join(WEB_DIR, "index.html"), "text/html; charset=utf-8")
        elif self.path == "/focus.pac":
            if not os.path.exists(PAC_FILE):
                generate_pac_file()
            self._serve_file(PAC_FILE, "application/x-ns-proxy-autoconfig")
        elif self.path == "/api/data":
            self._serve_data()
        elif self.path == "/api/repos":
            self._serve_repos()
        elif self.path == "/api/antigravity/projects":
            self._serve_antigravity_projects()
        elif self.path == "/api/projects/pinned":
            self._serve_pinned_projects()
        elif self.path == "/api/writing":
            self._serve_writing()
        elif self.path == "/api/bluetooth/status":
            self._serve_bluetooth_status()
        elif self.path == "/api/bluetooth/devices":
            self._serve_bluetooth_devices()
        elif self.path == "/api/calc/files":
            self._serve_calc_files()
        else:
            self._set_headers(404, "text/plain")
            self.wfile.write(b"Not Found")

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            payload = {}

        if self.path == "/api/data":
            self._save_data(payload)
        elif self.path == "/api/projects/pinned":
            self._save_pinned_projects(payload)
        elif self.path == "/api/focus/start":
            self._handle_focus(True)
        elif self.path == "/api/focus/stop":
            self._handle_focus(False)
        elif self.path == "/api/git/push":
            self._handle_push(payload)
        elif self.path == "/api/open-ide" or self.path == "/api/antigravity/open":
            self._handle_open_ide(payload)
        elif self.path == "/api/antigravity/terminal":
            self._handle_open_terminal(payload)
        elif self.path == "/api/writing/chapter":
            self._handle_create_chapter(payload)
        elif self.path == "/api/bluetooth/power":
            self._handle_bluetooth_power(payload)
        elif self.path == "/api/bluetooth/scan":
            self._handle_bluetooth_scan()
        elif self.path == "/api/bluetooth/connect":
            self._handle_bluetooth_connect(payload)
        elif self.path == "/api/bluetooth/disconnect":
            self._handle_bluetooth_disconnect(payload)
        elif self.path == "/api/bluetooth/pair":
            self._handle_bluetooth_pair(payload)
        elif self.path == "/api/calc/open":
            self._handle_calc_open(payload)
        else:
            self._set_headers(404, "text/plain")
            self.wfile.write(b"Not Found")

    def _serve_file(self, filepath, content_type):
        if os.path.exists(filepath):
            with open(filepath, "rb") as f:
                content = f.read()
            self._set_headers(200, content_type)
            self.wfile.write(content)
        else:
            self._set_headers(404, "text/plain")
            self.wfile.write(b"File not found")

    def _serve_data(self):
        if os.path.exists(DATA_PATH):
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                content = f.read()
            self._set_headers(200, "application/json")
            self.wfile.write(content.encode("utf-8"))
        else:
            self._set_headers(200, "application/json")
            self.wfile.write(b"{}")

    def _save_data(self, data):
        os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        self._set_headers(200, "application/json")
        self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))

    def _serve_pinned_projects(self):
        pinned = []
        if os.path.exists(PINNED_FILE):
            try:
                with open(PINNED_FILE, "r", encoding="utf-8") as f:
                    pinned = json.load(f)
            except Exception:
                pinned = []
        self._set_headers(200, "application/json")
        self.wfile.write(json.dumps(pinned).encode("utf-8"))

    def _save_pinned_projects(self, payload):
        projects = payload.get("projects", [])
        os.makedirs(CONFIG_DIR, exist_ok=True)
        try:
            with open(PINNED_FILE, "w", encoding="utf-8") as f:
                json.dump(projects, f, indent=2)
            self._set_headers(200, "application/json")
            self.wfile.write(json.dumps({"status": "ok", "count": len(projects)}).encode("utf-8"))
        except Exception as e:
            self._set_headers(500, "application/json")
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

    def _serve_antigravity_projects(self):
        projects = {}
        # 1. Inspect conversation_summaries.db
        if os.path.exists(ANTIGRAVITY_DB):
            try:
                conn = sqlite3.connect(ANTIGRAVITY_DB)
                c = conn.cursor()
                c.execute("""
                    SELECT workspace_uris, project_id, title, last_modified_time, step_count
                    FROM conversation_summaries 
                    ORDER BY last_modified_time DESC
                """)
                for uris_raw, pid, title, last_mod, steps in c.fetchall():
                    try:
                        uris = json.loads(uris_raw) if uris_raw else []
                    except Exception:
                        uris = [uris_raw] if uris_raw else []
                    for uri in uris:
                        if uri.startswith("file://"):
                            path = uri.replace("file://", "")
                            if os.path.exists(path) and path != "/home/usuario":
                                name = os.path.basename(path)
                                if name not in projects:
                                    projects[name] = {
                                        "name": name,
                                        "path": path,
                                        "last_activity": last_mod,
                                        "last_title": title,
                                        "convo_count": 1,
                                        "total_steps": steps
                                    }
                                else:
                                    projects[name]["convo_count"] += 1
                                    projects[name]["total_steps"] += steps
                conn.close()
            except Exception:
                pass

        # 2. Inspect storage.json
        if os.path.exists(STORAGE_JSON):
            try:
                with open(STORAGE_JSON, "r", encoding="utf-8") as f:
                    sdata = json.load(f)
                    for w in sdata.get("profileAssociations", {}).get("workspaces", {}):
                        if w.startswith("file://"):
                            path = w.replace("file://", "")
                            if os.path.exists(path) and path != "/home/usuario":
                                name = os.path.basename(path)
                                if name not in projects:
                                    projects[name] = {
                                        "name": name,
                                        "path": path,
                                        "last_activity": "",
                                        "last_title": "",
                                        "convo_count": 0,
                                        "total_steps": 0
                                    }
            except Exception:
                pass

        # 3. Add ~/develop repos
        if os.path.isdir(DEVELOP_DIR):
            for item in sorted(os.listdir(DEVELOP_DIR)):
                p = os.path.join(DEVELOP_DIR, item)
                if os.path.isdir(os.path.join(p, ".git")):
                    if item not in projects:
                        projects[item] = {
                            "name": item,
                            "path": p,
                            "last_activity": "",
                            "last_title": "",
                            "convo_count": 0,
                            "total_steps": 0
                        }

        # Git info
        for name, p in projects.items():
            path = p["path"]
            git_dir = os.path.join(path, ".git")
            if os.path.isdir(git_dir):
                p["is_git"] = True
                try:
                    b_res = subprocess.run(["git", "-C", path, "branch", "--show-current"], capture_output=True, text=True, timeout=0.6)
                    p["branch"] = b_res.stdout.strip() or "main"
                    s_res = subprocess.run(["git", "-C", path, "status", "--porcelain"], capture_output=True, text=True, timeout=0.6)
                    p["dirty"] = len(s_res.stdout.strip().splitlines()) if s_res.stdout.strip() else 0
                except Exception:
                    p["branch"] = "main"
                    p["dirty"] = 0
            else:
                p["is_git"] = False
                p["branch"] = ""
                p["dirty"] = 0

        res_list = sorted(projects.values(), key=lambda x: (x.get("convo_count", 0), x.get("last_activity", "")), reverse=True)
        self._set_headers(200, "application/json")
        self.wfile.write(json.dumps(res_list).encode("utf-8"))

    def _serve_writing(self):
        cutoff_iso = get_daily_cutoff_iso()
        words_today = 0
        changed_files_today = set()

        if os.path.exists(UVC_DIR):
            try:
                res_log = subprocess.run(
                    ["git", "-C", UVC_DIR, "log", f"--since={cutoff_iso}", "--name-only", "--format="],
                    capture_output=True, text=True, timeout=1.2
                )
                if res_log.returncode == 0 and res_log.stdout.strip():
                    for line in res_log.stdout.strip().splitlines():
                        if line.strip():
                            changed_files_today.add(os.path.basename(line.strip()))
                    res_diff = subprocess.run(
                        ["git", "-C", UVC_DIR, "log", f"--since={cutoff_iso}", "-p", "--", "books/red-right-hand/"],
                        capture_output=True, text=True, timeout=1.2
                    )
                    for line in res_diff.stdout.splitlines():
                        if line.startswith("+") and not line.startswith("+++"):
                            words_today += len(line[1:].split())
            except Exception:
                pass

            try:
                res_diff = subprocess.run(
                    ["git", "-C", UVC_DIR, "diff", "HEAD", "--", "books/red-right-hand/"],
                    capture_output=True, text=True, timeout=1.2
                )
                if res_diff.returncode == 0 and res_diff.stdout.strip():
                    for line in res_diff.stdout.splitlines():
                        if line.startswith("+") and not line.startswith("+++"):
                            words_today += len(line[1:].split())
                    res_names = subprocess.run(
                        ["git", "-C", UVC_DIR, "diff", "--name-only", "HEAD", "--", "books/red-right-hand/"],
                        capture_output=True, text=True, timeout=1.2
                    )
                    for line in res_names.stdout.splitlines():
                        if line.strip():
                            changed_files_today.add(os.path.basename(line.strip()))
            except Exception:
                pass

        cap_dir = os.path.join(UVC_DIR, "books", "red-right-hand", "capitulos")
        chapters = []
        total_words = 0
        if os.path.exists(cap_dir):
            for f in sorted(glob.glob(os.path.join(cap_dir, "*.md"))):
                fname = os.path.basename(f)
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        content = fp.read()
                        words = len(content.split())
                        total_words += words
                        chapters.append({
                            "filename": fname,
                            "path": f,
                            "words": words,
                            "is_today": (fname in changed_files_today),
                            "mtime": os.path.getmtime(f)
                        })
                except Exception:
                    pass

        out = {
            "book": "Red Right Hand",
            "total_words": total_words,
            "words_today": words_today,
            "chapters": chapters,
            "uvc_exists": os.path.exists(UVC_DIR)
        }
        self._set_headers(200, "application/json")
        self.wfile.write(json.dumps(out).encode("utf-8"))

    def _handle_create_chapter(self, payload):
        title = payload.get("title", "").strip()
        if not title:
            self._set_headers(400, "application/json")
            self.wfile.write(json.dumps({"error": "Title required"}).encode("utf-8"))
            return

        cap_dir = os.path.join(UVC_DIR, "books", "red-right-hand", "capitulos")
        os.makedirs(cap_dir, exist_ok=True)
        files = glob.glob(os.path.join(cap_dir, "*.md"))
        next_num = len(files)
        slug = title.lower().replace(" ", "-").replace("ç", "c").replace("ã", "a").replace("é", "e")
        filename = f"{next_num:02d}-{slug}.md"
        filepath = os.path.join(cap_dir, filename)

        if not os.path.exists(filepath):
            template = f"""# Capítulo {next_num:02d} — {title}

*Universo UVC — Red Right Hand*
Data: {datetime.now().strftime('%d/%m/%Y')}

---

[Inicie a cena aqui...]
"""
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(template)

        self._set_headers(200, "application/json")
        self.wfile.write(json.dumps({"status": "ok", "filename": filename, "path": filepath}).encode("utf-8"))

    def _serve_repos(self):
        repos = []
        if os.path.isdir(DEVELOP_DIR):
            for item in sorted(os.listdir(DEVELOP_DIR)):
                p = os.path.join(DEVELOP_DIR, item)
                if os.path.isdir(os.path.join(p, ".git")):
                    hud_file = os.path.join(p, ".hud.json")
                    has_hud = os.path.exists(hud_file)

                    res_stat = subprocess.run(
                        ["git", "-C", p, "status", "--porcelain"],
                        capture_output=True, text=True, timeout=0.8
                    )
                    uncommitted = len(res_stat.stdout.strip().splitlines()) if res_stat.stdout.strip() else 0

                    diff_lines = None
                    res_diff = subprocess.run(
                        ["git", "-C", p, "diff", "--shortstat"],
                        capture_output=True, text=True, timeout=0.8
                    )
                    if res_diff.returncode == 0 and res_diff.stdout.strip():
                        adds = sum(int(x) for x in re.findall(r"(\d+) insertion", res_diff.stdout))
                        dels = sum(int(x) for x in re.findall(r"(\d+) deletion", res_diff.stdout))
                        diff_lines = {"add": adds, "del": dels}

                    repos.append({
                        "name": item,
                        "path": p,
                        "has_hud": has_hud,
                        "uncommitted": uncommitted,
                        "diff_lines": diff_lines
                    })

        self._set_headers(200, "application/json")
        self.wfile.write(json.dumps(repos).encode("utf-8"))

    # Bluetooth Endpoints
    def _serve_bluetooth_status(self):
        try:
            res = subprocess.run(["bluetoothctl", "show"], capture_output=True, text=True, timeout=2.0)
            powered = "Powered: yes" in res.stdout
            name = "policorp"
            for line in res.stdout.splitlines():
                if line.strip().startswith("Name:"):
                    name = line.strip().split("Name:", 1)[1].strip()
            self._set_headers(200, "application/json")
            self.wfile.write(json.dumps({"powered": powered, "name": name}).encode("utf-8"))
        except Exception as e:
            self._set_headers(500, "application/json")
            self.wfile.write(json.dumps({"error": str(e), "powered": False}).encode("utf-8"))

    def _serve_bluetooth_devices(self):
        devices = []
        try:
            res = subprocess.run(["bluetoothctl", "devices"], capture_output=True, text=True, timeout=3.0)
            for line in res.stdout.strip().splitlines():
                parts = line.strip().split(None, 2)
                if len(parts) >= 3 and parts[0] == "Device":
                    mac = parts[1]
                    name = parts[2]
                    info_res = subprocess.run(["bluetoothctl", "info", mac], capture_output=True, text=True, timeout=2.0)
                    info_txt = info_res.stdout

                    connected = "Connected: yes" in info_txt
                    paired = "Paired: yes" in info_txt

                    icon = "generic"
                    name_low = name.lower()
                    if "audio" in info_txt.lower() or "headset" in info_txt.lower() or "tws" in name_low or "bt510" in name_low or "m10" in name_low:
                        icon = "audio"
                    elif "mouse" in name_low:
                        icon = "mouse"
                    elif "controller" in name_low:
                        icon = "controller"

                    rssi = None
                    m_rssi = re.search(r"RSSI:\s*(-?\d+)", info_txt)
                    if m_rssi:
                        rssi = int(m_rssi.group(1))

                    devices.append({
                        "mac": mac,
                        "name": name,
                        "connected": connected,
                        "paired": paired,
                        "icon": icon,
                        "rssi": rssi
                    })
        except Exception:
            pass

        self._set_headers(200, "application/json")
        self.wfile.write(json.dumps(devices).encode("utf-8"))

    def _handle_bluetooth_power(self, payload):
        turn_on = payload.get("power", True)
        cmd = "on" if turn_on else "off"
        try:
            if turn_on:
                subprocess.run(["/usr/sbin/rfkill", "unblock", "bluetooth"], capture_output=True)
            res = subprocess.run(["bluetoothctl", "power", cmd], capture_output=True, text=True, timeout=3.0)
            success = "succeeded" in res.stdout.lower() or res.returncode == 0
            self._set_headers(200, "application/json")
            self.wfile.write(json.dumps({"status": "ok" if success else "error", "message": res.stdout}).encode("utf-8"))
        except Exception as e:
            self._set_headers(500, "application/json")
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

    def _handle_bluetooth_scan(self):
        try:
            subprocess.run(["/usr/sbin/rfkill", "unblock", "bluetooth"], capture_output=True)
            subprocess.run(["bluetoothctl", "power", "on"], capture_output=True)
            # Run 5 second scan
            subprocess.run(["bluetoothctl", "--timeout", "5", "scan", "on"], capture_output=True, timeout=7.0)
            self._serve_bluetooth_devices()
        except Exception as e:
            self._set_headers(500, "application/json")
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

    def _handle_bluetooth_connect(self, payload):
        mac = payload.get("mac")
        if not mac:
            self._set_headers(400, "application/json")
            self.wfile.write(json.dumps({"error": "MAC address required"}).encode("utf-8"))
            return

        try:
            res = subprocess.run(["bluetoothctl", "connect", mac], capture_output=True, text=True, timeout=9.0)
            msg = res.stdout or res.stderr
            success = "Connection successful" in msg
            self._set_headers(200, "application/json")
            self.wfile.write(json.dumps({
                "status": "ok" if success else "error",
                "message": "Conectado com sucesso!" if success else f"Falha ao conectar: {msg.strip()}"
            }).encode("utf-8"))
        except Exception as e:
            self._set_headers(500, "application/json")
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

    def _handle_bluetooth_disconnect(self, payload):
        mac = payload.get("mac")
        if not mac:
            self._set_headers(400, "application/json")
            self.wfile.write(json.dumps({"error": "MAC address required"}).encode("utf-8"))
            return

        try:
            res = subprocess.run(["bluetoothctl", "disconnect", mac], capture_output=True, text=True, timeout=5.0)
            msg = res.stdout or res.stderr
            success = "Successful disconnected" in msg or "disconnection successful" in msg.lower() or res.returncode == 0
            self._set_headers(200, "application/json")
            self.wfile.write(json.dumps({
                "status": "ok" if success else "error",
                "message": "Desconectado!" if success else msg
            }).encode("utf-8"))
        except Exception as e:
            self._set_headers(500, "application/json")
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

    def _handle_bluetooth_pair(self, payload):
        mac = payload.get("mac")
        if not mac:
            self._set_headers(400, "application/json")
            self.wfile.write(json.dumps({"error": "MAC address required"}).encode("utf-8"))
            return

        try:
            res = subprocess.run(["bluetoothctl", "pair", mac], capture_output=True, text=True, timeout=8.0)
            msg = res.stdout or res.stderr
            success = "Pairing successful" in msg or res.returncode == 0
            self._set_headers(200, "application/json")
            self.wfile.write(json.dumps({
                "status": "ok" if success else "error",
                "message": "Pareado com sucesso!" if success else msg
            }).encode("utf-8"))
        except Exception as e:
            self._set_headers(500, "application/json")
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

    # Cálculo III Files
    def _serve_calc_files(self):
        files_data = []
        if os.path.exists(CALC_DIR):
            for root, dirs, files in os.walk(CALC_DIR):
                rel = os.path.relpath(root, CALC_DIR)
                for f in sorted(files):
                    fp = os.path.join(root, f)
                    files_data.append({
                        "name": f,
                        "category": rel if rel != "." else "Geral",
                        "path": fp,
                        "size_kb": round(os.path.getsize(fp) / 1024, 1),
                        "is_pdf": f.endswith(".pdf")
                    })
        self._set_headers(200, "application/json")
        self.wfile.write(json.dumps(files_data).encode("utf-8"))

    def _handle_calc_open(self, payload):
        path = payload.get("path")
        if path and os.path.exists(path):
            subprocess.Popen(["xdg-open", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self._set_headers(200, "application/json")
            self.wfile.write(json.dumps({"status": "ok", "opened": path}).encode("utf-8"))
        else:
            self._set_headers(404, "application/json")
            self.wfile.write(json.dumps({"error": "File not found"}).encode("utf-8"))

    def _handle_focus(self, enable: bool):
        try:
            if enable:
                activate_focus_mode()
            else:
                deactivate_focus_mode()
            self._set_headers(200, "application/json")
            self.wfile.write(json.dumps({"status": "ok", "focus": enable}).encode("utf-8"))
        except Exception as e:
            self._set_headers(500, "application/json")
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

    def _handle_push(self, payload):
        repo_name = payload.get("repo")
        if not repo_name:
            self._set_headers(400, "application/json")
            self.wfile.write(json.dumps({"error": "repo missing"}).encode("utf-8"))
            return

        repo_path = os.path.join(DEVELOP_DIR, repo_name)
        try:
            res = subprocess.run(
                ["git", "-C", repo_path, "push", "origin", "main"],
                capture_output=True, text=True, timeout=20.0
            )
            msg = res.stdout if res.returncode == 0 else (res.stderr or res.stdout)
            self._set_headers(200, "application/json")
            self.wfile.write(json.dumps({"status": "ok" if res.returncode == 0 else "error", "message": msg}).encode("utf-8"))
        except Exception as e:
            self._set_headers(500, "application/json")
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

    def _handle_open_ide(self, payload):
        path = payload.get("path")
        if path and os.path.exists(path):
            subprocess.Popen([IDE_BIN, path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self._set_headers(200, "application/json")
        self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))

    def _handle_open_terminal(self, payload):
        path = payload.get("path")
        if path and os.path.exists(path):
            subprocess.Popen(["gnome-terminal", f"--working-directory={path}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self._set_headers(200, "application/json")
        self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))

    def log_message(self, format, *args):
        pass


def run_server():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), HUDRequestHandler)
    print(f"⚡ Desktop HUD Web Server 24/7 rodando em http://localhost:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
