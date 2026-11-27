import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DashboardView } from "../views/DashboardView";
import { QuestionsView } from "../views/QuestionsView";
import type { MetricsSummary, ProjectItem, Question, Subject } from "../types";

vi.mock("../api", () => ({
  api: {
    getQuestions: vi.fn().mockResolvedValue([
      {
        id: "f3_q1",
        topico: "Lei de Gauss",
        dificuldade: "media",
        enunciado: "Calcule $E(r)$ para $r < R$.",
        dica: "Use superfície gaussiana esférica.",
        gabarito: "$E(r) = \\frac{\\rho r}{3\\varepsilon_0}$",
        status: "pendente",
        attempts: 0,
      } satisfies Question,
    ]),
    recordQuestionAttempt: vi.fn().mockResolvedValue([
      {
        id: "f3_q1",
        topico: "Lei de Gauss",
        dificuldade: "media",
        enunciado: "Calcule $E(r)$ para $r < R$.",
        dica: "Use superfície gaussiana esférica.",
        gabarito: "$E(r) = \\frac{\\rho r}{3\\varepsilon_0}$",
        status: "acertei",
        attempts: 1,
      } satisfies Question,
    ]),
    importQuestionsJson: vi.fn().mockResolvedValue([]),
  },
  copyToClipboard: vi.fn().mockResolvedValue(undefined),
  isTauri: () => false,
}));

const subject: Subject = {
  id: "fisica3",
  nome: "Física III",
  codigo: "FIS03",
  categoria: "teorica",
  prioridade: "alta",
  cor: "#38bdf8",
  descricao: "Eletrostática",
  materiais_dir: "estudos/fisica3",
  questoes_file: "fisica3.json",
  metas: { questoes_semana: 15, leitura_min_semana: 120, sessoes_semana: 4 },
  avaliacoes: [],
  topicos: [],
  ultimo_estudo: null,
  ultima_leitura: null,
};

const project: ProjectItem = {
  id: "sumo-app",
  nome: "Sumo App",
  categoria: "robotics",
  status: "ativo",
  prioridade: "alta",
  stack: ["ESP32"],
  repo_name: "sumo-app",
  descricao: "Robô sumô",
  next_action: "Calibrar sensores",
  pinned: true,
};

const metrics: MetricsSummary = {
  today_date: "2026-11-26",
  today_questions: 3,
  today_reading_min: 30,
  today_focus_min: 60,
  today_project_min: 45,
  daily_goals: { questoes: 5, leitura_min: 45, foco_min: 90 },
  current_streak: 4,
  best_streak: 7,
  active_days_30d: 14,
  consistency_score: 78,
  week_questions: 12,
  week_reading_min: 90,
  week_project_min: 180,
  reading_ratio_pct: 43,
  heatmap: [
    {
      date: "2026-11-26",
      questions: 3,
      reading_min: 30,
      focus_min: 60,
      project_min: 45,
      score: 99,
      level: 3,
    },
  ],
  subject_metrics: [
    {
      subject_id: "fisica3",
      nome: "Física III",
      cor: "#38bdf8",
      prioridade: "alta",
      week_questions: 4,
      week_reading_min: 30,
      week_sessions: 2,
      goal_questions: 15,
      goal_reading_min: 120,
      days_since_study: 5,
      days_since_reading: 5,
      syllabus_progress_pct: 25,
      reading_topics_done: 1,
      total_topics: 4,
      neglected: true,
    },
  ],
  recent_events: [
    {
      ts: "2026-11-26T14:00:00",
      type: "study_session",
      subject: "fisica3",
      topic: "Lei de Gauss",
    },
  ],
};

describe("DashboardView", () => {
  it("renders KPIs, neglected radar, and triggers Antigravity prompt", async () => {
    const onOpenSubject = vi.fn();
    const onLaunchAgy = vi.fn().mockResolvedValue(undefined);

    render(
      <DashboardView
        metrics={metrics}
        subjects={[subject]}
        projects={[project]}
        onLogStudy={vi.fn().mockResolvedValue(undefined)}
        onLogProject={vi.fn().mockResolvedValue(undefined)}
        onOpenSubject={onOpenSubject}
        onLaunchAgy={onLaunchAgy}
      />
    );

    expect(screen.getByText("78")).toBeInTheDocument();
    expect(screen.getByText(/1 precisando de atenção/i)).toBeInTheDocument();
    expect(screen.getByText(/5d sem ver/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Abrir/i }));
    expect(onOpenSubject).toHaveBeenCalledWith("fisica3");

    fireEvent.click(screen.getByRole("button", { name: /Plano de Hoje no Antigravity/i }));
    expect(onLaunchAgy).toHaveBeenCalled();
  });
});

describe("QuestionsView", () => {
  it("loads AI questions, reveals hint & solution, and marks Acertei", async () => {
    const onRefreshMetrics = vi.fn().mockResolvedValue(undefined);
    const onLaunchAgy = vi.fn().mockResolvedValue(undefined);
    const onNotify = vi.fn();

    render(
      <QuestionsView
        subjects={[subject]}
        initialSubjectId="fisica3"
        onRefreshMetrics={onRefreshMetrics}
        onLaunchAgy={onLaunchAgy}
        onNotify={onNotify}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Lei de Gauss")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Ver Dica/i }));
    expect(screen.getByText(/superfície gaussiana esférica/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Ver Gabarito/i }));
    expect(screen.getByText(/Resolução \/ Gabarito/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /^Acertei$/i }));
    await waitFor(() => {
      expect(onRefreshMetrics).toHaveBeenCalled();
      expect(onNotify).toHaveBeenCalled();
    });
  });
});
