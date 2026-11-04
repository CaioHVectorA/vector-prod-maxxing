"""Métricas e utilidades do projeto de escrita (UVC / Red Right Hand)."""

import glob
import os
import re
import unicodedata
from datetime import datetime
from typing import Dict, Set

from core import paths
from core.gitutil import git, is_repo
from core.storage import iter_events
from core.timeutil import workday_start
from core.workspace import find_project_subdir

BOOK_REL = "books/red-right-hand"
_EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"  # hash fixo da árvore vazia do git


def uvc_dir() -> str:
    return find_project_subdir("UVC")


def chapters_dir() -> str:
    return os.path.join(uvc_dir(), *BOOK_REL.split("/"), "capitulos")


def _count_words(text: str) -> int:
    return len(text.split())


def _words_written_today(repo: str, since_ts: float) -> tuple[int, Set[str]]:
    """Palavras líquidas adicionadas ao livro desde o início do dia de trabalho.

    Compara a árvore de trabalho com o último commit anterior ao corte (um único
    ``git diff``). Também conta capítulos novos ainda não rastreados pelo git.
    """
    words, changed = 0, set()
    cutoff = datetime.fromtimestamp(since_ts).strftime("%Y-%m-%d %H:%M:%S")

    base = git(repo, "rev-list", "-1", f"--before={cutoff}", "HEAD", timeout=10)
    base_rev = base.stdout.strip() if base.ok and base.stdout.strip() else _EMPTY_TREE

    diff = git(repo, "-c", "core.quotepath=off", "diff", "-U0", base_rev, "--", BOOK_REL, timeout=20)
    if diff.ok:
        current = ""
        for line in diff.stdout.splitlines():
            if line.startswith("+++ "):
                current = os.path.basename(line[6:].strip())
                if current:
                    changed.add(current)
            elif line.startswith("+") and not line.startswith("+++"):
                words += _count_words(line[1:])

    untracked = git(repo, "-c", "core.quotepath=off", "ls-files", "--others", "--exclude-standard", "--", BOOK_REL)
    if untracked.ok:
        for rel in untracked.stdout.splitlines():
            full = os.path.join(repo, rel)
            try:
                with open(full, "r", encoding="utf-8") as f:
                    words += _count_words(f.read())
                changed.add(os.path.basename(rel))
            except OSError:
                pass
    return words, changed


def scan_writing() -> Dict:
    """Capítulos, totais e palavras escritas hoje."""
    repo = uvc_dir()
    since = workday_start().timestamp()
    git_words, changed = (0, set())
    if is_repo(repo):
        git_words, changed = _words_written_today(repo, since)

    # Palavras registradas via CLI/IA. Usamos o maior valor entre git e eventos
    # para não contar duas vezes o mesmo texto (que aparece nos dois).
    logged_words = sum(
        int(ev.get("words") or 0)
        for ev in iter_events(since)
        if ev.get("type") in ("writing", "writing_sprint")
    )

    chapters, total = [], 0
    for fp in sorted(glob.glob(os.path.join(chapters_dir(), "*.md"))):
        fname = os.path.basename(fp)
        try:
            with open(fp, "r", encoding="utf-8") as f:
                words = _count_words(f.read())
            mtime = os.path.getmtime(fp)
        except OSError:
            continue
        total += words
        raw = fname[:-3]
        num, _, rest = raw.partition("-")
        chapters.append({
            "file": fp, "path": fp, "filename": fname, "num": num,
            "title": f"Cap. {num}: {(rest or raw).replace('-', ' ').title()}",
            "words": words, "mtime": mtime, "is_today": fname in changed,
        })

    def count(sub: str) -> int:
        return len(glob.glob(os.path.join(repo, "docs", sub, "*.md")))

    return {
        "book": "Red Right Hand",
        "total_words": total,
        "words_today": max(git_words, logged_words),
        "chapters": chapters,
        "uvc_exists": os.path.isdir(repo),
        "lore_count": count("lore"),
        "char_count": count("characters"),
        "factions_count": count("factions"),
    }


def slugify(title: str) -> str:
    """'Confronto em Severum!' -> 'confronto-em-severum' (remove acentos de verdade)."""
    ascii_ = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_.lower()).strip("-") or "capitulo"


def create_chapter(title: str) -> str:
    """Cria o arquivo do próximo capítulo e retorna o caminho."""
    title = title.strip()
    cap_dir = chapters_dir()
    os.makedirs(cap_dir, exist_ok=True)
    nums = [
        int(m.group(1))
        for f in os.listdir(cap_dir)
        if (m := re.match(r"(\d+)-", f))
    ]
    number = (max(nums) + 1) if nums else 0
    path = os.path.join(cap_dir, f"{number:02d}-{slugify(title)}.md")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(
                f"# Capítulo {number:02d} — {title}\n\n"
                f"*Universo UVC — Red Right Hand*\n"
                f"Data: {datetime.now():%d/%m/%Y}\n\n---\n\n[Inicie a cena aqui...]\n"
            )
    return path
