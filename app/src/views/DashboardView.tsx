import React from "react";
import {
  AlertTriangle,
  BookOpen,
  Calculator,
  Flame,
  Sparkles,
  Target,
  Activity,
  ArrowRight,
} from "lucide-react";
import { FocusTimer } from "../components/FocusTimer";
import { Heatmap } from "../components/Heatmap";
import type { MetricsSummary, ProjectItem, Subject } from "../types";

interface DashboardViewProps {
  metrics: MetricsSummary;
  subjects: Subject[];
  projects: ProjectItem[];
  onLogStudy: (payload: {
    subject_id: string;
    questions: number;
    reading_min: number;
    pages: number;
    duration_min: number;
    mode: string;
    topic: string;
  }) => Promise<void>;
  onLogProject: (payload: {
    project_id: string;
    category: string;
    duration_min: number;
    summary: string;
  }) => Promise<void>;
  onOpenSubject: (subjectId: string) => void;
  onLaunchAgy: (prompt: string) => Promise<void>;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  metrics,
  subjects,
  projects,
  onLogStudy,
  onLogProject,
  onOpenSubject,
  onLaunchAgy,
}) => {
  const readingPct = Math.min(
    100,
    Math.round((metrics.today_reading_min / Math.max(1, metrics.daily_goals.leitura_min)) * 100)
  );
  const questionsPct = Math.min(
    100,
    Math.round((metrics.today_questions / Math.max(1, metrics.daily_goals.questoes)) * 100)
  );

  const neglected = metrics.subject_metrics.filter((s) => s.neglected);

  const readingNudge =
    metrics.week_reading_min === 0
      ? "Nenhuma leitura registrada nos últimos 7 dias. Comece com 25 min de teoria hoje!"
      : metrics.reading_ratio_pct < 35
      ? `Leitura representa ${metrics.reading_ratio_pct}% do seu esforço semanal. Equilibre com um bloco de leitura antes da próxima lista.`
      : `Ótimo equilíbrio! Leitura representa ${metrics.reading_ratio_pct}% do seu esforço semanal.`;

  return (
    <div className="space-y-5">
      {/* Top KPI Strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="rounded-xl border border-slate-800/90 bg-[#11141c] p-4">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Sequência (Streak)</span>
            <Flame className="w-4 h-4 text-amber-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-mono font-bold tabular-nums text-slate-100">
              {metrics.current_streak}
            </span>
            <span className="text-xs text-slate-400">dias</span>
          </div>
          <div className="mt-1 text-[11px] text-slate-500">
            Recorde: <span className="font-mono text-slate-300">{metrics.best_streak}d</span> ·{" "}
            {metrics.active_days_30d}/30 dias ativos
          </div>
        </div>

        <div className="rounded-xl border border-slate-800/90 bg-[#11141c] p-4">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Score de Consistência</span>
            <Target className="w-4 h-4 text-sky-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-1.5">
            <span className="text-3xl font-mono font-bold tabular-nums text-sky-300">
              {metrics.consistency_score}
            </span>
            <span className="text-xs text-slate-500">/100</span>
          </div>
          <div className="mt-2 h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-sky-500 to-emerald-400 transition-all"
              style={{ width: `${metrics.consistency_score}%` }}
            />
          </div>
        </div>

        <div className="rounded-xl border border-slate-800/90 bg-[#11141c] p-4">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Leitura Hoje</span>
            <BookOpen className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-1.5">
            <span className="text-3xl font-mono font-bold tabular-nums text-emerald-300">
              {metrics.today_reading_min}
            </span>
            <span className="text-xs text-slate-500">
              / {metrics.daily_goals.leitura_min} min
            </span>
          </div>
          <div className="mt-2 h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
            <div
              className="h-full rounded-full bg-emerald-400 transition-all"
              style={{ width: `${readingPct}%` }}
            />
          </div>
        </div>

        <div className="rounded-xl border border-slate-800/90 bg-[#11141c] p-4">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Exercícios Hoje</span>
            <Calculator className="w-4 h-4 text-violet-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-1.5">
            <span className="text-3xl font-mono font-bold tabular-nums text-violet-300">
              {metrics.today_questions}
            </span>
            <span className="text-xs text-slate-500">
              / {metrics.daily_goals.questoes} questões
            </span>
          </div>
          <div className="mt-2 h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
            <div
              className="h-full rounded-full bg-violet-400 transition-all"
              style={{ width: `${questionsPct}%` }}
            />
          </div>
        </div>
      </div>

      {/* Reading vs Exercises Balance Banner */}
      <div className="rounded-xl border border-emerald-500/20 bg-emerald-950/15 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs font-semibold text-emerald-300">
            <BookOpen className="w-4 h-4" />
            Equilíbrio Semanal: Leitura vs Exercícios
          </div>
          <p className="text-xs text-slate-300">{readingNudge}</p>
          <div className="text-[11px] font-mono text-slate-400">
            Últimos 7 dias: {metrics.week_reading_min} min de leitura · {metrics.week_questions}{" "}
            questões · {metrics.week_project_min} min em projetos/robótica
          </div>
        </div>
        <button
          onClick={() =>
            onLaunchAgy(
              `Analise minhas métricas atuais com 'python3 hud_cli.py stats' e monte um plano de leitura + lista de exercícios para hoje focado nas matérias mais negligenciadas do semestre.`
            )
          }
          className="shrink-0 flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-sky-500/15 border border-sky-500/35 text-sky-300 hover:bg-sky-500/25 text-xs font-semibold transition"
        >
          <Sparkles className="w-3.5 h-3.5" />
          Plano de Hoje no Antigravity
        </button>
      </div>

      {/* Heatmap */}
      <Heatmap days={metrics.heatmap} />

      {/* Main 2-column grid: Neglected/Subjects + Focus Timer & Feed */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4">
        <div className="xl:col-span-7 space-y-4">
          {/* Attention / Neglected Subjects */}
          <div className="rounded-xl border border-slate-800/90 bg-[#11141c] p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                <h3 className="text-sm font-semibold text-slate-100">
                  Radar das Matérias ({metrics.subject_metrics.length})
                </h3>
              </div>
              {neglected.length > 0 && (
                <span className="text-[11px] px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30">
                  {neglected.length} precisando de atenção
                </span>
              )}
            </div>

            <div className="space-y-2.5">
              {metrics.subject_metrics.map((s) => {
                const qPct = Math.min(
                  100,
                  Math.round((s.week_questions / Math.max(1, s.goal_questions)) * 100)
                );
                const rPct = Math.min(
                  100,
                  Math.round((s.week_reading_min / Math.max(1, s.goal_reading_min)) * 100)
                );
                return (
                  <div
                    key={s.subject_id}
                    className="rounded-lg border border-slate-800/80 bg-[#0b0e14] p-3 hover:border-slate-700 transition"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <span
                          className="w-2.5 h-2.5 rounded-full shrink-0"
                          style={{ backgroundColor: s.cor }}
                        />
                        <span className="text-sm font-medium text-slate-100 truncate">
                          {s.nome}
                        </span>
                        {s.neglected && (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-300">
                            {s.days_since_study === null
                              ? "sem início"
                              : `${s.days_since_study}d sem ver`}
                          </span>
                        )}
                      </div>
                      <button
                        onClick={() => onOpenSubject(s.subject_id)}
                        className="flex items-center gap-1 text-xs text-sky-400 hover:text-sky-300 shrink-0"
                      >
                        Abrir <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    <div className="grid grid-cols-2 gap-3 mt-2.5">
                      <div>
                        <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                          <span>Leitura sem.</span>
                          <span className="font-mono text-slate-300">
                            {s.week_reading_min}/{s.goal_reading_min}m
                          </span>
                        </div>
                        <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden">
                          <div
                            className="h-full rounded-full bg-emerald-400"
                            style={{ width: `${rPct}%` }}
                          />
                        </div>
                      </div>

                      <div>
                        <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                          <span>Questões sem.</span>
                          <span className="font-mono text-slate-300">
                            {s.week_questions}/{s.goal_questions}
                          </span>
                        </div>
                        <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden">
                          <div
                            className="h-full rounded-full bg-sky-400"
                            style={{ width: `${qPct}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        <div className="xl:col-span-5 space-y-4">
          <FocusTimer
            subjects={subjects}
            projects={projects}
            onLogStudy={onLogStudy}
            onLogProject={onLogProject}
          />

          {/* Recent Activity Feed */}
          <div className="rounded-xl border border-slate-800/90 bg-[#11141c] p-4">
            <div className="flex items-center gap-2 mb-3">
              <Activity className="w-4 h-4 text-sky-400" />
              <h3 className="text-sm font-semibold text-slate-100">
                Ledger Recente (App & Antigravity)
              </h3>
            </div>
            {metrics.recent_events.length === 0 ? (
              <p className="text-xs text-slate-500">
                Nenhum evento registrado ainda. Use o timer acima ou registre via Antigravity.
              </p>
            ) : (
              <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                {metrics.recent_events.slice(0, 12).map((ev, idx) => {
                  const ts = (ev.ts || ev.timestamp || "").replace("T", " ").slice(0, 16);
                  return (
                    <div
                      key={idx}
                      className="flex items-start justify-between gap-2 text-xs py-1.5 border-b border-slate-800/60 last:border-0"
                    >
                      <div className="min-w-0">
                        <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 mr-1.5">
                          {ev.type}
                        </span>
                        <span className="text-slate-200">
                          {ev.subject || ev.project || "geral"}
                        </span>
                        {ev.topic && (
                          <span className="text-slate-400"> — {ev.topic}</span>
                        )}
                        {ev.summary && (
                          <span className="text-slate-400"> — {ev.summary}</span>
                        )}
                      </div>
                      <span className="font-mono text-[10px] text-slate-500 shrink-0">
                        {ts}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
