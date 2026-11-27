import React, { useEffect, useState } from "react";
import { BookOpen, Code2, Pause, Play, RotateCcw, Save, Calculator } from "lucide-react";
import type { ProjectItem, Subject } from "../types";

interface FocusTimerProps {
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
}

export const FocusTimer: React.FC<FocusTimerProps> = ({
  subjects,
  projects,
  onLogStudy,
  onLogProject,
}) => {
  const [mode, setMode] = useState<"leitura" | "exercicios" | "projeto">("leitura");
  const [targetId, setTargetId] = useState<string>(subjects[0]?.id ?? "");
  const [presetMin, setPresetMin] = useState<number>(25);
  const [secondsLeft, setSecondsLeft] = useState<number>(25 * 60);
  const [elapsedSec, setElapsedSec] = useState<number>(0);
  const [running, setRunning] = useState<boolean>(false);
  const [notes, setNotes] = useState<string>("");
  const [extraCount, setExtraCount] = useState<number>(0); // pages or questions
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (mode === "projeto") {
      if (!projects.some((p) => p.id === targetId)) {
        setTargetId(projects[0]?.id ?? "");
      }
    } else {
      if (!subjects.some((s) => s.id === targetId)) {
        setTargetId(subjects[0]?.id ?? "");
      }
    }
  }, [mode, subjects, projects, targetId]);

  useEffect(() => {
    if (!running) return;
    const id = window.setInterval(() => {
      setSecondsLeft((prev) => {
        if (prev <= 1) {
          setRunning(false);
          return 0;
        }
        return prev - 1;
      });
      setElapsedSec((prev) => prev + 1);
    }, 1000);
    return () => window.clearInterval(id);
  }, [running]);

  const selectPreset = (m: number) => {
    setRunning(false);
    setPresetMin(m);
    setSecondsLeft(m * 60);
    setElapsedSec(0);
  };

  const mins = Math.floor(secondsLeft / 60);
  const secs = secondsLeft % 60;
  const elapsedMin = Math.max(1, Math.round(elapsedSec / 60));

  const handleSave = async () => {
    if (!targetId) return;
    setSaving(true);
    try {
      const duration = elapsedSec >= 30 ? elapsedMin : presetMin;
      if (mode === "projeto") {
        const proj = projects.find((p) => p.id === targetId);
        await onLogProject({
          project_id: targetId,
          category: proj?.categoria ?? "code",
          duration_min: duration,
          summary: notes.trim() || "Sessão de foco",
        });
      } else {
        await onLogStudy({
          subject_id: targetId,
          questions: mode === "exercicios" ? Math.max(extraCount, 1) : 0,
          reading_min: mode === "leitura" ? duration : 0,
          pages: mode === "leitura" ? extraCount : 0,
          duration_min: duration,
          mode,
          topic: notes.trim() || (mode === "leitura" ? "Leitura teórica" : "Prática de exercícios"),
        });
      }
      setRunning(false);
      setElapsedSec(0);
      setSecondsLeft(presetMin * 60);
      setNotes("");
      setExtraCount(0);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="rounded-xl border border-slate-800/90 bg-[#11141c] p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-100">Sessão de Foco & Leitura</h3>
        <div className="flex gap-1 bg-[#0b0e14] p-0.5 rounded-lg border border-slate-800">
          <button
            onClick={() => setMode("leitura")}
            className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-medium ${
              mode === "leitura" ? "bg-emerald-500/20 text-emerald-300" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" /> Leitura
          </button>
          <button
            onClick={() => setMode("exercicios")}
            className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-medium ${
              mode === "exercicios" ? "bg-sky-500/20 text-sky-300" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Calculator className="w-3.5 h-3.5" /> Exercícios
          </button>
          <button
            onClick={() => setMode("projeto")}
            className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-medium ${
              mode === "projeto" ? "bg-violet-500/20 text-violet-300" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Code2 className="w-3.5 h-3.5" /> Projeto
          </button>
        </div>
      </div>

      <div className="flex items-center justify-between gap-4 bg-[#0b0e14] rounded-lg px-4 py-3 border border-slate-800/80">
        <div>
          <div className="text-3xl font-mono font-bold tabular-nums tracking-tight text-slate-100">
            {String(mins).padStart(2, "0")}:{String(secs).padStart(2, "0")}
          </div>
          <div className="flex gap-1.5 mt-1.5">
            {[15, 25, 45, 60].map((m) => (
              <button
                key={m}
                onClick={() => selectPreset(m)}
                className={`px-2 py-0.5 rounded text-[11px] font-mono ${
                  presetMin === m
                    ? "bg-slate-700 text-slate-100"
                    : "bg-slate-900 text-slate-400 hover:text-slate-200"
                }`}
              >
                {m}m
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setRunning((r) => !r)}
            className={`flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold transition ${
              running
                ? "bg-amber-500/20 text-amber-300 border border-amber-500/40 hover:bg-amber-500/30"
                : "bg-sky-500 text-slate-950 hover:bg-sky-400"
            }`}
          >
            {running ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            {running ? "Pausar" : "Iniciar"}
          </button>
          <button
            onClick={() => selectPreset(presetMin)}
            className="p-2 rounded-lg bg-slate-800/80 text-slate-300 hover:bg-slate-700"
            title="Resetar timer"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <select
          value={targetId}
          onChange={(e) => setTargetId(e.target.value)}
          className="bg-[#0b0e14] border border-slate-800 rounded-lg px-2.5 py-2 text-xs text-slate-200 focus:outline-none focus:border-sky-500"
        >
          {mode === "projeto"
            ? projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.nome}
                </option>
              ))
            : subjects.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.nome}
                </option>
              ))}
        </select>

        {mode !== "projeto" ? (
          <input
            type="number"
            min={0}
            value={extraCount || ""}
            onChange={(e) => setExtraCount(parseInt(e.target.value || "0", 10))}
            placeholder={mode === "leitura" ? "Páginas lidas (opcional)" : "Questões resolvidas"}
            className="bg-[#0b0e14] border border-slate-800 rounded-lg px-2.5 py-2 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-sky-500"
          />
        ) : (
          <input
            type="text"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="O que avançou no projeto?"
            className="bg-[#0b0e14] border border-slate-800 rounded-lg px-2.5 py-2 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-sky-500"
          />
        )}
      </div>

      {mode !== "projeto" && (
        <input
          type="text"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Tópico / capítulo estudado..."
          className="bg-[#0b0e14] border border-slate-800 rounded-lg px-2.5 py-2 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-sky-500"
        />
      )}

      <button
        onClick={handleSave}
        disabled={saving || !targetId}
        className="w-full flex items-center justify-center gap-1.5 py-2 rounded-lg bg-emerald-500/15 border border-emerald-500/35 text-emerald-300 hover:bg-emerald-500/25 text-xs font-semibold transition disabled:opacity-50"
      >
        <Save className="w-3.5 h-3.5" />
        {saving
          ? "Registrando..."
          : elapsedSec >= 30
          ? `Registrar Sessão (${elapsedMin} min)`
          : `Registrar Sessão Rápida (${presetMin} min)`}
      </button>
    </div>
  );
};
