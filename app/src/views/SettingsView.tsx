import React, { useState } from "react";
import { CheckCircle2, CloudUpload, Copy, Save, Terminal, XCircle } from "lucide-react";
import { api, copyToClipboard } from "../api";
import type { AgyStatus, AppData } from "../types";

interface SettingsViewProps {
  data: AppData;
  agyStatus: AgyStatus | null;
  onDataChange: (next: AppData) => void;
  onRefreshMetrics: () => Promise<void>;
  onNotify: (msg: string) => void;
}

export const SettingsView: React.FC<SettingsViewProps> = ({
  data,
  agyStatus,
  onDataChange,
  onRefreshMetrics,
  onNotify,
}) => {
  const [questoes, setQuestoes] = useState(data.daily_goals.questoes);
  const [leituraMin, setLeituraMin] = useState(data.daily_goals.leitura_min);
  const [focoMin, setFocoMin] = useState(data.daily_goals.foco_min);
  const [cliCommand, setCliCommand] = useState(data.agy_config.cli_command);
  const [terminalCmd, setTerminalCmd] = useState(data.agy_config.terminal_command);
  const [developDirs, setDevelopDirs] = useState(data.agy_config.develop_dirs.join("\n"));
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const next: AppData = {
        ...data,
        daily_goals: {
          questoes: Number(questoes) || 5,
          leitura_min: Number(leituraMin) || 45,
          foco_min: Number(focoMin) || 90,
        },
        agy_config: {
          ...data.agy_config,
          cli_command: cliCommand.trim() || "antigravity",
          terminal_command: terminalCmd.trim() || "x-terminal-emulator",
          develop_dirs: developDirs
            .split("\n")
            .map((s) => s.trim())
            .filter(Boolean),
        },
      };
      const saved = await api.saveAppData(next);
      onDataChange(saved);
      await onRefreshMetrics();
      onNotify("Configurações salvas!");
    } finally {
      setSaving(false);
    }
  };

  const handleGitSync = async () => {
    setSyncing(true);
    try {
      const msg = await api.gitSyncNow();
      onNotify(msg);
    } catch (e) {
      onNotify(`Erro no Git Sync: ${String(e)}`);
    } finally {
      setSyncing(false);
    }
  };

  const cliExamples = `# Ver consistência e matérias negligenciadas
python3 hud_cli.py stats

# Registrar leitura + questões
python3 hud_cli.py log-study --subject fisica3 --reading-min 40 --pages 12 --questions 3 --topic "Lei de Gauss"

# Importar lista de questões gerada por IA
python3 hud_cli.py add-questions --subject sinais_sistemas --file lista.json

# Registrar sessão de robótica / código
python3 hud_cli.py log-project --project rl-robot --category robotics --duration 60 --summary "Reward shaping"`;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
      <form
        onSubmit={handleSave}
        className="lg:col-span-7 rounded-xl border border-slate-800/90 bg-[#11141c] p-5 space-y-5"
      >
        <div>
          <h3 className="text-sm font-semibold text-slate-100">Metas Diárias de Consistência</h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Usadas para calcular o Score de Consistência e barras de progresso diárias.
          </p>
          <div className="grid grid-cols-3 gap-3 mt-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Leitura (min/dia)</label>
              <input
                type="number"
                min={5}
                value={leituraMin}
                onChange={(e) => setLeituraMin(Number(e.target.value))}
                className="w-full bg-[#0b0e14] border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-emerald-300"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Questões/dia</label>
              <input
                type="number"
                min={1}
                value={questoes}
                onChange={(e) => setQuestoes(Number(e.target.value))}
                className="w-full bg-[#0b0e14] border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-sky-300"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Foco total (min/dia)</label>
              <input
                type="number"
                min={15}
                value={focoMin}
                onChange={(e) => setFocoMin(Number(e.target.value))}
                className="w-full bg-[#0b0e14] border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-violet-300"
              />
            </div>
          </div>
        </div>

        <div className="pt-4 border-t border-slate-800/80 space-y-3">
          <h3 className="text-sm font-semibold text-slate-100">Integração Antigravity & Linux</h3>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Comando CLI Antigravity</label>
              <input
                value={cliCommand}
                onChange={(e) => setCliCommand(e.target.value)}
                placeholder="antigravity ou agy"
                className="w-full bg-[#0b0e14] border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-slate-100"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Terminal fallback</label>
              <input
                value={terminalCmd}
                onChange={(e) => setTerminalCmd(e.target.value)}
                placeholder="x-terminal-emulator"
                className="w-full bg-[#0b0e14] border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-slate-100"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">
              Diretórios de projetos (1 por linha)
            </label>
            <textarea
              rows={3}
              value={developDirs}
              onChange={(e) => setDevelopDirs(e.target.value)}
              className="w-full bg-[#0b0e14] border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-slate-200"
            />
          </div>
        </div>

        <div className="flex items-center justify-between pt-3 border-t border-slate-800/80">
          <button
            type="button"
            onClick={handleGitSync}
            disabled={syncing}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 font-medium"
          >
            <CloudUpload className="w-3.5 h-3.5 text-sky-400" />
            {syncing ? "Sincronizando..." : "Git Sync Agora"}
          </button>

          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-sky-500 text-slate-950 text-xs font-semibold hover:bg-sky-400"
          >
            <Save className="w-3.5 h-3.5" />
            {saving ? "Salvando..." : "Salvar Alterações"}
          </button>
        </div>
      </form>

      {/* Antigravity Status & CLI Cheatsheet */}
      <div className="lg:col-span-5 space-y-4">
        <div className="rounded-xl border border-slate-800/90 bg-[#11141c] p-4 space-y-2.5">
          <div className="flex items-center gap-2">
            <Terminal className="w-4 h-4 text-sky-400" />
            <h3 className="text-sm font-semibold text-slate-100">Status do Ecossistema</h3>
          </div>
          <div className="text-xs space-y-1.5 font-mono">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Antigravity CLI:</span>
              {agyStatus?.cli_available ? (
                <span className="flex items-center gap-1 text-emerald-300">
                  <CheckCircle2 className="w-3.5 h-3.5" /> {agyStatus.resolved_path}
                </span>
              ) : (
                <span className="flex items-center gap-1 text-amber-300">
                  <XCircle className="w-3.5 h-3.5" /> Fallback (copia prompt)
                </span>
              )}
            </div>
            <div className="text-[11px] text-slate-500 break-all">
              Repo: <span className="text-slate-300">{agyStatus?.repo_dir ?? "—"}</span>
            </div>
            <div className="text-[11px] text-slate-500">
              File Watcher: <span className="text-emerald-300">Ativo (data/ &amp; estudos/)</span>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-slate-800/90 bg-[#11141c] p-4 space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-100">Protocolo hud_cli.py</h3>
            <button
              onClick={async () => {
                await copyToClipboard(cliExamples);
                onNotify("Comandos copiados!");
              }}
              className="flex items-center gap-1 text-xs text-sky-400 hover:text-sky-300"
            >
              <Copy className="w-3.5 h-3.5" /> Copiar
            </button>
          </div>
          <pre className="bg-[#0b0e14] border border-slate-800 rounded-lg p-3 text-[11px] font-mono text-slate-300 overflow-x-auto whitespace-pre-wrap">
            {cliExamples}
          </pre>
        </div>
      </div>
    </div>
  );
};
