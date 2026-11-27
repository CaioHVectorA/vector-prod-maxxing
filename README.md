# Vector Prod Maxxing v2 (Linux · Tauri + Rust + Antigravity)

Cockpit pessoal de produtividade, consistência nos estudos (leitura + listas IA com KaTeX), código e projetos de robótica/engenharia — integrado em mão dupla com o **Antigravity**.

## Setup em 1 comando (Linux)

### 1. Pré-requisitos de sistema (Ubuntu/Debian)
```bash
sudo apt-get install -y libwebkit2gtk-4.1-dev libgtk-3-dev librsvg2-dev libayatana-appindicator3-dev libssl-dev pkg-config patchelf
```

### 2. Instalar atalho na Área de Trabalho e na Barra de Tarefas (Dock)
```bash
./install-desktop.sh
```
O que isso faz automaticamente:
- Cria o atalho na **Área de Trabalho** (já marcado como confiável no GNOME).
- Instala no **Menu de Aplicativos** e **fixa na Barra de Tarefas / GNOME Dock** com ícone e `StartupWMClass` corretos.
- Configura o clique padrão para abrir via [`launch.sh`](launch.sh) em **Modo Live Auto-Reload**:
  - Editou React/CSS (`app/src/`) → atualiza na janela aberta instantaneamente (Vite HMR).
  - Editou Rust (`app/src-tauri/src/`) → recompila e recarrega automaticamente (Cargo watch).
  - Editou `data/` ou `estudos/` pelo Antigravity → atualiza em ~250 ms (`notify` watcher).
- Adiciona ações de botão direito no ícone:
  - **Abrir Binário Otimizado (Auto-Rebuild)**: inicia instantaneamente e recompila sozinho sempre que o hash SHA-256 do código mudar.
  - **Rodar Testes & Coverage**: executa `./test.sh`.
- Instala um git hook `post-merge` para rodar `npm install` automaticamente após `git pull` quando `package.json` mudar.

Para remover os atalhos: `./uninstall-desktop.sh`.

### Comandos úteis no terminal
```bash
./launch.sh --check    # Verifica Node, Cargo, Rust e webkit2gtk-4.1
./launch.sh            # Abre em modo Live Auto-Reload
./launch.sh --release  # Abre binário release (auto-rebuild se código mudou)
./test.sh              # Roda todos os testes + coverage (Rust, Vitest, Pytest)
```

## Arquitetura

- **`app/`** — App Desktop nativo Linux em **Tauri v2 (Rust)** + **React + TypeScript + Tailwind v4 + KaTeX**.
  - `src-tauri/src/metrics.rs`: motor de consistência (heatmap de 16 semanas, streak, score 0–100, equilíbrio leitura vs exercícios, radar de matérias negligenciadas).
  - `src-tauri/src/watcher.rs`: observador de arquivos (`notify`) em `data/` e `estudos/` — tudo que o Antigravity grava aparece na tela em tempo real.
  - `src-tauri/src/agy.rs`: ponte com a CLI do Antigravity (`antigravity` / `agy`) com fallback automático para terminal + cópia de prompt.
  - `src-tauri/src/scanner.rs`: scanner de materiais (`estudos/`), repositórios Git locais (`~/develop`), portas seriais Linux (`/dev/ttyUSB*`, `/dev/ttyACM*`) e `firmwares/`.
- **`data/`** — Estado portável versionável em Git:
  - `data/data.json`: semestres (`2027.1` pré-configurado com Física 3, Física Exp 3, Sinais e Sistemas, Eletromagnetismo, Circuitos CA, ResMat e Lab CA + `2026.2`), metas diárias, avaliações e ementa customizáveis.
  - `data/events.jsonl`: ledger append-only de todas as sessões de leitura, exercícios, questões e projetos.
  - `data/questoes/<materia>.json`: bancos de questões com suporte a LaTeX (`$...$` e `$$...$$`).
  - `data/projects.json`: projetos de código, IA/RL e robótica.
- **`hud_cli.py`** — CLI usada pelo Antigravity para registrar estudos, importar listas de questões IA, atualizar tópicos/notas e consultar métricas (`python3 hud_cli.py --help`).
