"""Regra global do Antigravity que liga o chat do agente ao HUD.

Instalada em ``~/.gemini/config/rules/`` com os caminhos *desta* máquina, para o
agente saber onde fica o repositório e usar ``hud_cli.py`` em qualquer PC.
"""

import os
from pathlib import Path

from core import paths
from core.osinfo import HOSTNAME, OS_LABEL, python_executable

RULE_PATH = Path.home() / ".gemini" / "config" / "rules" / "vector_hud.md"


def render_rule() -> str:
    cli = os.path.join(paths.REPO_DIR, "hud_cli.py")
    run = f'"{python_executable()}" "{cli}"'
    return f"""# Vector-Prod-Maxxing v2 — Protocolo Antigravity ↔ App Tauri (Linux)

Host `{HOSTNAME}` ({OS_LABEL}).

- Repositório: `{paths.REPO_DIR}`
- Dados: `{paths.DATA_FILE}` e `{paths.EVENTS_FILE}`
- Materiais: `{os.path.join(paths.REPO_DIR, "estudos")}/<subject_id>/`
- CLI: `{cli}`

## Matérias Ativas (2027.1)
`fisica3`, `fisica_exp3`, `sinais_sistemas`, `eletromagnetismo`, `circuitos_ca`, `resmat`, `lab_ca` (fechamento 2026.2: `fisica2`).

## Regras (aplicar automaticamente)

1. **Ver métricas e matérias negligenciadas**:
   `{run} stats`
2. **Estudos (Leitura + Exercícios)**:
   `{run} log-study --subject <id> --reading-min <MIN> --pages <P> --questions <N> --topic "<tópico>"`
3. **Importar listas de questões geradas por IA (LaTeX `$...$`)**:
   `{run} add-questions --subject <id> --file <lista.json>`
4. **Atualizar tópico da ementa / notas**:
   `{run} update-topic --subject <id> --topic "<título>" --status <nao_iniciado|lendo|praticando|dominado> --reading-done`
   `{run} set-exam --subject <id> --exam <p1|p2|p3|vs|rel1> --grade <nota> --date <YYYY-MM-DD>`
5. **Projetos de Código & Robótica**:
   `{run} log-project --project <id> --category <code|robotics|hardware> --duration <MIN> --summary "<resumo>" --next-action "<próximo passo>"`
6. O app Tauri observa `data/` e `estudos/` em tempo real (~250 ms). Para sincronizar com o GitHub: `{run} sync`
"""


def install_rule() -> bool:
    """Grava a regra só se o conteúdo mudou. Retorna True se gravou."""
    content = render_rule()
    try:
        if RULE_PATH.exists() and RULE_PATH.read_text(encoding="utf-8") == content:
            return False
        RULE_PATH.parent.mkdir(parents=True, exist_ok=True)
        RULE_PATH.write_text(content, encoding="utf-8", newline="\n")
        return True
    except OSError:
        return False
