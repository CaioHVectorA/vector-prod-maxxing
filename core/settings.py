"""Configuração de runtime (constantes compartilhadas por GUI, servidor e CLI)."""

import os

WEB_PORT = 8090
# 127.0.0.1 por padrão: o servidor expõe ações (abrir IDE/terminal, git push, foco).
# Para acessar de outro dispositivo da rede, defina HUD_BIND_HOST=0.0.0.0 conscientemente.
WEB_HOST = os.environ.get("HUD_BIND_HOST", "127.0.0.1")
HUD_LOCK_PORT = 48765  # trava de instância única da GUI

BOT_NAME = "Vector HUD Bot"
BOT_EMAIL = "bot@vector-hud.internal"
