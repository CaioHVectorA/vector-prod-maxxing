# Vector-Prod-Maxxing v2 — Protocolo Antigravity ↔ App Tauri (Linux)

Sempre que o usuário conversar no Antigravity sobre estudos (2027.1: `fisica3`, `fisica_exp3`, `sinais_sistemas`, `eletromagnetismo`, `circuitos_ca`, `resmat`, `lab_ca`; ou 2026.2: `fisica2`), enviar materiais de estudo, pedir listas de exercícios ou trabalhar em projetos de código/robótica (`sumo-app`, `rl-robot`, `vss-ironcup-rl`, `haxball-rl`), mantenha `data/` e `estudos/` atualizados em tempo real. O app Tauri observa `data/` e `estudos/` via `notify` e atualiza a tela automaticamente.

## Comandos Rápidos (`python3 hud_cli.py`)

- **Ver consistência e matérias negligenciadas**:
  `python3 hud_cli.py stats`
- **Registrar Estudo (Exercícios e/ou Leitura)**:
  `python3 hud_cli.py log-study --subject <id> --questions <N> --reading-min <MIN> --pages <P> --topic "<Tópico>"`
- **Importar Lista de Questões Gerada por IA (com LaTeX `$ ... $`)**:
  `python3 hud_cli.py add-questions --subject <id> --file <lista.json>` (ou via `stdin`)
  Formato esperado de cada item:
  `{"id": "f3_l2_q1", "topico": "...", "dificuldade": "facil|media|dificil", "enunciado": "...", "dica": "...", "gabarito": "..."}`
- **Atualizar Tópico da Ementa**:
  `python3 hud_cli.py update-topic --subject <id> --topic "<título ou id>" --status <nao_iniciado|lendo|praticando|dominado> --reading-done`
- **Atualizar Nota/Data de Prova**:
  `python3 hud_cli.py set-exam --subject <id> --exam <p1|p2|p3|vs|rel1> --grade <float> --date <YYYY-MM-DD>`
- **Registrar Sessão de Projeto / Robótica**:
  `python3 hud_cli.py log-project --project <id> --category <code|robotics|hardware> --duration <MIN> --summary "<resumo>" --next-action "<próximo passo>"`
- **Materiais de Estudo**:
  Salvar PDFs, resumos `.md` e listas diretamente em `estudos/<subject_id>/` — o app Tauri detecta e exibe automaticamente.
