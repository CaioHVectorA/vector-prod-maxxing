import React, { useCallback, useEffect, useState } from "react";
import {
  BookOpen,
  Bot,
  Calculator,
  CloudUpload,
  Flame,
  LayoutDashboard,
  RefreshCw,
  Settings,
  Sparkles,
} from "lucide-react";
import { api, copyToClipboard } from "./api";
import type { AgyStatus, AppData, MetricsSummary, ProjectItem } from "./types";
import { DashboardView } from "./views/DashboardView";
import { ProjectsView } from "./views/ProjectsView";
import { QuestionsView } from "./views/QuestionsView";
import { SettingsView } from "./views/SettingsView";
import { StudiesView } from "./views/StudiesView";

type Tab = "dashboard" | "studies" | "questions" | "projects" | "settings";

export const App: React.FC = () => {
  const [tab, setTab] = useState<Tab>("dashboard");
  const [data, setData] = useState<AppData | null>(null);
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [agyStatus, setAgyStatus] = useState<AgyStatus | null>(null);
  const [focusedSubjectId, setFocusedSubjectId] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const notify = useCallback((msg: string) => {
    setToast(msg);
    window.setTimeout(() => {
      setToast((prev) => (prev === msg ? null : prev));
    }, 4200);
  }, []);

  const loadAll = useCallback(async () => {
    try {
      const [appData, met, projs, agy] = await Promise.all([
        api.getAppData(),
        api.getMetrics(),
        api.getProjects(),
        api.getAgyStatus(),
      ]);
      setData(appData);
      setMetrics(met);
      setProjects(projs);
      setAgyStatus(agy);
      setError(null);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  // Live file-watcher sync when Antigravity updates data/ or estudos/
  useEffect(() => {
    let unlisten: (() => void) | undefined;
    api.onWorkspaceChanged(() => {
      loadAll();
    }).then((fn) => {
      unlisten = fn;
    });
    return () => {
      if (unlisten) unlisten();
    };
  }, [loadAll]);

  const refreshMetrics = useCallback(async () => {
    const met = await api.getMetrics();
    setMetrics(met);
  }, []);

  const handleLaunchAgy = useCallback(
    async (prompt: string, workingDir?: string) => {
      await copyToClipboard(prompt);
      try {
        const res = await api.launchAgy(workingDir ?? null, prompt);
        notify(res);
      } catch (e) {
        notify(String(e));
      }
    },
    [notify]
  );

  const handleLogStudy = useCallback(
    async (payload: {
      subject_id: string;
      questions: number;
      reading_min: number;
      pages: number;
      duration_min: number;
      mode: string;
      topic: string;
    }) => {
      const met = await api.logStudySession(payload);
      setMetrics(met);
      const nextData = await api.getAppData();
      setData(nextData);
      notify(
        `Sessão registrada (${payload.mode}): +${payload.reading_min}m leitura, +${payload.questions} questões.`
      );
    },
    [notify]
  );

  const handleLogProject = useCallback(
    async (payload: {
      project_id: string;
      category: string;
      duration_min: number;
      summary: string;
    }) => {
      const met = await api.logProjectSession(payload);
      setMetrics(met);
      notify(`Sessão de projeto registrada (+${payload.duration_min}m).`);
    },
    [notify]
  );

  const activeSubjects =
    data?.semesters[data.active_semester]?.disciplinas ?? [];

  if (loading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-[#090b10] text-slate-300 text-sm font-mono">
        Carregando Vector Prod Maxxing...
      </div>
    );
  }

  if (error || !data || !metrics) {
    return (
      <div className="h-screen w-screen flex flex-col items-center justify-center bg-[#090b10] text-slate-200 p-6 gap-3">
        <div className="text-rose-400 font-semibold">Erro ao carregar workspace</div>
        <pre className="text-xs font-mono bg-[#11141c] border border-slate-800 p-4 rounded-xl max-w-xl overflow-auto">
          {error || "Dados não encontrados"}
        </pre>
        <button
          onClick={loadAll}
          className="px-4 py-2 rounded-lg bg-sky-500 text-slate-950 text-xs font-semibold"
        >
          Tentar novamente
        </button>
      </div>
    );
  }

  const navItems: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: "dashboard", label: "Consistência", icon: <LayoutDashboard className="w-4 h-4" /> },
    { id: "studies", label: "Estudos", icon: <BookOpen className="w-4 h-4" /> },
    { id: "questions", label: "Questões IA", icon: <Calculator className="w-4 h-4" /> },
    { id: "projects", label: "Código & Robótica", icon: <Bot className="w-4 h-4" /> },
    { id: "settings", label: "Config & Agy", icon: <Settings className="w-4 h-4" /> },
  ];

  return (
    <div className="h-screen w-screen flex bg-[#090b10] text-slate-100 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-60 shrink-0 border-r border-slate-800/80 bg-[#0d1017] flex flex-col justify-between p-4">
        <div className="space-y-6">
          <div className="flex items-center gap-2.5 px-1">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-sky-400 to-emerald-400 flex items-center justify-center text-slate-950 font-black text-sm">
              V
            </div>
            <div>
              <div className="text-sm font-bold tracking-tight text-slate-100 leading-none">
                Vector Maxxing
              </div>
              <div className="text-[11px] font-mono text-slate-500 mt-0.5">
                Semestre {data.active_semester}
              </div>
            </div>
          </div>

          <nav className="space-y-1">
            {navItems.map((item) => {
              const active = tab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setTab(item.id)}
                  className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-xs font-medium transition ${
                    active
                      ? "bg-sky-500/15 text-sky-300 border border-sky-500/30"
                      : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-200 border border-transparent"
                  }`}
                >
                  {item.icon}
                  {item.label}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Bottom Mini Consistency Card + Agy Quick Launch */}
        <div className="space-y-2.5">
          <div className="rounded-xl border border-slate-800/80 bg-[#11141c] p-3 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-1 text-amber-300 font-semibold">
                <Flame className="w-3.5 h-3.5" /> {metrics.current_streak}d streak
              </span>
              <span className="font-mono text-sky-300 font-semibold">
                {metrics.consistency_score}/100
              </span>
            </div>
            <div className="text-[11px] font-mono text-slate-400 flex justify-between">
              <span>Leit: {metrics.today_reading_min}m</span>
              <span>Quest: {metrics.today_questions}</span>
            </div>
          </div>

          <button
            onClick={() =>
              handleLaunchAgy(
                "Abra minha sessão de produtividade no vector-prod-maxxing. Rode 'python3 hud_cli.py stats' e me diga qual matéria priorizar hoje."
              )
            }
            className="w-full flex items-center justify-center gap-1.5 py-2.5 rounded-xl bg-sky-500 text-slate-950 hover:bg-sky-400 text-xs font-semibold transition"
          >
            <Sparkles className="w-3.5 h-3.5" /> Abrir Antigravity
          </button>
        </div>
      </aside>

      {/* Main Workspace */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Bar */}
        <header className="h-14 shrink-0 border-b border-slate-800/80 bg-[#0d1017]/80 backdrop-blur-sm px-6 flex items-center justify-between">
          <div>
            <h1 className="text-sm font-semibold text-slate-100">
              {navItems.find((n) => n.id === tab)?.label}
            </h1>
            <p className="text-[11px] text-slate-500">
              {data.semesters[data.active_semester]?.nome ?? data.active_semester}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="hidden sm:inline-flex items-center gap-1.5 text-[11px] font-mono px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-300">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Live Sync (data/)
            </span>
            <button
              onClick={loadAll}
              className="p-2 rounded-lg bg-slate-800/70 text-slate-300 hover:bg-slate-800"
              title="Recarregar dados"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={async () => {
                try {
                  const res = await api.gitSyncNow();
                  notify(res);
                } catch (e) {
                  notify(`Git Sync: ${String(e)}`);
                }
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800/70 hover:bg-slate-800 text-xs text-slate-200"
              title="Sincronizar com GitHub"
            >
              <CloudUpload className="w-3.5 h-3.5 text-sky-400" />
              Sync
            </button>
          </div>
        </header>

        {/* Scrollable Content */}
        <main className="flex-1 overflow-y-auto p-6">
          <div className="max-w-6xl mx-auto">
            {tab === "dashboard" && (
              <DashboardView
                metrics={metrics}
                subjects={activeSubjects}
                projects={projects}
                onLogStudy={handleLogStudy}
                onLogProject={handleLogProject}
                onOpenSubject={(sid) => {
                  setFocusedSubjectId(sid);
                  setTab("studies");
                }}
                onLaunchAgy={(prompt) => handleLaunchAgy(prompt)}
              />
            )}

            {tab === "studies" && (
              <StudiesView
                data={data}
                metrics={metrics}
                initialSubjectId={focusedSubjectId}
                onDataChange={setData}
                onRefreshMetrics={refreshMetrics}
                onOpenQuestions={(sid) => {
                  setFocusedSubjectId(sid);
                  setTab("questions");
                }}
                onLaunchAgy={(prompt) => handleLaunchAgy(prompt)}
                onNotify={notify}
              />
            )}

            {tab === "questions" && (
              <QuestionsView
                subjects={activeSubjects}
                initialSubjectId={focusedSubjectId}
                onRefreshMetrics={refreshMetrics}
                onLaunchAgy={(prompt) => handleLaunchAgy(prompt)}
                onNotify={notify}
              />
            )}

            {tab === "projects" && (
              <ProjectsView
                projects={projects}
                onProjectsChange={setProjects}
                onRefreshMetrics={refreshMetrics}
                onLaunchAgy={handleLaunchAgy}
                onNotify={notify}
              />
            )}

            {tab === "settings" && (
              <SettingsView
                data={data}
                agyStatus={agyStatus}
                onDataChange={setData}
                onRefreshMetrics={refreshMetrics}
                onNotify={notify}
              />
            )}
          </div>
        </main>
      </div>

      {/* Toast Notification */}
      {toast && (
        <div className="fixed bottom-5 right-5 z-50 max-w-md rounded-xl border border-sky-500/40 bg-[#11141c]/95 backdrop-blur-md px-4 py-3 text-xs text-slate-100 shadow-2xl">
          {toast}
        </div>
      )}
    </div>
  );
};
