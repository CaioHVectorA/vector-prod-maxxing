import React, { useMemo, useState } from "react";
import type { HeatmapDay } from "../types";

type Mode = "all" | "reading" | "questions" | "projects";

interface HeatmapProps {
  days: HeatmapDay[];
}

export const Heatmap: React.FC<HeatmapProps> = ({ days }) => {
  const [mode, setMode] = useState<Mode>("all");
  const [hovered, setHovered] = useState<HeatmapDay | null>(null);

  const weeks = useMemo(() => {
    const cols: HeatmapDay[][] = [];
    for (let i = 0; i < days.length; i += 7) {
      cols.push(days.slice(i, i + 7));
    }
    return cols;
  }, [days]);

  const getLevel = (d: HeatmapDay): number => {
    if (mode === "all") return d.level;
    if (mode === "reading") {
      if (d.reading_min === 0) return 0;
      if (d.reading_min < 20) return 1;
      if (d.reading_min < 45) return 2;
      if (d.reading_min < 90) return 3;
      return 4;
    }
    if (mode === "questions") {
      if (d.questions === 0) return 0;
      if (d.questions <= 2) return 1;
      if (d.questions <= 5) return 2;
      if (d.questions <= 10) return 3;
      return 4;
    }
    if (d.project_min === 0) return 0;
    if (d.project_min < 30) return 1;
    if (d.project_min < 60) return 2;
    if (d.project_min < 120) return 3;
    return 4;
  };

  const colorFor = (lvl: number) => {
    if (mode === "reading") {
      return [
        "bg-[#161b26]",
        "bg-emerald-950/90 border-emerald-800/40",
        "bg-emerald-700/75 border-emerald-500/40",
        "bg-emerald-500/85 border-emerald-400/50",
        "bg-emerald-400 border-emerald-300",
      ][lvl];
    }
    if (mode === "questions") {
      return [
        "bg-[#161b26]",
        "bg-sky-950/90 border-sky-800/40",
        "bg-sky-700/75 border-sky-500/40",
        "bg-sky-500/85 border-sky-400/50",
        "bg-sky-400 border-sky-300",
      ][lvl];
    }
    if (mode === "projects") {
      return [
        "bg-[#161b26]",
        "bg-violet-950/90 border-violet-800/40",
        "bg-violet-700/75 border-violet-500/40",
        "bg-violet-500/85 border-violet-400/50",
        "bg-violet-400 border-violet-300",
      ][lvl];
    }
    return [
      "bg-[#161b26]",
      "bg-cyan-950/90 border-cyan-800/40",
      "bg-cyan-700/75 border-cyan-500/40",
      "bg-cyan-500/85 border-cyan-400/50",
      "bg-cyan-300 border-cyan-200",
    ][lvl];
  };

  return (
    <div className="rounded-xl border border-slate-800/90 bg-[#11141c] p-4">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-100">
            Mapa de Consistência (16 semanas)
          </h3>
          <p className="text-xs text-slate-400">
            {hovered ? (
              <span className="font-mono text-slate-300">
                {hovered.date} — {hovered.reading_min}m leitura · {hovered.questions} questões ·{" "}
                {hovered.project_min}m projetos
              </span>
            ) : (
              "Passe o mouse em um dia para inspecionar leitura, questões e projetos"
            )}
          </p>
        </div>

        <div className="flex items-center gap-1 bg-[#0b0e14] p-1 rounded-lg border border-slate-800">
          {(
            [
              ["all", "Tudo"],
              ["reading", "Leitura"],
              ["questions", "Exercícios"],
              ["projects", "Projetos"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              onClick={() => setMode(id)}
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition ${
                mode === id
                  ? "bg-slate-800 text-sky-300"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-x-auto pb-1">
        <div className="inline-flex gap-1.5">
          {weeks.map((week, wi) => (
            <div key={wi} className="flex flex-col gap-1.5">
              {week.map((day) => {
                const lvl = getLevel(day);
                return (
                  <div
                    key={day.date}
                    onMouseEnter={() => setHovered(day)}
                    onMouseLeave={() => setHovered(null)}
                    className={`w-3.5 h-3.5 rounded-[3px] border border-transparent transition-transform hover:scale-125 cursor-pointer ${colorFor(
                      lvl
                    )}`}
                    title={`${day.date}: ${day.reading_min}m leitura, ${day.questions} questões, ${day.project_min}m projetos`}
                  />
                );
              })}
            </div>
          ))}
        </div>
      </div>

      <div className="flex items-center justify-end gap-1.5 mt-2 text-[11px] text-slate-500">
        <span>Menos</span>
        {[0, 1, 2, 3, 4].map((lvl) => (
          <span
            key={lvl}
            className={`w-3 h-3 rounded-[2px] border border-transparent ${colorFor(lvl)}`}
          />
        ))}
        <span>Mais</span>
      </div>
    </div>
  );
};
