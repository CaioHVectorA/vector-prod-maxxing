export interface DailyGoals {
  questoes: number;
  leitura_min: number;
  foco_min: number;
}

export interface AgyConfig {
  cli_command: string;
  terminal_command: string;
  develop_dirs: string[];
  auto_git_sync: boolean;
}

export interface SubjectGoals {
  questoes_semana: number;
  leitura_min_semana: number;
  sessoes_semana: number;
}

export interface Evaluation {
  id: string;
  nome: string;
  peso: number;
  nota: number | null;
  data: string | null;
}

export type TopicStatus = "nao_iniciado" | "lendo" | "praticando" | "dominado";

export interface SyllabusTopic {
  id: string;
  titulo: string;
  status: TopicStatus;
  leitura_concluida: boolean;
  questoes_resolvidas: number;
}

export interface Subject {
  id: string;
  nome: string;
  codigo: string;
  categoria: "teorica" | "laboratorio" | "engenharia" | string;
  prioridade: "alta" | "media" | "baixa" | string;
  cor: string;
  descricao: string;
  materiais_dir: string;
  questoes_file: string;
  metas: SubjectGoals;
  avaliacoes: Evaluation[];
  topicos: SyllabusTopic[];
  ultimo_estudo: string | null;
  ultima_leitura: string | null;
}

export interface Semester {
  id: string;
  nome: string;
  status: string;
  inicio?: string | null;
  fim?: string | null;
  disciplinas: Subject[];
}

export interface AppData {
  schema_version: number;
  active_semester: string;
  daily_goals: DailyGoals;
  agy_config: AgyConfig;
  semesters: Record<string, Semester>;
  [key: string]: unknown;
}

export interface Question {
  id: string;
  topico: string;
  dificuldade: "facil" | "media" | "dificil" | string;
  enunciado: string;
  dica: string;
  gabarito: string;
  status: "pendente" | "acertei" | "errei" | "revisar" | string;
  attempts: number;
  last_attempt?: string | null;
}

export interface ProjectItem {
  id: string;
  nome: string;
  categoria: "code" | "robotics" | "hardware" | string;
  status: string;
  prioridade: string;
  stack: string[];
  repo_name: string;
  descricao: string;
  next_action: string;
  pinned: boolean;
}

export interface EventRecord {
  ts?: string | null;
  timestamp?: string | null;
  env?: string | null;
  type: string;
  subject?: string | null;
  project?: string | null;
  category?: string | null;
  questions?: number | null;
  reading_min?: number | null;
  pages?: number | null;
  duration_min?: number | null;
  mode?: string | null;
  topic?: string | null;
  result?: string | null;
  summary?: string | null;
  question_id?: string | null;
}

export interface HeatmapDay {
  date: string;
  questions: number;
  reading_min: number;
  focus_min: number;
  project_min: number;
  score: number;
  level: number;
}

export interface SubjectMetric {
  subject_id: string;
  nome: string;
  cor: string;
  prioridade: string;
  week_questions: number;
  week_reading_min: number;
  week_sessions: number;
  goal_questions: number;
  goal_reading_min: number;
  days_since_study: number | null;
  days_since_reading: number | null;
  syllabus_progress_pct: number;
  reading_topics_done: number;
  total_topics: number;
  neglected: boolean;
}

export interface MetricsSummary {
  today_date: string;
  today_questions: number;
  today_reading_min: number;
  today_focus_min: number;
  today_project_min: number;
  daily_goals: DailyGoals;
  current_streak: number;
  best_streak: number;
  active_days_30d: number;
  consistency_score: number;
  week_questions: number;
  week_reading_min: number;
  week_project_min: number;
  reading_ratio_pct: number;
  heatmap: HeatmapDay[];
  subject_metrics: SubjectMetric[];
  recent_events: EventRecord[];
}

export interface StudyMaterial {
  name: string;
  rel_path: string;
  abs_path: string;
  ext: string;
  size_bytes: number;
  modified_at: string;
}

export interface GitRepoInfo {
  name: string;
  path: string;
  branch: string;
  dirty_files: number;
  last_commit_msg: string;
  last_commit_rel: string;
}

export interface SerialDevice {
  port: string;
  label: string;
  board_hint: string;
}

export interface FirmwareItem {
  board: string;
  name: string;
  path: string;
  files: string[];
}

export interface HardwareSnapshot {
  serial_devices: SerialDevice[];
  firmwares: FirmwareItem[];
}

export interface AgyStatus {
  cli_command: string;
  cli_available: boolean;
  resolved_path: string | null;
  repo_dir: string;
  hud_cli_path: string;
}
