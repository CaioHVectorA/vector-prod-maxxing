import React, { useState } from "react";
import { X } from "lucide-react";
import type { Subject } from "../types";

const PALETTE = [
  "#38bdf8",
  "#2dd4bf",
  "#a78bfa",
  "#f472b6",
  "#fbbf24",
  "#fb923c",
  "#34d399",
  "#818cf8",
];

interface SubjectModalProps {
  initial?: Subject | null;
  onClose: () => void;
  onSave: (subject: Subject) => Promise<void>;
}

export const SubjectModal: React.FC<SubjectModalProps> = ({
  initial,
  onClose,
  onSave,
}) => {
  const isEdit = Boolean(initial);
  const [nome, setNome] = useState(initial?.nome ?? "");
  const [id, setId] = useState(initial?.id ?? "");
  const [codigo, setCodigo] = useState(initial?.codigo ?? "");
  const [categoria, setCategoria] = useState(initial?.categoria ?? "teorica");
  const [prioridade, setPrioridade] = useState(initial?.prioridade ?? "alta");
  const [cor, setCor] = useState(initial?.cor ?? PALETTE[0]);
  const [descricao, setDescricao] = useState(initial?.descricao ?? "");
  const [qSemana, setQSemana] = useState(initial?.metas.questoes_semana ?? 12);
  const [lSemana, setLSemana] = useState(initial?.metas.leitura_min_semana ?? 120);
  const [sSemana, setSSemana] = useState(initial?.metas.sessoes_semana ?? 3);
  const [saving, setSaving] = useState(false);

  const slugify = (s: string) =>
    s
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_|_$/g, "");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const finalId = (id.trim() || slugify(nome)).slice(0, 40);
    if (!nome.trim() || !finalId) return;
    setSaving(true);
    try {
      const subject: Subject = {
        id: finalId,
        nome: nome.trim(),
        codigo: codigo.trim() || finalId.toUpperCase(),
        categoria,
        prioridade,
        cor,
        descricao: descricao.trim(),
        materiais_dir: initial?.materiais_dir || `estudos/${finalId}`,
        questoes_file: initial?.questoes_file || `${finalId}.json`,
        metas: {
          questoes_semana: Number(qSemana) || 0,
          leitura_min_semana: Number(lSemana) || 0,
          sessoes_semana: Number(sSemana) || 1,
        },
        avaliacoes: initial?.avaliacoes ?? [
          { id: "p1", nome: "P1", peso: 1, nota: null, data: null },
          { id: "p2", nome: "P2", peso: 1, nota: null, data: null },
        ],
        topicos: initial?.topicos ?? [],
        ultimo_estudo: initial?.ultimo_estudo ?? null,
        ultima_leitura: initial?.ultima_leitura ?? null,
      };
      await onSave(subject);
      onClose();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4">
      <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-[#11141c] shadow-2xl overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800">
          <h2 className="text-base font-semibold text-slate-100">
            {isEdit ? `Editar ${initial?.nome}` : "Nova Disciplina"}
          </h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-slate-100"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Nome da Disciplina</label>
              <input
                required
                value={nome}
                onChange={(e) => {
                  setNome(e.target.value);
                  if (!isEdit) setId(slugify(e.target.value));
                }}
                placeholder="Ex: Eletromagnetismo"
                className="w-full bg-[#0b0e14] border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-sky-500"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">ID (CLI / pasta)</label>
              <input
                required
                disabled={isEdit}
                value={id}
                onChange={(e) => setId(slugify(e.target.value))}
                placeholder="eletromagnetismo"
                className="w-full bg-[#0b0e14] border border-slate-800 rounded-lg px-3 py-2 text-sm font-mono text-slate-200 disabled:opacity-50 focus:outline-none focus:border-sky-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Código</label>
              <input
                value={codigo}
                onChange={(e) => setCodigo(e.target.value)}
                placeholder="ELETROMAG"
                className="w-full bg-[#0b0e14] border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-sky-500"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Categoria</label>
              <select
                value={categoria}
                onChange={(e) => setCategoria(e.target.value)}
                className="w-full bg-[#0b0e14] border border-slate-800 rounded-lg px-2.5 py-2 text-xs text-slate-200"
              >
                <option value="teorica">Teórica</option>
                <option value="engenharia">Engenharia</option>
                <option value="laboratorio">Laboratório</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Prioridade</label>
              <select
                value={prioridade}
                onChange={(e) => setPrioridade(e.target.value)}
                className="w-full bg-[#0b0e14] border border-slate-800 rounded-lg px-2.5 py-2 text-xs text-slate-200"
              >
                <option value="alta">Alta</option>
                <option value="media">Média</option>
                <option value="baixa">Baixa</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">Descrição / Ementa curta</label>
            <textarea
              rows={2}
              value={descricao}
              onChange={(e) => setDescricao(e.target.value)}
              className="w-full bg-[#0b0e14] border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-sky-500"
            />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Meta Questões/sem</label>
              <input
                type="number"
                min={0}
                value={qSemana}
                onChange={(e) => setQSemana(Number(e.target.value))}
                className="w-full bg-[#0b0e14] border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-slate-200"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Meta Leitura (min/sem)</label>
              <input
                type="number"
                min={0}
                value={lSemana}
                onChange={(e) => setLSemana(Number(e.target.value))}
                className="w-full bg-[#0b0e14] border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-slate-200"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Sessões/sem</label>
              <input
                type="number"
                min={1}
                value={sSemana}
                onChange={(e) => setSSemana(Number(e.target.value))}
                className="w-full bg-[#0b0e14] border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-slate-200"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1.5">Cor da Disciplina</label>
            <div className="flex gap-2">
              {PALETTE.map((c) => (
                <button
                  type="button"
                  key={c}
                  onClick={() => setCor(c)}
                  className={`w-6 h-6 rounded-full transition-transform ${
                    cor === c ? "scale-125 ring-2 ring-white" : "opacity-70 hover:opacity-100"
                  }`}
                  style={{ backgroundColor: c }}
                />
              ))}
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-xs text-slate-400 hover:bg-slate-800"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 rounded-lg bg-sky-500 text-slate-950 text-xs font-semibold hover:bg-sky-400 disabled:opacity-50"
            >
              {saving ? "Salvando..." : "Salvar Disciplina"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
