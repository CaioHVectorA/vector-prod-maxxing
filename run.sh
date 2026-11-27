#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export VECTOR_REPO_DIR="$REPO_DIR"

MODE="${1:-dev}"

cd "$REPO_DIR/app"

if [ ! -d "node_modules" ]; then
  echo "[vector] Instalando dependências frontend..."
  npm install
fi

if [ "$MODE" = "build" ]; then
  echo "[vector] Gerando build release do Tauri (Linux)..."
  npm run tauri build
else
  echo "[vector] Iniciando Vector Prod Maxxing (Tauri dev)..."
  npm run tauri dev
fi
