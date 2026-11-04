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
    return f"""# Vector-Prod-Maxxing — protocolo HUD ↔ Antigravity

Host `{HOSTNAME}` ({OS_LABEL}).

- Repositório: `{paths.REPO_DIR}`
- Dados: `{paths.DATA_FILE}` e `{paths.EVENTS_FILE}`
- CLI: `{cli}`

## Regras (aplicar sem o usuário pedir)

1. **Estudos (UFF)** — ao resolver questões/estudar uma matéria:
   `{run} log-study --subject <calculo3|fisica2|met_numericos|sis_computacao|fisica_exp2> --questions <N> --topic "<tópico>"`
   Notas/datas de prova:
   `{run} set-exam --subject <id> --exam <p1|p2|p3|vs|testes> --grade <nota> --date <YYYY-MM-DD>`
2. **Escrita (UVC)** — ao escrever/editar capítulos:
   `{run} log-writing --words <N> --chapter "<nome>"`
3. **Treino de IA** — ao iniciar/encerrar treinos:
   `{run} ai-train --start --project "<nome>" --info "<detalhes>"`
   `{run} ai-train --stop --info "<resumo>"`
4. O HUD observa os arquivos de dados e atualiza em ~200 ms. O sync com o GitHub é
   automático e em lote; para forçar: `{run} sync`
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
