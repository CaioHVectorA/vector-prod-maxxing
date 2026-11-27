import React, { useEffect, useMemo, useState } from "react";
import {
  CheckCircle2,
  Eye,
  EyeOff,
  HelpCircle,
  RotateCcw,
  Sparkles,
  Upload,
  XCircle,
} from "lucide-react";
import { api } from "../api";
import { MathText } from "../components/MathText";
import type { Question, Subject } from "../types";

interface QuestionsViewProps {
  subjects: Subject[];
  initialSubjectId?: string | null;
  onRefreshMetrics: () => Promise<void>;
  onLaunchAgy: (prompt: string) => Promise<void>;
  onNotify: (msg: string) => void;
}

const STATUS_BADGE: Record<string, string> = {
  pendente: "bg-slate-800 text-slate-300",
  acertei: "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30",
  revisar: "bg-amber-500/20 text-amber-300 border border-amber-500/30",
  errei: "bg-rose-500/20 text-rose-300 border border-rose-500/30",
};

export const QuestionsView: React.FC<QuestionsViewProps> = ({
  subjects,
  initialSubjectId,
  onRefreshMetrics,
  onLaunchAgy,
  onNotify,
}) => {
  const [subjectId, setSubjectId] = useState<string>(
    initialSubjectId || subjects[0]?.id || ""
  );
  const [questions, setQuestions] = useState<Question[]>([]);
  const [filterStatus, setFilterStatus] = useState<string>("todas");
  const [revealedHints, setRevealedHints] = useState<Record<string, boolean>>({});
  const [revealedSolutions, setRevealedSolutions] = useState<Record<string, boolean>>({});
  const [importOpen, setImportOpen] = useState(false);
  const [importText, setImportText] = useState("");

  useEffect(() => {
    if (initialSubjectId && subjects.some((s) => s.id === initialSubjectId)) {
      setSubjectId(initialSubjectId);
    } else if (!subjects.some((s) => s.id === subjectId) && subjects[0]) {
      setSubjectId(subjects[0].id);
    }
  }, [initialSubjectId, subjects, subjectId]);

  const loadQuestions = async (sid: string) => {
    if (!sid) return;
    try {
      const list = await api.getQuestions(sid);
      setQuestions(list);
    } catch {
      setQuestions([]);
    }
  };

  useEffect(() => {
    loadQuestions(subjectId);
  }, [subjectId]);

  const selectedSubject = subjects.find((s) => s.id === subjectId);

  const filtered = useMemo(() => {
    if (filterStatus === "todas") return questions;
    return questions.filter((q) => (q.status || "pendente") === filterStatus);
  }, [questions, filterStatus]);

  const stats = useMemo(() => {
    const total = questions.length;
    const acertei = questions.filter((q) => q.status === "acertei").length;
    const revisar = questions.filter((q) => q.status === "revisar").length;
    const errei = questions.filter((q) => q.status === "errei").length;
    return { total, acertei, revisar, errei };
  }, [questions]);

  const handleMark = async (qid: string, result: "acertei" | "errei" | "revisar") => {
    const updated = await api.recordQuestionAttempt({
      subject_id: subjectId,
      question_id: qid,
      result,
    });
    setQuestions(updated);
    await onRefreshMetrics();
    onNotify(
      result === "acertei"
        ? "Questão marcada como acertada! (+1 no progresso de hoje)"
        : result === "revisar"
        ? "Questão marcada para revisão."
        : "Questão marcada como erro — boa para revisar depois!"
    );
  };

  const handleImport = async () => {
    if (!importText.trim() || !subjectId) return;
    try {
      const updated = await api.importQuestionsJson(subjectId, importText);
      setQuestions(updated);
      setImportText("");
      setImportOpen(false);
      onNotify(`Lista importada! Total de ${updated.length} questões em ${subjectId}.`);
    } catch (e) {
      onNotify(`Erro ao importar JSON: ${String(e)}`);
    }
  };

  return (
    <div className="space-y-4">
      {/* Top Controls */}
      <div className="rounded-xl border border-slate-800/90 bg-[#11141c] p-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={subjectId}
            onChange={(e) => setSubjectId(e.target.value)}
            className="bg-[#0b0e14] border border-slate-700 rounded-lg px-3 py-2 text-xs font-semibold text-slate-100 focus:outline-none focus:border-sky-500"
          >
            {subjects.map((s) => (
              <option key={s.id} value={s.id}>
                {s.nome} ({s.id})
              </option>
            ))}
          </select>

          <div className="flex gap-1 bg-[#0b0e14] p-1 rounded-lg border border-slate-800">
            {(
              [
                ["todas", `Todas (${stats.total})`],
                ["pendente", "Pendentes"],
                ["errei", `Errei (${stats.errei})`],
                ["revisar", `Revisar (${stats.revisar})`],
                ["acertei", `Acertei (${stats.acertei})`],
              ] as const
            ).map(([k, label]) => (
              <button
                key={k}
                onClick={() => setFilterStatus(k)}
                className={`px-2.5 py-1 rounded text-xs transition ${
                  filterStatus === k
                    ? "bg-slate-800 text-sky-300 font-medium"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setImportOpen((v) => !v)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-800 text-slate-200 hover:bg-slate-700 text-xs font-medium"
          >
            <Upload className="w-3.5 h-3.5" />
            Colar JSON
          </button>
          <button
            onClick={() =>
              onLaunchAgy(
                `Gere uma nova lista de 6 questões de ${selectedSubject?.nome ?? subjectId} (id: ${subjectId}) variando de fácil a difícil, com fórmulas em LaTeX ($...$), dica e gabarito completo, e salve no banco usando 'python3 hud_cli.py add-questions --subject ${subjectId}'.`
              )
            }
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-sky-500 text-slate-950 hover:bg-sky-400 text-xs font-semibold"
          >
            <Sparkles className="w-3.5 h-3.5" />
            Gerar Nova Lista no Antigravity
          </button>
        </div>
      </div>

      {importOpen && (
        <div className="rounded-xl border border-slate-800 bg-[#11141c] p-4 space-y-2">
          <p className="text-xs text-slate-400">
            Cole um array JSON de questões (ou peça ao Antigravity para rodar{" "}
            <code className="text-sky-300">python3 hud_cli.py add-questions --subject {subjectId}</code>):
          </p>
          <textarea
            rows={5}
            value={importText}
            onChange={(e) => setImportText(e.target.value)}
            placeholder='[{"id": "q1", "topico": "...", "dificuldade": "media", "enunciado": "...", "dica": "...", "gabarito": "..."}]'
            className="w-full bg-[#0b0e14] border border-slate-800 rounded-lg p-3 text-xs font-mono text-slate-200"
          />
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setImportOpen(false)}
              className="px-3 py-1.5 rounded-lg text-xs text-slate-400 hover:bg-slate-800"
            >
              Cancelar
            </button>
            <button
              onClick={handleImport}
              className="px-3.5 py-1.5 rounded-lg bg-emerald-500 text-slate-950 text-xs font-semibold"
            >
              Importar Questões
            </button>
          </div>
        </div>
      )}

      {/* Question Cards */}
      {filtered.length === 0 ? (
        <div className="rounded-xl border border-slate-800 bg-[#11141c] p-10 text-center space-y-3">
          <p className="text-sm text-slate-300">
            Nenhuma questão encontrada neste filtro para{" "}
            <span className="font-semibold text-sky-300">
              {selectedSubject?.nome ?? subjectId}
            </span>
            .
          </p>
          <p className="text-xs text-slate-500">
            Use o botão &quot;Gerar Nova Lista no Antigravity&quot; acima para criar questões sob
            medida com LaTeX e gabarito passo a passo.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filtered.map((q, index) => {
            const showHint = Boolean(revealedHints[q.id]);
            const showSol = Boolean(revealedSolutions[q.id]);
            return (
              <div
                key={q.id}
                className="rounded-xl border border-slate-800/90 bg-[#11141c] p-5 space-y-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs font-mono text-slate-500">#{index + 1}</span>
                    <span className="text-xs font-semibold text-sky-300 bg-sky-500/10 border border-sky-500/20 px-2 py-0.5 rounded">
                      {q.topico || "Geral"}
                    </span>
                    <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                      {q.dificuldade || "media"}
                    </span>
                    <span
                      className={`text-[11px] px-2 py-0.5 rounded font-medium ${
                        STATUS_BADGE[q.status] ?? STATUS_BADGE.pendente
                      }`}
                    >
                      {q.status || "pendente"}
                    </span>
                  </div>
                  <button
                    onClick={() =>
                      onLaunchAgy(
                        `Me ajude a entender passo a passo esta questão de ${selectedSubject?.nome ?? subjectId} (${q.topico}):\n\n${q.enunciado}`
                      )
                    }
                    className="flex items-center gap-1 text-xs text-sky-400 hover:text-sky-300"
                  >
                    <Sparkles className="w-3.5 h-3.5" /> Explicar no Antigravity
                  </button>
                </div>

                {/* Statement with KaTeX */}
                <div className="text-sm text-slate-100 bg-[#0b0e14] border border-slate-800/80 rounded-lg p-4">
                  <MathText text={q.enunciado} />
                </div>

                {/* Hint & Solution toggles */}
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    {q.dica && (
                      <button
                        onClick={() =>
                          setRevealedHints((prev) => ({ ...prev, [q.id]: !prev[q.id] }))
                        }
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800/80 text-amber-300 hover:bg-slate-800 text-xs"
                      >
                        <HelpCircle className="w-3.5 h-3.5" />
                        {showHint ? "Ocultar Dica" : "Ver Dica"}
                      </button>
                    )}
                    {q.gabarito && (
                      <button
                        onClick={() =>
                          setRevealedSolutions((prev) => ({ ...prev, [q.id]: !prev[q.id] }))
                        }
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800/80 text-sky-300 hover:bg-slate-800 text-xs"
                      >
                        {showSol ? (
                          <EyeOff className="w-3.5 h-3.5" />
                        ) : (
                          <Eye className="w-3.5 h-3.5" />
                        )}
                        {showSol ? "Ocultar Gabarito" : "Ver Gabarito"}
                      </button>
                    )}
                  </div>

                  {/* Self-assessment actions */}
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={() => handleMark(q.id, "acertei")}
                      className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-emerald-500/15 border border-emerald-500/35 text-emerald-300 hover:bg-emerald-500/25 text-xs font-semibold"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" /> Acertei
                    </button>
                    <button
                      onClick={() => handleMark(q.id, "revisar")}
                      className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-amber-500/15 border border-amber-500/35 text-amber-300 hover:bg-amber-500/25 text-xs font-semibold"
                    >
                      <RotateCcw className="w-3.5 h-3.5" /> Revisar
                    </button>
                    <button
                      onClick={() => handleMark(q.id, "errei")}
                      className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-rose-500/15 border border-rose-500/35 text-rose-300 hover:bg-rose-500/25 text-xs font-semibold"
                    >
                      <XCircle className="w-3.5 h-3.5" /> Errei
                    </button>
                  </div>
                </div>

                {showHint && q.dica && (
                  <div className="rounded-lg border border-amber-500/25 bg-amber-950/15 p-3 text-xs text-amber-200">
                    <div className="font-semibold mb-1">Dica</div>
                    <MathText text={q.dica} />
                  </div>
                )}

                {showSol && q.gabarito && (
                  <div className="rounded-lg border border-emerald-500/25 bg-emerald-950/15 p-3.5 text-xs text-emerald-100">
                    <div className="font-semibold text-emerald-300 mb-1">
                      Resolução / Gabarito
                    </div>
                    <MathText text={q.gabarito} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
