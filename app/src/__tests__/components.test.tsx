import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { FocusTimer } from "../components/FocusTimer";
import { Heatmap } from "../components/Heatmap";
import { MathText } from "../components/MathText";
import { SubjectModal } from "../components/SubjectModal";
import type { HeatmapDay, ProjectItem, Subject } from "../types";

const sampleSubject: Subject = {
  id: "fisica3",
  nome: "Física III",
  codigo: "FIS03",
  categoria: "teorica",
  prioridade: "alta",
  cor: "#38bdf8",
  descricao: "Eletrostática e Magnetostática",
  materiais_dir: "estudos/fisica3",
  questoes_file: "fisica3.json",
  metas: { questoes_semana: 15, leitura_min_semana: 120, sessoes_semana: 4 },
  avaliacoes: [],
  topicos: [],
  ultimo_estudo: null,
  ultima_leitura: null,
};

const sampleProject: ProjectItem = {
  id: "rl-robot",
  nome: "RL Robot",
  categoria: "robotics",
  status: "ativo",
  prioridade: "alta",
  stack: ["Python", "RL"],
  repo_name: "rl-robot",
  descricao: "Robô RL",
  next_action: "Treinar política",
  pinned: true,
};

describe("MathText", () => {
  it("renders plain prose and inline/display KaTeX math", () => {
    const { container } = render(
      <MathText text={"Lei de Gauss: $E = \\frac{\\rho r}{3\\varepsilon_0}$\n$$\\nabla \\cdot \\vec{E} = \\frac{\\rho}{\\varepsilon_0}$$"} />
    );
    expect(container.textContent).toContain("Lei de Gauss");
    expect(container.querySelectorAll(".katex").length).toBeGreaterThanOrEqual(2);
    expect(container.querySelector(".katex-display")).toBeTruthy();
  });
});

describe("Heatmap", () => {
  it("renders 112 days and switches filter modes", () => {
    const days: HeatmapDay[] = Array.from({ length: 112 }, (_, i) => ({
      date: `2026-10-${String((i % 28) + 1).padStart(2, "0")}`,
      questions: i % 3 === 0 ? 4 : 0,
      reading_min: i % 2 === 0 ? 45 : 0,
      focus_min: 30,
      project_min: i % 5 === 0 ? 60 : 0,
      score: i % 2 === 0 ? 50 : 0,
      level: i % 2 === 0 ? 2 : 0,
    }));

    render(<Heatmap days={days} />);
    expect(screen.getByText(/Mapa de Consistência/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Leitura" }));
    fireEvent.click(screen.getByRole("button", { name: "Exercícios" }));
    fireEvent.click(screen.getByRole("button", { name: "Projetos" }));
    fireEvent.click(screen.getByRole("button", { name: "Tudo" }));
  });
});

describe("FocusTimer", () => {
  it("logs a quick reading session and switches to project mode", async () => {
    const onLogStudy = vi.fn().mockResolvedValue(undefined);
    const onLogProject = vi.fn().mockResolvedValue(undefined);

    render(
      <FocusTimer
        subjects={[sampleSubject]}
        projects={[sampleProject]}
        onLogStudy={onLogStudy}
        onLogProject={onLogProject}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "45m" }));
    expect(screen.getByText("45:00")).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText(/Páginas lidas/i), {
      target: { value: "10" },
    });
    fireEvent.change(screen.getByPlaceholderText(/Tópico/i), {
      target: { value: "Lei de Gauss" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Registrar Sessão Rápida/i }));

    await waitFor(() => {
      expect(onLogStudy).toHaveBeenCalledWith(
        expect.objectContaining({
          subject_id: "fisica3",
          reading_min: 45,
          pages: 10,
          mode: "leitura",
          topic: "Lei de Gauss",
        })
      );
    });

    fireEvent.click(screen.getByRole("button", { name: /Projeto/i }));
    fireEvent.click(screen.getByRole("button", { name: /Registrar Sessão Rápida/i }));
    await waitFor(() => {
      expect(onLogProject).toHaveBeenCalledWith(
        expect.objectContaining({
          project_id: "rl-robot",
          category: "robotics",
        })
      );
    });
  });
});

describe("SubjectModal", () => {
  it("auto-slugifies subject ID and submits new subject", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const onClose = vi.fn();

    render(<SubjectModal onClose={onClose} onSave={onSave} />);

    fireEvent.change(screen.getByPlaceholderText(/Ex: Eletromagnetismo/i), {
      target: { value: "Controle Clássico" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Salvar Disciplina/i }));

    await waitFor(() => {
      expect(onSave).toHaveBeenCalledWith(
        expect.objectContaining({
          id: "controle_classico",
          nome: "Controle Clássico",
          materiais_dir: "estudos/controle_classico",
        })
      );
      expect(onClose).toHaveBeenCalled();
    });
  });
});
