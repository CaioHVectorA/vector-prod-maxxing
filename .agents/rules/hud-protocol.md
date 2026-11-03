# Vector-Prod-Maxxing — Antigravity 2.0 Bidirectional HUD Protocol

Whenever the user chats with you in Antigravity 2.0 about college studies (Cálculo III, Física II, Métodos Numéricos, Sistemas de Computação, Física Experimental II), creative writing (UVC / Red Right Hand), or AI training runs across environments, keep the portable `data/` folder of this repository updated in real time.

## Quick Commands (`hud_cli.py`)

Use `python3 hud_cli.py` (or `python hud_cli.py` on Windows) from the root of `vector-prod-maxxing`:

- **Log Study / Solved Questions**:
  `python3 hud_cli.py log-study --subject <calculo3|fisica2|met_numericos|sis_computacao|fisica_exp2> --questions <N> --topic "<Topic>"`
- **Update Exam Grade or Date**:
  `python3 hud_cli.py set-exam --subject <id> --exam <p1|p2|p3|vs|testes> --grade <float> --date <YYYY-MM-DD>`
- **Log Writing Session**:
  `python3 hud_cli.py log-writing --words <N> --chapter "<Chapter>"`
- **Register AI Training on Current Environment/Node**:
  - Start: `python3 hud_cli.py ai-train --start --project "<Name>" --info "<Epoch/Loss/Info>"`
  - Stop: `python3 hud_cli.py ai-train --stop --project "<Name>" --info "<Result>"`
- **Force Git Auto-Sync**:
  `python3 hud_cli.py sync`
