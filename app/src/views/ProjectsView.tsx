import React, { useEffect, useState } from "react";
import {
  Bot,
  Code2,
  Cpu,
  FolderOpen,
  GitBranch,
  Plus,
  RefreshCw,
  Sparkles,
  Usb,
} from "lucide-react";
import { api } from "../api";
import type { GitRepoInfo, HardwareSnapshot, ProjectItem } from "../types";

interface ProjectsViewProps {
  projects: ProjectItem[];
  onProjectsChange: (next: ProjectItem[]) => void;
  onRefreshMetrics: () => Promise<void>;
  onLaunchAgy: (prompt: string, workingDir?: string) => Promise<void>;
  onNotify: (msg: string) => void;
}

export const ProjectsView: React.FC<ProjectsViewProps> = ({
  projects,
  onProjectsChange,
  onRefreshMetrics,
  onLaunchAgy,
  onNotify,
}) => {
  const [subTab, setSubTab] = useState<"projects" | "repos" | "hardware">("projects");
  const [repos, setRepos] = useState<GitRepoInfo[]>([]);
  const [hw, setHw] = useState<HardwareSnapshot>({ serial_devices: [], firmwares: [] });
  const [loadingScan, setLoadingScan] = useState(false);
  const [newProjOpen, setNewProjOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newCat, setNewCat] = useState<"robotics" | "code" | "hardware">("robotics");
  const [newDesc, setNewDesc] = useState("");

  const refreshSystem = async () => {
    setLoadingScan(true);
    try {
      const [r, h] = await Promise.all([api.scanRepos(), api.scanHardware()]);
      setRepos(r);
      setHw(h);
    } finally {
      setLoadingScan(false);
    }
  };

  useEffect(() => {
    refreshSystem();
  }, []);

  const handleUpdateNextAction = async (id: string, nextAction: string) => {
    const updated = projects.map((p) =>
      p.id === id ? { ...p, next_action: nextAction } : p
    );
    const saved = await api.saveProjects(updated);
    onProjectsChange(saved);
  };

  const handleAddProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    const slug = newName
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "");
    const item: ProjectItem = {
      id: slug,
      nome: newName.trim(),
      categoria: newCat,
      status: "ativo",
      prioridade: "media",
      stack: [],
      repo_name: slug,
      descricao: newDesc.trim(),
      next_action: "Definir próximos passos",
      pinned: true,
    };
    const saved = await api.saveProjects([...projects, item]);
    onProjectsChange(saved);
    setNewName("");
    setNewDesc("");
    setNewProjOpen(false);
    onNotify(`Projeto "${item.nome}" adicionado!`);
  };

  const handleQuickLog = async (p: ProjectItem) => {
    await api.logProjectSession({
      project_id: p.id,
      category: p.categoria,
      duration_min: 30,
      summary: p.next_action || "Sessão de desenvolvimento",
    });
    await onRefreshMetrics();
    onNotify(`+30 min registrados em ${p.nome}!`);
  };

  const findRepoFor = (p: ProjectItem) =>
    repos.find(
      (r) =>
        r.name.toLowerCase() === p.repo_name.toLowerCase() ||
        r.name.toLowerCase() === p.id.toLowerCase()
    );

  return (
    <div className="space-y-4">
      {/* Sub-navigation */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-1 bg-[#11141c] p-1 rounded-xl border border-slate-800">
          <button
            onClick={() => setSubTab("projects")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium ${
              subTab === "projects"
                ? "bg-slate-800 text-sky-300"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Bot className="w-3.5 h-3.5" /> Projetos & Robótica ({projects.length})
          </button>
          <button
            onClick={() => setSubTab("repos")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium ${
              subTab === "repos"
                ? "bg-slate-800 text-sky-300"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <GitBranch className="w-3.5 h-3.5" /> Repositórios Locais ({repos.length})
          </button>
          <button
            onClick={() => setSubTab("hardware")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium ${
              subTab === "hardware"
                ? "bg-slate-800 text-sky-300"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Cpu className="w-3.5 h-3.5" /> Serial & Firmwares ({hw.serial_devices.length})
          </button>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={refreshSystem}
            disabled={loadingScan}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-800 text-slate-200 hover:bg-slate-700 text-xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingScan ? "animate-spin" : ""}`} />
            Escanear
          </button>
          {subTab === "projects" && (
            <button
              onClick={() => setNewProjOpen((v) => !v)}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-sky-500 text-slate-950 text-xs font-semibold hover:bg-sky-400"
            >
              <Plus className="w-3.5 h-3.5" /> Novo Projeto
            </button>
          )}
        </div>
      </div>

      {newProjOpen && subTab === "projects" && (
        <form
          onSubmit={handleAddProject}
          className="rounded-xl border border-slate-800 bg-[#11141c] p-4 grid grid-cols-1 md:grid-cols-4 gap-2"
        >
          <input
            required
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Nome do projeto"
            className="bg-[#0b0e14] border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100"
          />
          <select
            value={newCat}
            onChange={(e) => setNewCat(e.target.value as "robotics" | "code" | "hardware")}
            className="bg-[#0b0e14] border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200"
          >
            <option value="robotics">Robótica / RL</option>
            <option value="code">Código / Software</option>
            <option value="hardware">Hardware / Embarcados</option>
          </select>
          <input
            value={newDesc}
            onChange={(e) => setNewDesc(e.target.value)}
            placeholder="Descrição curta"
            className="bg-[#0b0e14] border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200"
          />
          <button
            type="submit"
            className="rounded-lg bg-emerald-500 text-slate-950 text-xs font-semibold py-2"
          >
            Adicionar
          </button>
        </form>
      )}

      {subTab === "projects" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {projects.map((p) => {
            const repo = findRepoFor(p);
            return (
              <div
                key={p.id}
                className="rounded-xl border border-slate-800/90 bg-[#11141c] p-4 flex flex-col justify-between gap-3"
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      {p.categoria === "robotics" ? (
                        <Bot className="w-4 h-4 text-emerald-400" />
                      ) : p.categoria === "hardware" ? (
                        <Cpu className="w-4 h-4 text-amber-400" />
                      ) : (
                        <Code2 className="w-4 h-4 text-sky-400" />
                      )}
                      <h3 className="text-sm font-semibold text-slate-100">{p.nome}</h3>
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                      {p.categoria}
                    </span>
                  </div>

                  {p.descricao && (
                    <p className="mt-1.5 text-xs text-slate-400">{p.descricao}</p>
                  )}

                  {repo && (
                    <div className="mt-2.5 flex items-center gap-2 text-[11px] font-mono text-slate-400 bg-[#0b0e14] px-2.5 py-1.5 rounded-lg border border-slate-800/70">
                      <GitBranch className="w-3 h-3 text-sky-400 shrink-0" />
                      <span className="text-sky-300">{repo.branch}</span>
                      {repo.dirty_files > 0 && (
                        <span className="text-amber-300">• {repo.dirty_files} dirty</span>
                      )}
                      <span className="truncate text-slate-500 ml-auto">
                        {repo.last_commit_rel}
                      </span>
                    </div>
                  )}

                  <div className="mt-3">
                    <label className="block text-[10px] uppercase tracking-wider text-slate-500 mb-1">
                      Próximo passo
                    </label>
                    <input
                      defaultValue={p.next_action}
                      onBlur={(e) => {
                        if (e.target.value !== p.next_action) {
                          handleUpdateNextAction(p.id, e.target.value);
                        }
                      }}
                      className="w-full bg-[#0b0e14] border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-sky-500"
                    />
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-800/70">
                  <button
                    onClick={() =>
                      onLaunchAgy(
                        `Vamos trabalhar no projeto ${p.nome} (${p.categoria}). Próximo passo planejado: ${p.next_action}. Ao finalizar, registre a sessão com 'python3 hud_cli.py log-project --project ${p.id} --category ${p.categoria}'.`,
                        repo?.path
                      )
                    }
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-sky-500/15 border border-sky-500/35 text-sky-300 hover:bg-sky-500/25 text-xs font-medium"
                  >
                    <Sparkles className="w-3.5 h-3.5" /> Vibecodar no Agy
                  </button>
                  <button
                    onClick={() => handleQuickLog(p)}
                    className="px-2.5 py-1.5 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/25 text-xs"
                  >
                    +30m log
                  </button>
                  {repo && (
                    <button
                      onClick={() => api.openPath(repo.path)}
                      className="ml-auto p-1.5 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700"
                      title="Abrir pasta no sistema"
                    >
                      <FolderOpen className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {subTab === "repos" && (
        <div className="space-y-2">
          {repos.length === 0 ? (
            <div className="rounded-xl border border-slate-800 bg-[#11141c] p-8 text-center text-xs text-slate-400">
              Nenhum repositório Git encontrado nos diretórios configurados. Configure o caminho em
              Configurações.
            </div>
          ) : (
            repos.map((r) => (
              <div
                key={r.path}
                className="rounded-xl border border-slate-800/90 bg-[#11141c] p-3.5 flex flex-wrap items-center justify-between gap-3"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-slate-100">{r.name}</span>
                    <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-sky-500/10 text-sky-300">
                      {r.branch}
                    </span>
                    {r.dirty_files > 0 && (
                      <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-amber-500/15 text-amber-300">
                        {r.dirty_files} alterações
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-400 mt-1 truncate">
                    {r.last_commit_msg}{" "}
                    <span className="text-slate-500 font-mono">({r.last_commit_rel})</span>
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() =>
                      onLaunchAgy(`Abrir e continuar desenvolvimento no repo ${r.name}.`, r.path)
                    }
                    className="px-3 py-1.5 rounded-lg bg-sky-500/15 border border-sky-500/35 text-sky-300 text-xs font-medium hover:bg-sky-500/25"
                  >
                    Abrir no Agy
                  </button>
                  <button
                    onClick={() => api.openPath(r.path)}
                    className="p-2 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700"
                  >
                    <FolderOpen className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {subTab === "hardware" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          <div className="lg:col-span-5 rounded-xl border border-slate-800/90 bg-[#11141c] p-4 space-y-3">
            <div className="flex items-center gap-2">
              <Usb className="w-4 h-4 text-emerald-400" />
              <h3 className="text-sm font-semibold text-slate-100">
                Portas Seriais Linux (/dev/ttyUSB*, /dev/ttyACM*)
              </h3>
            </div>
            {hw.serial_devices.length === 0 ? (
              <p className="text-xs text-slate-500">
                Nenhuma placa conectada no momento. Conecte um ESP32 ou Arduino e clique em
                Escanear.
              </p>
            ) : (
              <div className="space-y-2">
                {hw.serial_devices.map((d) => (
                  <div
                    key={d.port}
                    className="rounded-lg bg-[#0b0e14] border border-emerald-500/25 p-3"
                  >
                    <div className="text-xs font-mono font-semibold text-emerald-300">
                      {d.port}
                    </div>
                    <div className="text-[11px] text-slate-400 mt-0.5">{d.board_hint}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="lg:col-span-7 rounded-xl border border-slate-800/90 bg-[#11141c] p-4 space-y-3">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-sky-400" />
              <h3 className="text-sm font-semibold text-slate-100">
                Biblioteca de Firmwares ({hw.firmwares.length})
              </h3>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {hw.firmwares.map((fw) => (
                <div
                  key={fw.path}
                  className="rounded-lg bg-[#0b0e14] border border-slate-800 p-3 flex items-center justify-between gap-2"
                >
                  <div className="min-w-0">
                    <span className="text-[10px] font-mono uppercase text-sky-400">
                      {fw.board}
                    </span>
                    <div className="text-xs font-semibold text-slate-100 truncate">
                      {fw.name}
                    </div>
                  </div>
                  <button
                    onClick={() => api.openPath(fw.path)}
                    className="p-1.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700"
                    title="Abrir pasta do firmware"
                  >
                    <FolderOpen className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
