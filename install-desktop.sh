#!/usr/bin/env bash
set -euo pipefail

# Vector Prod Maxxing v2 — Instalador de Atalhos Linux (Área de Trabalho + Barra de Tarefas/Dock)
# Uso:
#   ./install-desktop.sh           -> Instala menu, área de trabalho, ícone, pin na dock GNOME e git hook
#   ./install-desktop.sh --no-pin  -> Instala tudo sem alterar favoritos da dock GNOME

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ID="vector-prod-maxxing"
DESKTOP_NAME="${APP_ID}.desktop"

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
APPS_DIR="$DATA_HOME/applications"
ICON_DIR="$DATA_HOME/icons/hicolor/128x128/apps"
ICON_SRC="$REPO_DIR/app/src-tauri/icons/icon.png"
ICON_DST="$ICON_DIR/${APP_ID}.png"
APP_DESKTOP="$APPS_DIR/$DESKTOP_NAME"

PIN_DOCK=1
for arg in "$@"; do
  case "$arg" in
    --no-pin) PIN_DOCK=0 ;;
  esac
done

# Descobre pasta da Área de Trabalho (respeita XDG pt-BR "Área de Trabalho" ou "Desktop")
resolve_desktop_dir() {
  if command -v xdg-user-dir >/dev/null 2>&1; then
    local d
    d="$(xdg-user-dir DESKTOP 2>/dev/null || true)"
    if [ -n "$d" ] && [ "$d" != "$HOME" ]; then
      echo "$d"
      return
    fi
  fi
  if [ -d "$HOME/Área de Trabalho" ]; then
    echo "$HOME/Área de Trabalho"
  else
    echo "$HOME/Desktop"
  fi
}

DESKTOP_DIR="$(resolve_desktop_dir)"
DESKTOP_SHORTCUT="$DESKTOP_DIR/$DESKTOP_NAME"

chmod +x "$REPO_DIR/launch.sh" "$REPO_DIR/run.sh" "$REPO_DIR/test.sh" 2>/dev/null || true

mkdir -p "$APPS_DIR" "$ICON_DIR" "$DESKTOP_DIR"

if [ -f "$ICON_SRC" ]; then
  cp "$ICON_SRC" "$ICON_DST"
fi

cat > "$APP_DESKTOP" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Vector Prod Maxxing
GenericName=Cockpit de Estudos e Robótica
Comment=Estudos, Consistência, Listas IA e Robótica com Auto-Reload integrado ao Antigravity
Exec=$REPO_DIR/launch.sh
Path=$REPO_DIR
Icon=$ICON_DST
Terminal=false
Categories=Development;Education;Utility;
Keywords=estudos;antigravity;tauri;robotica;produtividade;
StartupNotify=true
StartupWMClass=vector-prod-maxxing
Actions=Release;Test;

[Desktop Action Release]
Name=Abrir Binário Otimizado (Auto-Rebuild)
Exec=$REPO_DIR/launch.sh --release

[Desktop Action Test]
Name=Rodar Testes & Coverage
Exec=x-terminal-emulator -e bash -c 'cd "$REPO_DIR" && ./test.sh; echo ""; read -p "Pressione Enter para fechar..."'
EOF

chmod +x "$APP_DESKTOP"
cp "$APP_DESKTOP" "$DESKTOP_SHORTCUT"
chmod +x "$DESKTOP_SHORTCUT"

# Marca o atalho da Área de Trabalho como confiável no GNOME (evita popup "Não confiável")
if command -v gio >/dev/null 2>&1; then
  gio set "$DESKTOP_SHORTCUT" metadata::trusted true >/dev/null 2>&1 || true
fi

# Atualiza bancos de ícones e aplicativos do Linux
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -f -t "$DATA_HOME/icons/hicolor" >/dev/null 2>&1 || true
fi

# Fixa automaticamente na Barra de Tarefas / Dock do GNOME (Ubuntu) se disponível
pin_to_gnome_dock() {
  if ! command -v gsettings >/dev/null 2>&1; then
    return
  fi
  local current
  current="$(gsettings get org.gnome.shell favorite-apps 2>/dev/null || true)"
  if [ -z "$current" ] || [ "$current" = "@as []" ]; then
    return
  fi
  if echo "$current" | grep -q "'$DESKTOP_NAME'"; then
    echo "  [OK] Já fixado na barra de tarefas (GNOME Dock)."
    return
  fi
  local updated
  updated="$(python3 -c "
import ast, sys
favs = ast.literal_eval(sys.argv[1])
if sys.argv[2] not in favs:
    favs.append(sys.argv[2])
print(repr(favs))
" "$current" "$DESKTOP_NAME" 2>/dev/null || true)"
  if [ -n "$updated" ]; then
    if gsettings set org.gnome.shell favorite-apps "$updated" >/dev/null 2>&1; then
      echo "  [OK] Fixado na barra de tarefas (GNOME Dock)!"
    fi
  fi
}

if [ "$PIN_DOCK" -eq 1 ]; then
  pin_to_gnome_dock
fi

# Instala git post-merge hook para manter npm deps sincronizados após git pull
if [ -d "$REPO_DIR/.git/hooks" ]; then
  HOOK_FILE="$REPO_DIR/.git/hooks/post-merge"
  cat > "$HOOK_FILE" <<'HOOK'
#!/usr/bin/env bash
# Auto-sync frontend dependencies when package-lock.json changes on git pull
changed="$(git diff-tree -r --name-only --no-commit-id ORIG_HEAD HEAD 2>/dev/null || true)"
if echo "$changed" | grep -q "app/package"; then
  echo "[vector post-merge] package.json alterado — rodando npm install..."
  (cd app && npm install) || true
fi
HOOK
  chmod +x "$HOOK_FILE"
fi

echo ""
echo "============================================================"
echo " Vector Prod Maxxing instalado com sucesso no Linux!"
echo "============================================================"
echo "  Menu / Barra de Tarefas : $APP_DESKTOP"
echo "  Área de Trabalho        : $DESKTOP_SHORTCUT"
echo "  Ícone                   : $ICON_DST"
echo "  Modo padrão ao clicar   : Live Auto-Reload (Vite HMR + Cargo Watch)"
echo "  Botão direito no ícone  : 'Abrir Binário Otimizado (Auto-Rebuild)' ou 'Rodar Testes'"
echo ""
echo "Dica: verifique dependências do sistema rodando: ./launch.sh --check"
