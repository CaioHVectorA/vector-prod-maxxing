#!/usr/bin/env bash
set -euo pipefail

# Vector Prod Maxxing v2 — Smart Linux Launcher (.desktop & CLI safe)
# Suporta:
#   ./launch.sh            -> Modo Live Auto-Reload (Vite HMR + Cargo watch + File Watcher)
#   ./launch.sh --release  -> Modo Release com Auto-Rebuild por fingerprint SHA-256
#   ./launch.sh --fingerprint -> Imprime hash atual do código-fonte e sai
#   ./launch.sh --check    -> Verifica dependências do sistema e toolchain

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$REPO_DIR/app"
TAURI_DIR="$APP_DIR/src-tauri"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/vector-prod-maxxing"
LOG_FILE="$STATE_DIR/app.log"
LOCK_FILE="$STATE_DIR/app.lock"
FINGERPRINT_FILE="$STATE_DIR/release.fingerprint"
NPM_HASH_FILE="$STATE_DIR/package.fingerprint"
RELEASE_BIN="$TAURI_DIR/target/release/vector-prod-maxxing"

export VECTOR_REPO_DIR="$REPO_DIR"
mkdir -p "$STATE_DIR"

# 1. Bootstrap PATH (essencial quando aberto via atalho .desktop sem .bashrc)
bootstrap_env() {
  export PATH="$HOME/.cargo/bin:$HOME/.local/bin:/usr/local/bin:$PATH"
  if [ -f "$HOME/.cargo/env" ]; then
    # shellcheck disable=SC1091
    source "$HOME/.cargo/env"
  fi
  if [ -s "${NVM_DIR:-$HOME/.nvm}/nvm.sh" ]; then
    export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
    # shellcheck disable=SC1091
    source "$NVM_DIR/nvm.sh" --no-use >/dev/null 2>&1 || true
    nvm use default >/dev/null 2>&1 || true
  fi
  if [ -d "$HOME/.fnm" ]; then
    export PATH="$HOME/.fnm:$PATH"
  fi
  if [ -d "$HOME/.volta/bin" ]; then
    export PATH="$HOME/.volta/bin:$PATH"
  fi
}

notify() {
  local title="$1"
  local body="$2"
  local urgency="${3:-normal}"
  if command -v notify-send >/dev/null 2>&1; then
    notify-send -u "$urgency" -a "Vector Prod Maxxing" -i "vector-prod-maxxing" "$title" "$body" >/dev/null 2>&1 || true
  fi
}

compute_source_fingerprint() {
  (
    cd "$REPO_DIR"
    {
      find app/src app/src-tauri/src -type f 2>/dev/null
      for f in \
        app/index.html \
        app/package.json \
        app/vite.config.ts \
        app/tsconfig.json \
        app/src-tauri/Cargo.toml \
        app/src-tauri/tauri.conf.json \
        app/src-tauri/build.rs; do
        [ -f "$f" ] && echo "$f"
      done
    } | LC_ALL=C sort | xargs -r sha256sum | sha256sum | awk '{print $1}'
  )
}

compute_npm_fingerprint() {
  (
    cd "$APP_DIR"
    {
      [ -f package.json ] && sha256sum package.json
      [ -f package-lock.json ] && sha256sum package-lock.json
    } | sha256sum | awk '{print $1}'
  )
}

ensure_npm_deps() {
  local cur_hash prev_hash=""
  cur_hash="$(compute_npm_fingerprint)"
  [ -f "$NPM_HASH_FILE" ] && prev_hash="$(cat "$NPM_HASH_FILE" 2>/dev/null || true)"
  if [ ! -d "$APP_DIR/node_modules" ] || [ "$cur_hash" != "$prev_hash" ]; then
    echo "[vector] Sincronizando dependências frontend (npm install)..."
    (cd "$APP_DIR" && npm install)
    echo "$cur_hash" > "$NPM_HASH_FILE"
  fi
}

check_toolchain() {
  bootstrap_env
  local missing=0
  for cmd in node npm cargo rustc; do
    if command -v "$cmd" >/dev/null 2>&1; then
      echo "  [OK] $cmd -> $(command -v "$cmd")"
    else
      echo "  [FALTA] $cmd não encontrado no PATH"
      missing=1
    fi
  done
  if pkg-config --exists webkit2gtk-4.1 2>/dev/null; then
    echo "  [OK] webkit2gtk-4.1 -> $(pkg-config --modversion webkit2gtk-4.1)"
  else
    echo "  [FALTA] libwebkit2gtk-4.1-dev (instale com apt-get)"
    missing=1
  fi
  return "$missing"
}

focus_existing_if_running() {
  if [ -f "$LOCK_FILE" ]; then
    local pid
    pid="$(cat "$LOCK_FILE" 2>/dev/null || true)"
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      if command -v wmctrl >/dev/null 2>&1; then
        wmctrl -a "Vector Prod Maxxing" >/dev/null 2>&1 || true
      fi
      notify "Vector Prod Maxxing" "O app já está aberto (focado na tela)." "low"
      exit 0
    fi
  fi
}

MODE="live"
case "${1:-}" in
  --fingerprint)
    compute_source_fingerprint
    exit 0
    ;;
  --check)
    check_toolchain
    exit $?
    ;;
  --release)
    MODE="release"
    ;;
  --live|--dev|"")
    MODE="live"
    ;;
  *)
    echo "Uso: $0 [--live|--release|--fingerprint|--check]"
    exit 1
    ;;
esac

bootstrap_env
focus_existing_if_running

# Garante que temos node/cargo antes de tentar abrir
if ! command -v node >/dev/null 2>&1 || ! command -v cargo >/dev/null 2>&1; then
  notify "Vector Prod Maxxing — Erro" "Node.js ou Cargo não encontrados no PATH. Veja $LOG_FILE" "critical"
  echo "[vector] Erro: node ou cargo não encontrados no PATH=$PATH" >> "$LOG_FILE"
  exit 1
fi

echo "$$" > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

if [ "$MODE" = "release" ]; then
  {
    echo "=== [$(date -Iseconds)] Vector Prod Maxxing (release auto-rebuild) ==="
    ensure_npm_deps
    CUR_FP="$(compute_source_fingerprint)"
    PREV_FP=""
    [ -f "$FINGERPRINT_FILE" ] && PREV_FP="$(cat "$FINGERPRINT_FILE" 2>/dev/null || true)"

    if [ ! -x "$RELEASE_BIN" ] || [ "$CUR_FP" != "$PREV_FP" ]; then
      notify "Vector Prod Maxxing" "Código atualizado — recompilando versão otimizada..."
      echo "[vector] Fingerprint mudou ($PREV_FP -> $CUR_FP). Compilando..."
      (cd "$APP_DIR" && npm run build)
      (cd "$TAURI_DIR" && cargo build --release)
      echo "$CUR_FP" > "$FINGERPRINT_FILE"
      notify "Vector Prod Maxxing" "Compilação concluída! Abrindo app..."
    fi
  } >> "$LOG_FILE" 2>&1

  exec "$RELEASE_BIN" >> "$LOG_FILE" 2>&1
else
  # Modo Live Auto-Reload: Vite HMR (frontend instantâneo) + Tauri Watch (Rust auto-rebuild)
  notify "Vector Prod Maxxing" "Iniciando em modo Live Auto-Reload (atualiza ao salvar código)..." "low"
  {
    echo "=== [$(date -Iseconds)] Vector Prod Maxxing (live auto-reload) ==="
    ensure_npm_deps
  } >> "$LOG_FILE" 2>&1

  cd "$APP_DIR"
  exec npm run tauri dev >> "$LOG_FILE" 2>&1
fi
