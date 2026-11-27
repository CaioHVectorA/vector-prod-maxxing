import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { ProjectsView } from "../views/ProjectsView";
import { SettingsView } from "../views/SettingsView";
import { StudiesView } from "../views/StudiesView";
import type { AgyStatus, AppData, MetricsSummary, ProjectItem } from "../types";

const mockData: AppData = {
  schema_version: 2,
  active_semester: "2027.1",
  daily_goals: { questoes: 5, leitura_min: 45, foco_min: 90 },
  agy_config: {
    cli_command: "antigravity",
    terminal_command: "x-terminal-emulator",
    develop_dirs: ["~/develop"],
    auto_git_sync: true,
  },
  semesters: {
    "2027.1": {
      id: "2027.1",
      nome: "2027.1 — Preparação",
      status: "ativo",
      disciplinas: [
        {
          id: "fisica3",
          nome: "Física III",
          codigo: "FIS03",
          categoria: "teorica",
          prioridade: "alta",
          cor: "#38bdf8",
          descricao: "Eletrostática e Magnetismo",
          materiais_dir: "estudos/fisica3",
          questoes_file: "fisica3.json",
          metas: { questoes_semana: 15, leitura_min_semana: 120, sessoes_semana: 4 },
          avaliacoes: [
            { id: "p1", nome: "P1", peso: 1, nota: 8.0, data: "2027-04-15" },
            { id: "p2", nome: "P2", peso: 1, nota: null, data: null },
          ],
          topicos: [
            {
              id: "t1",
              titulo: "Lei de Gauss",
              status: "lendo",
              leitura_concluida: false,
              questoes_resolvidas: 2,
            },
          ],
          ultimo_estudo: null,
          ultima_leitura: null,
        },
      ],
    },
  },
};

const mockMetrics: MetricsSummary = {
  today_date: "2026-11-26",
  today_questions: 2,
  today_reading_min: 30,
  today_focus_min: 45,
  today_project_min: 30,
  daily_goals: { questoes: 5, leitura_min: 45, foco_min: 90 },
  current_streak: 3,
  best_streak: 5,
  active_days_30d: 10,
  consistency_score: 72,
  week_questions: 10,
  week_reading_min: 90,
  week_project_min: 120,
  reading_ratio_pct: 47,
  heatmap: [
    {
      date: "2026-11-26",
      questions: 2,
      reading_min: 30,
      focus_min: 45,
      project_min: 30,
      score: 70,
      level: 3,
    },
  ],
  subject_metrics: [
    {
      subject_id: "fisica3",
      nome: "Física III",
      cor: "#38bdf8",
      prioridade: "alta",
      week_questions: 5,
      week_reading_min: 60,
      week_sessions: 2,
      goal_questions: 15,
      goal_reading_min: 120,
      days_since_study: 1,
      days_since_reading: 1,
      syllabus_progress_pct: 35,
      reading_topics_done: 0,
      total_topics: 1,
      neglected: false,
    },
  ],
  recent_events: [],
};

const mockProjects: ProjectItem[] = [
  {
    id: "rl-robot",
    nome: "RL Robot",
    categoria: "robotics",
    status: "ativo",
    prioridade: "alta",
    stack: ["Python", "RL"],
    repo_name: "rl-robot",
    descricao: "Robô RL",
    next_action: "Ajustar recompensa",
    pinned: true,
  },
];

const mockAgyStatus: AgyStatus = {
  cli_command: "antigravity",
  cli_available: true,
  resolved_path: "/usr/local/bin/antigravity",
  repo_dir: "/home/user/vector-prod-maxxing",
  hud_cli_path: "/home/user/vector-prod-maxxing/hud_cli.py",
};

vi.mock("../api", () => ({
  api: {
    getAppData: vi.fn(async () => mockData),
    saveAppData: vi.fn(async (d: AppData) => d),
    setActiveSemester: vi.fn(async () => mockData),
    createSemester: vi.fn(async () => mockData),
    upsertSubject: vi.fn(async () => mockData),
    deleteSubject: vi.fn(async () => mockData),
    updateTopicState: vi.fn(async () => mockData),
    addTopic: vi.fn(async () => mockData),
    updateEvaluations: vi.fn(async () => mockData),
    logStudySession: vi.fn(async () => mockMetrics),
    getMetrics: vi.fn(async () => mockMetrics),
    getQuestions: vi.fn(async () => []),
    recordQuestionAttempt: vi.fn(async () => []),
    importQuestionsJson: vi.fn(async () => []),
    listMaterials: vi.fn(async () => [
      {
        name: "Apostila_Gauss.pdf",
        rel_path: "estudos/fisica3/Apostila_Gauss.pdf",
        abs_path: "/tmp/Apostila_Gauss.pdf",
        ext: "pdf",
        size_bytes: 2048,
        modified_at: "2026-11-26 10:00",
      },
    ]),
    getProjects: vi.fn(async () => mockProjects),
    saveProjects: vi.fn(async (p: ProjectItem[]) => p),
    logProjectSession: vi.fn(async () => mockMetrics),
    scanRepos: vi.fn(async () => [
      {
        name: "rl-robot",
        path: "/home/user/develop/rl-robot",
        branch: "main",
        dirty_files: 2,
        last_commit_msg: "feat: reward shaping",
        last_commit_rel: "2 hours ago",
      },
    ]),
    scanHardware: vi.fn(async () => ({
      serial_devices: [
        {
          port: "/dev/ttyUSB0",
          label: "ttyUSB0",
          board_hint: "ESP32 / CP210x",
        },
      ],
      firmwares: [
        {
          board: "esp32",
          name: "blink",
          path: "/tmp/firmwares/esp32/blink",
          files: ["blink.ino"],
        },
      ],
    })),
    getAgyStatus: vi.fn(async () => mockAgyStatus),
    launchAgy: vi.fn(async () => "Antigravity iniciado"),
    openPath: vi.fn(async () => undefined),
    gitSyncNow: vi.fn(async () => "Sincronizado"),
    onWorkspaceChanged: vi.fn(async () => () => {}),
  },
  copyToClipboard: vi.fn(async () => undefined),
  isTauri: () => false,
}));

describe("StudiesView", () => {
  it("renders subject details, auto-scanned materials, syllabus, and adds topic", async () => {
    const onDataChange = vi.fn();
    const onRefreshMetrics = vi.fn().mockResolvedValue(undefined);
    const onOpenQuestions = vi.fn();
    const onLaunchAgy = vi.fn().mockResolvedValue(undefined);
    const onNotify = vi.fn();

    render(
      <StudiesView
        data={mockData}
        metrics={mockMetrics}
        onDataChange={onDataChange}
        onRefreshMetrics={onRefreshMetrics}
        onOpenQuestions={onOpenQuestions}
        onLaunchAgy={onLaunchAgy}
        onNotify={onNotify}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Apostila_Gauss.pdf")).toBeInTheDocument();
    });

    expect(screen.getByText(/Média: 8\.00/)).toBeInTheDocument();

    fireEvent.click(screen.getByText("Lendo"));
    await waitFor(() => expect(onDataChange).toHaveBeenCalled());

    fireEvent.change(screen.getByPlaceholderText(/Adicionar tópico/i), {
      target: { value: "Lei de Ampère" },
    });
    fireEvent.click(screen.getByRole("button", { name: /\+ Tópico/i }));
    await waitFor(() => expect(onRefreshMetrics).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: /Praticar Banco de Questões/i }));
    expect(onOpenQuestions).toHaveBeenCalledWith("fisica3");
  });
});

describe("ProjectsView", () => {
  it("displays robotics projects, local git repos, and Linux serial/firmwares", async () => {
    const onProjectsChange = vi.fn();
    const onRefreshMetrics = vi.fn().mockResolvedValue(undefined);
    const onLaunchAgy = vi.fn().mockResolvedValue(undefined);
    const onNotify = vi.fn();

    render(
      <ProjectsView
        projects={mockProjects}
        onProjectsChange={onProjectsChange}
        onRefreshMetrics={onRefreshMetrics}
        onLaunchAgy={onLaunchAgy}
        onNotify={onNotify}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("RL Robot")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /\+30m log/i }));
    await waitFor(() => expect(onRefreshMetrics).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: /Repositórios Locais/i }));
    expect(screen.getByText(/feat: reward shaping/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Serial & Firmwares/i }));
    expect(screen.getByText("/dev/ttyUSB0")).toBeInTheDocument();
    expect(screen.getByText("blink")).toBeInTheDocument();
  });
});

describe("SettingsView", () => {
  it("saves updated daily goals and runs Git Sync", async () => {
    const onDataChange = vi.fn();
    const onRefreshMetrics = vi.fn().mockResolvedValue(undefined);
    const onNotify = vi.fn();

    render(
      <SettingsView
        data={mockData}
        agyStatus={mockAgyStatus}
        onDataChange={onDataChange}
        onRefreshMetrics={onRefreshMetrics}
        onNotify={onNotify}
      />
    );

    expect(screen.getByText(/\/usr\/local\/bin\/antigravity/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Salvar Alterações/i }));
    await waitFor(() => expect(onDataChange).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: /Git Sync Agora/i }));
    await waitFor(() => expect(onNotify).toHaveBeenCalledWith("Sincronizado"));
  });
});

describe("App Shell Navigation", () => {
  it("loads data and navigates across all 5 tabs cleanly", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText("Vector Maxxing")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /^Estudos$/i }));
    await waitFor(() => expect(screen.getByText(/Ementa & Progresso de Leitura/i)).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /Questões IA/i }));
    await waitFor(() => expect(screen.getByRole("button", { name: /Gerar Nova Lista no Antigravity/i })).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /Código & Robótica/i }));
    await waitFor(() => expect(screen.getByText("RL Robot")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /Config & Agy/i }));
    await waitFor(() => expect(screen.getByText(/Metas Diárias de Consistência/i)).toBeInTheDocument());
  });
});
