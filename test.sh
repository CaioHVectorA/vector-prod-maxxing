#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== [1/3] Rust / Tauri Backend Tests ==="
(cd "$REPO_DIR/app/src-tauri" && cargo test)

echo ""
echo "=== [2/3] Frontend React / TypeScript Tests + V8 Coverage ==="
(cd "$REPO_DIR/app" && npm run test:coverage)

echo ""
echo "=== [3/3] Python Antigravity CLI Tests + Coverage ==="
(cd "$REPO_DIR" && python3 -m pytest tests/ --cov=hud_cli --cov-report=term-missing)

echo ""
echo "ALL TEST SUITES PASSED."
