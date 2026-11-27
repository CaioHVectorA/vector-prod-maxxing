import React, { useEffect, useState } from "react";
import {
  BookOpen,
  CheckCircle2,
  Circle,
  ExternalLink,
  FileText,
  FolderOpen,
  Pencil,
  Plus,
  Sparkles,
  Trash2,
} from "lucide-react";
import { api } from "../api";
import { SubjectModal } from "../components/SubjectModal";
import type {
  AppData,
  Evaluation,
  MetricsSummary,
  StudyMaterial,
  Subject,
  TopicStatus,
} from "../types";

interface StudiesViewProps {
  data: AppData;
  metrics: MetricsSummary;
  initialSubjectId?: string | null;
  onDataChange: (next: AppData) => void;
  onRefreshMetrics: () => Promise<void>;
  onOpenQuestions: (subjectId: string) => void;
  onLaunchAgy: (prompt: string) => Promise<void>;
  onNotify: (msg: string) => void;
}

const STATUS_CYCLE: TopicStatus[] = ["nao_iniciado", "lendo", "praticando", "dominado"];
const STATUS_STYLE: Record<string, string> = {
  nao_iniciado: "bg-slate-800 text-slate-400",
  lendo: "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30",
  praticando: "bg-sky-500/20 text-sky-300 border border-sky-500/30",
  dominado: "bg-violet-500/20 text-violet-300 border border-violet-500/30",
};
const STATUS_LABEL: Record<string, string> = {
  nao_iniciado: "Não iniciado",
  lendo: "Lendo",
  praticando: "Praticando",
  dominado: "Dominado",
};

export const StudiesView: React.FC<StudiesViewProps> = ({
  data,
  metrics,
  initialSubjectId,
  onDataChange,
  onRefreshMetrics,
  onOpenQuestions,
  onLaunchAgy,
  onNotify,
}) => {
  const sem = data.semesters[data.active_semester];
  const subjects = sem?.disciplinas ?? [];
  const [selectedId, setSelectedId] = useState<string>(
    initialSubjectId || subjects[0]?.id || ""
  );
  const [materials, setMaterials] = useState<StudyMaterial[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingSubject, setEditingSubject] = useState<Subject | null>(null);
  const [newTopicTitle, setNewTopicTitle] = useState("");
  const [newSemOpen, setNewSemOpen] = useState(false);
  const [newSemId, setNewSemId] = useState("");
  const [newSemName, setNewSemName] = useState("");

  useEffect(() => {
    if (initialSubjectId && subjects.some((s) => s.id === initialSubjectId)) {
      setSelectedId(initialSubjectId);
    } else if (!subjects.some((s) => s.id === selectedId)) {
      setSelectedId(subjects[0]?.id ?? "");
    }
  }, [initialSubjectId, data.active_semester, subjects, selectedId]);

  const selected = subjects.find((s) => s.id === selectedId) ?? null;

  useEffect(() => {
    if (!selected) {
      setMaterials([]);
      return;
    }
    api
      .listMaterials(selected.materiais_dir || `estudos/${selected.id}`)
      .then(setMaterials)
      .catch(() => setMaterials([]));
  }, [selected?.id, selected?.materiais_dir, data]);

  const handleSemesterSwitch = async (semId: string) => {
    const next = await api.setActiveSemester(semId);
    onDataChange(next);
    await onRefreshMetrics();
  };

  const handleCreateSemester = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSemId.trim() || !newSemName.trim()) return;
    const next = await api.createSemester(newSemId.trim(), newSemName.trim());
    onDataChange(next);
    setNewSemId("");
    setNewSemName("");
    setNewSemOpen(false);
    await onRefreshMetrics();
    onNotify(`Semestre ${newSemId} criado!`);
  };

  const handleSaveSubject = async (subj: Subject) => {
    const next = await api.upsertSubject(data.active_semester, subj);
    onDataChange(next);
    setSelectedId(subj.id);
    await onRefreshMetrics();
    onNotify(`Disciplina "${subj.nome}" salva.`);
  };

  const handleDeleteSubject = async (subj: Subject) => {
    if (!window.confirm(`Remover "${subj.nome}" deste semestre?`)) return;
    const next = await api.deleteSubject(data.active_semester, subj.id);
    onDataChange(next);
    await onRefreshMetrics();
    onNotify(`Disciplina "${subj.nome}" removida.`);
  };

  const handleCycleTopic = async (topicId: string, current: TopicStatus, readDone: boolean) => {
    if (!selected) return;
    const idx = STATUS_CYCLE.indexOf(current);
    const nextStatus = STATUS_CYCLE[(idx + 1) % STATUS_CYCLE.length];
    const nextRead = nextStatus === "dominado" ? true : readDone;
    const next = await api.updateTopicState(
      data.active_semester,
      selected.id,
      topicId,
      nextStatus,
      nextRead
    );
    onDataChange(next);
    await onRefreshMetrics();
  };

  const handleToggleReading = async (topicId: string, status: TopicStatus, currentRead: boolean) => {
    if (!selected) return;
    const nextRead = !currentRead;
    const nextStatus = nextRead && status === "nao_iniciado" ? "lendo" : status;
    const next = await api.updateTopicState(
      data.active_semester,
      selected.id,
      topicId,
      nextStatus,
      nextRead
    );
    onDataChange(next);
    await onRefreshMetrics();
  };

  const handleAddTopic = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selected || !newTopicTitle.trim()) return;
    const next = await api.addTopic(data.active_semester, selected.id, newTopicTitle.trim());
    onDataChange(next);
    setNewTopicTitle("");
    await onRefreshMetrics();
  };

  const handleUpdateEval = async (idx: number, patch: Partial<Evaluation>) => {
    if (!selected) return;
    const updated = selected.avaliacoes.map((av, i) => (i === idx ? { ...av, ...patch } : av));
    const next = await api.updateEvaluations(data.active_semester, selected.id, updated);
    onDataChange(next);
  };

  const handleAddEval = async () => {
    if (!selected) return;
    const num = selected.avaliacoes.length + 1;
    const updated: Evaluation[] = [
      ...selected.avaliacoes,
      { id: `av_${num}`, nome: `Av ${num}`, peso: 1, nota: null, data: null },
    ];
    const next = await api.updateEvaluations(data.active_semester, selected.id, updated);
    onDataChange(next);
  };

  const weightedAvg = (evals: Evaluation[]) => {
    const graded = evals.filter((e) => e.nota !== null && !Number.isNaN(e.nota));
    if (graded.length === 0) return null;
    const sumW = graded.reduce((acc, e) => acc + (e.peso || 1), 0);
    const sumV = graded.reduce((acc, e) => acc + (e.nota ?? 0) * (e.peso || 1), 0);
    return sumW > 0 ? sumV / sumW : null;
  };

  return (
    <div className="space-y-4">
      {/* Semester Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          {Object.values(data.semesters).map((s) => (
            <button
              key={s.id}
              onClick={() => handleSemesterSwitch(s.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition ${
                s.id === data.active_semester
                  ? "bg-sky-500/15 border-sky-500/40 text-sky-300"
                  : "bg-[#11141c] border-slate-800 text-slate-400 hover:text-slate-200"
              }`}
            >
              {s.id}
              <span className="ml-1.5 text-[10px] opacity-70">({s.disciplinas.length})</span>
            </button>
          ))}
          <button
            onClick={() => setNewSemOpen((v) => !v)}
            className="px-2.5 py-1.5 rounded-lg text-xs border border-dashed border-slate-700 text-slate-400 hover:text-slate-200 hover:border-slate-500"
          >
            + Semestre
          </button>
        </div>

        <button
          onClick={() => {
            setEditingSubject(null);
            setModalOpen(true);
          }}
          className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-sky-500 text-slate-950 text-xs font-semibold hover:bg-sky-400 transition"
        >
          <Plus className="w-3.5 h-3.5" />
          Nova Matéria
        </button>
      </div>

      {newSemOpen && (
        <form
          onSubmit={handleCreateSemester}
          className="flex flex-wrap items-center gap-2 p-3 rounded-xl border border-slate-800 bg-[#11141c]"
        >
          <input
            value={newSemId}
            onChange={(e) => setNewSemId(e.target.value)}
            placeholder="ID (ex: 2027.2)"
            className="bg-[#0b0e14] border border-slate-800 rounded-lg px-3 py-1.5 text-xs font-mono text-slate-100 w-32"
          />
          <input
            value={newSemName}
            onChange={(e) => setNewSemName(e.target.value)}
            placeholder="Descrição do semestre"
            className="bg-[#0b0e14] border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-100 flex-1 min-w-48"
          />
          <button
            type="submit"
            className="px-3 py-1.5 rounded-lg bg-emerald-500 text-slate-950 text-xs font-semibold"
          >
            Criar
          </button>
        </form>
      )}

      {/* Split layout: Left subject list, Right subject cockpit */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-4 space-y-2">
          {subjects.map((subj) => {
            const m = metrics.subject_metrics.find((x) => x.subject_id === subj.id);
            const active = subj.id === selected?.id;
            return (
              <button
                key={subj.id}
                onClick={() => setSelectedId(subj.id)}
                className={`w-full text-left rounded-xl border p-3.5 transition ${
                  active
                    ? "bg-[#151a26] border-sky-500/50 shadow-lg shadow-sky-950/20"
                    : "bg-[#11141c] border-slate-800/90 hover:border-slate-700"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <span
                      className="w-2.5 h-2.5 rounded-full shrink-0"
                      style={{ backgroundColor: subj.cor }}
                    />
                    <span className="text-sm font-semibold text-slate-100 truncate">
                      {subj.nome}
                    </span>
                  </div>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                    {subj.codigo || subj.categoria}
                  </span>
                </div>

                <div className="mt-2.5 flex items-center justify-between text-[11px] text-slate-400 font-mono">
                  <span>
                    Leitura: {m?.week_reading_min ?? 0}/{subj.metas.leitura_min_semana}m
                  </span>
                  <span>
                    Questões: {m?.week_questions ?? 0}/{subj.metas.questoes_semana}
                  </span>
                </div>
                <div className="mt-1.5 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${m?.syllabus_progress_pct ?? 0}%`,
                      backgroundColor: subj.cor,
                    }}
                  />
                </div>
              </button>
            );
          })}
        </div>

        {/* Right Detail Panel */}
        <div className="lg:col-span-8">
          {!selected ? (
            <div className="rounded-xl border border-slate-800 bg-[#11141c] p-8 text-center text-sm text-slate-400">
              Selecione ou crie uma disciplina para começar.
            </div>
          ) : (
            <div className="space-y-4">
              {/* Subject Header */}
              <div className="rounded-xl border border-slate-800/90 bg-[#11141c] p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2.5">
                      <span
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: selected.cor }}
                      />
                      <h2 className="text-lg font-bold text-slate-100">{selected.nome}</h2>
                      <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                        {selected.id}
                      </span>
                    </div>
                    {selected.descricao && (
                      <p className="mt-1.5 text-xs text-slate-400 max-w-2xl">
                        {selected.descricao}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={() => {
                        setEditingSubject(selected);
                        setModalOpen(true);
                      }}
                      className="p-2 rounded-lg bg-slate-800/80 text-slate-300 hover:bg-slate-700"
                      title="Customizar disciplina"
                    >
                      <Pencil className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => handleDeleteSubject(selected)}
                      className="p-2 rounded-lg bg-slate-800/80 text-rose-400 hover:bg-rose-950/60"
                      title="Remover disciplina"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {/* Antigravity Quick Actions */}
                <div className="flex flex-wrap gap-2 mt-4 pt-4 border-t border-slate-800/80">
                  <button
                    onClick={() =>
                      onLaunchAgy(
                        `Gere uma lista de 5 questões progressivas de ${selected.nome} (id: ${selected.id}) com enunciado em LaTeX ($...$), dica e gabarito passo a passo, e importe automaticamente usando 'python3 hud_cli.py add-questions --subject ${selected.id}'.`
                      )
                    }
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-sky-500/15 border border-sky-500/35 text-sky-300 hover:bg-sky-500/25 text-xs font-medium"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    Gerar Lista IA no Antigravity
                  </button>
                  <button
                    onClick={() =>
                      onLaunchAgy(
                        `Crie um roteiro objetivo de leitura teórica para o próximo tópico pendente de ${selected.nome} (${selected.id}), usando os materiais em ${selected.materiais_dir} se existirem, e me ajude a estudar.`
                      )
                    }
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/15 border border-emerald-500/35 text-emerald-300 hover:bg-emerald-500/25 text-xs font-medium"
                  >
                    <BookOpen className="w-3.5 h-3.5" />
                    Roteiro de Leitura no Agy
                  </button>
                  <button
                    onClick={() => onOpenQuestions(selected.id)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-violet-500/15 border border-violet-500/35 text-violet-300 hover:bg-violet-500/25 text-xs font-medium"
                  >
                    Praticar Banco de Questões
                  </button>
                </div>
              </div>

              {/* Syllabus Topics */}
              <div className="rounded-xl border border-slate-800/90 bg-[#11141c] p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-slate-100">
                    Ementa & Progresso de Leitura
                  </h3>
                  <span className="text-xs font-mono text-slate-400">
                    {selected.topicos.filter((t) => t.leitura_concluida).length}/
                    {selected.topicos.length} leituras concluídas
                  </span>
                </div>

                <div className="space-y-2">
                  {selected.topicos.map((t) => (
                    <div
                      key={t.id}
                      className="flex items-center justify-between gap-2 rounded-lg border border-slate-800/70 bg-[#0b0e14] px-3 py-2"
                    >
                      <button
                        onClick={() =>
                          handleToggleReading(t.id, t.status, t.leitura_concluida)
                        }
                        className="flex items-center gap-2.5 text-left min-w-0 flex-1"
                        title="Marcar leitura teórica concluída"
                      >
                        {t.leitura_concluida ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                        ) : (
                          <Circle className="w-4 h-4 text-slate-600 shrink-0" />
                        )}
                        <span
                          className={`text-xs truncate ${
                            t.leitura_concluida
                              ? "text-slate-200"
                              : "text-slate-300"
                          }`}
                        >
                          {t.titulo}
                        </span>
                      </button>

                      <button
                        onClick={() =>
                          handleCycleTopic(t.id, t.status, t.leitura_concluida)
                        }
                        className={`text-[11px] px-2 py-0.5 rounded-md font-medium shrink-0 ${
                          STATUS_STYLE[t.status] ?? STATUS_STYLE.nao_iniciado
                        }`}
                        title="Clique para avançar status do tópico"
                      >
                        {STATUS_LABEL[t.status] ?? t.status}
                      </button>
                    </div>
                  ))}
                </div>

                <form onSubmit={handleAddTopic} className="flex gap-2 mt-3">
                  <input
                    value={newTopicTitle}
                    onChange={(e) => setNewTopicTitle(e.target.value)}
                    placeholder="Adicionar tópico à ementa..."
                    className="flex-1 bg-[#0b0e14] border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-sky-500"
                  />
                  <button
                    type="submit"
                    className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 font-medium"
                  >
                    + Tópico
                  </button>
                </form>
              </div>

              {/* Materials & Evaluations side-by-side */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Materials */}
                <div className="rounded-xl border border-slate-800/90 bg-[#11141c] p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-slate-100">
                      Materiais ({materials.length})
                    </h3>
                    <button
                      onClick={() =>
                        api.openPath(selected.materiais_dir || `estudos/${selected.id}`)
                      }
                      className="flex items-center gap-1 text-xs text-sky-400 hover:text-sky-300"
                    >
                      <FolderOpen className="w-3.5 h-3.5" /> Abrir pasta
                    </button>
                  </div>
                  <p className="text-[11px] font-mono text-slate-500 mb-2">
                    {selected.materiais_dir || `estudos/${selected.id}`}
                  </p>
                  {materials.length === 0 ? (
                    <p className="text-xs text-slate-500">
                      Envie PDFs, apostilas ou resumos .md pelo Antigravity para esta pasta — eles
                      aparecerão aqui automaticamente.
                    </p>
                  ) : (
                    <div className="space-y-1.5 max-h-52 overflow-y-auto pr-1">
                      {materials.map((m) => (
                        <button
                          key={m.abs_path}
                          onClick={() => api.openPath(m.abs_path)}
                          className="w-full flex items-center justify-between gap-2 px-2.5 py-2 rounded-lg bg-[#0b0e14] border border-slate-800/70 hover:border-sky-500/40 text-left transition"
                        >
                          <div className="flex items-center gap-2 min-w-0">
                            <FileText className="w-3.5 h-3.5 text-sky-400 shrink-0" />
                            <span className="text-xs text-slate-200 truncate">{m.name}</span>
                          </div>
                          <ExternalLink className="w-3 h-3 text-slate-500 shrink-0" />
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {/* Evaluations */}
                <div className="rounded-xl border border-slate-800/90 bg-[#11141c] p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-slate-100">Avaliações & Notas</h3>
                    <div className="flex items-center gap-2">
                      {weightedAvg(selected.avaliacoes) !== null && (
                        <span className="text-xs font-mono px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300">
                          Média: {weightedAvg(selected.avaliacoes)?.toFixed(2)}
                        </span>
                      )}
                      <button
                        onClick={handleAddEval}
                        className="text-xs text-sky-400 hover:text-sky-300"
                      >
                        + Av
                      </button>
                    </div>
                  </div>

                  <div className="space-y-2">
                    {selected.avaliacoes.map((av, idx) => (
                      <div
                        key={av.id + idx}
                        className="grid grid-cols-12 gap-1.5 items-center bg-[#0b0e14] border border-slate-800/70 rounded-lg px-2 py-1.5"
                      >
                        <input
                          value={av.nome}
                          onChange={(e) => handleUpdateEval(idx, { nome: e.target.value })}
                          className="col-span-4 bg-transparent text-xs text-slate-200 focus:outline-none"
                        />
                        <input
                          type="number"
                          step="0.1"
                          min="0"
                          max="10"
                          placeholder="Nota"
                          value={av.nota ?? ""}
                          onChange={(e) =>
                            handleUpdateEval(idx, {
                              nota: e.target.value === "" ? null : Number(e.target.value),
                            })
                          }
                          className="col-span-3 bg-slate-900 border border-slate-800 rounded px-1.5 py-1 text-xs font-mono text-sky-300"
                        />
                        <input
                          type="date"
                          value={av.data ?? ""}
                          onChange={(e) =>
                            handleUpdateEval(idx, { data: e.target.value || null })
                          }
                          className="col-span-5 bg-slate-900 border border-slate-800 rounded px-1.5 py-1 text-[11px] font-mono text-slate-300"
                        />
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {modalOpen && (
        <SubjectModal
          initial={editingSubject}
          onClose={() => setModalOpen(false)}
          onSave={handleSaveSubject}
        />
      )}
    </div>
  );
};
