#!/usr/bin/env bash
set -euo pipefail

APP_ID="vector-prod-maxxing"
DESKTOP_NAME="${APP_ID}.desktop"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"

rm -f "$DATA_HOME/applications/$DESKTOP_NAME"
rm -f "$DATA_HOME/icons/hicolor/128x128/apps/${APP_ID}.png"

for d in "$HOME/Desktop" "$HOME/Área de Trabalho"; do
  rm -f "$d/$DESKTOP_NAME"
done
if command -v xdg-user-dir >/dev/null 2>&1; then
  xdg_desk="$(xdg-user-dir DESKTOP 2>/dev/null || true)"
  [ -n "$xdg_desk" ] && [ "$xdg_desk" != "$HOME" ] && rm -f "$xdg_desk/$DESKTOP_NAME"
fi

if command -v gsettings >/dev/null 2>&1; then
  current="$(gsettings get org.gnome.shell favorite-apps 2>/dev/null || true)"
  if echo "$current" | grep -q "'$DESKTOP_NAME'"; then
    updated="$(python3 -c "
import ast, sys
favs = [x for x in ast.literal_eval(sys.argv[1]) if x != sys.argv[2]]
print(repr(favs))
" "$current" "$DESKTOP_NAME" 2>/dev/null || true)"
    [ -n "$updated" ] && gsettings set org.gnome.shell favorite-apps "$updated" >/dev/null 2>&1 || true
  fi
fi

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$DATA_HOME/applications" >/dev/null 2>&1 || true
fi

echo "[vector] Atalhos da Área de Trabalho e Barra de Tarefas removidos."
