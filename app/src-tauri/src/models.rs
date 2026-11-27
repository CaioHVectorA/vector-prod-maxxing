use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DailyGoals {
    #[serde(default = "default_goal_questions")]
    pub questoes: u32,
    #[serde(default = "default_goal_reading")]
    pub leitura_min: u32,
    #[serde(default = "default_goal_focus")]
    pub foco_min: u32,
}

fn default_goal_questions() -> u32 {
    5
}
fn default_goal_reading() -> u32 {
    45
}
fn default_goal_focus() -> u32 {
    90
}

impl Default for DailyGoals {
    fn default() -> Self {
        Self {
            questoes: 5,
            leitura_min: 45,
            foco_min: 90,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgyConfig {
    #[serde(default = "default_agy_cli")]
    pub cli_command: String,
    #[serde(default = "default_terminal_cmd")]
    pub terminal_command: String,
    #[serde(default = "default_develop_dirs")]
    pub develop_dirs: Vec<String>,
    #[serde(default = "default_true")]
    pub auto_git_sync: bool,
}

fn default_agy_cli() -> String {
    "antigravity".to_string()
}
fn default_terminal_cmd() -> String {
    "x-terminal-emulator".to_string()
}
fn default_develop_dirs() -> Vec<String> {
    vec!["~/develop".to_string()]
}
fn default_true() -> bool {
    true
}

impl Default for AgyConfig {
    fn default() -> Self {
        Self {
            cli_command: default_agy_cli(),
            terminal_command: default_terminal_cmd(),
            develop_dirs: default_develop_dirs(),
            auto_git_sync: true,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct SubjectGoals {
    #[serde(default)]
    pub questoes_semana: u32,
    #[serde(default)]
    pub leitura_min_semana: u32,
    #[serde(default)]
    pub sessoes_semana: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Evaluation {
    pub id: String,
    pub nome: String,
    #[serde(default = "default_peso")]
    pub peso: f64,
    #[serde(default)]
    pub nota: Option<f64>,
    #[serde(default)]
    pub data: Option<String>,
}

fn default_peso() -> f64 {
    1.0
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyllabusTopic {
    pub id: String,
    pub titulo: String,
    #[serde(default = "default_topic_status")]
    pub status: String, // nao_iniciado | lendo | praticando | dominado
    #[serde(default)]
    pub leitura_concluida: bool,
    #[serde(default)]
    pub questoes_resolvidas: u32,
}

fn default_topic_status() -> String {
    "nao_iniciado".to_string()
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Subject {
    pub id: String,
    pub nome: String,
    #[serde(default)]
    pub codigo: String,
    #[serde(default = "default_categoria")]
    pub categoria: String,
    #[serde(default = "default_prioridade")]
    pub prioridade: String,
    #[serde(default = "default_cor")]
    pub cor: String,
    #[serde(default)]
    pub descricao: String,
    #[serde(default)]
    pub materiais_dir: String,
    #[serde(default)]
    pub questoes_file: String,
    #[serde(default)]
    pub metas: SubjectGoals,
    #[serde(default)]
    pub avaliacoes: Vec<Evaluation>,
    #[serde(default)]
    pub topicos: Vec<SyllabusTopic>,
    #[serde(default)]
    pub ultimo_estudo: Option<String>,
    #[serde(default)]
    pub ultima_leitura: Option<String>,
}

fn default_categoria() -> String {
    "teorica".to_string()
}
fn default_prioridade() -> String {
    "media".to_string()
}
fn default_cor() -> String {
    "#38bdf8".to_string()
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Semester {
    pub id: String,
    pub nome: String,
    #[serde(default = "default_sem_status")]
    pub status: String,
    #[serde(default)]
    pub inicio: Option<String>,
    #[serde(default)]
    pub fim: Option<String>,
    #[serde(default)]
    pub disciplinas: Vec<Subject>,
}

fn default_sem_status() -> String {
    "ativo".to_string()
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct AppData {
    #[serde(default)]
    pub schema_version: u32,
    #[serde(default = "default_active_semester")]
    pub active_semester: String,
    #[serde(default)]
    pub daily_goals: DailyGoals,
    #[serde(default)]
    pub agy_config: AgyConfig,
    #[serde(default)]
    pub semesters: BTreeMap<String, Semester>,
    #[serde(flatten)]
    pub extra: BTreeMap<String, Value>,
}

fn default_active_semester() -> String {
    "2027.1".to_string()
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Question {
    pub id: String,
    #[serde(default)]
    pub topico: String,
    #[serde(default = "default_dificuldade")]
    pub dificuldade: String,
    pub enunciado: String,
    #[serde(default)]
    pub dica: String,
    #[serde(default)]
    pub gabarito: String,
    #[serde(default = "default_q_status")]
    pub status: String, // pendente | acertei | errei | revisar
    #[serde(default)]
    pub attempts: u32,
    #[serde(default)]
    pub last_attempt: Option<String>,
}

fn default_dificuldade() -> String {
    "media".to_string()
}
fn default_q_status() -> String {
    "pendente".to_string()
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectItem {
    pub id: String,
    pub nome: String,
    #[serde(default = "default_proj_cat")]
    pub categoria: String, // code | robotics | hardware
    #[serde(default = "default_sem_status")]
    pub status: String,
    #[serde(default = "default_prioridade")]
    pub prioridade: String,
    #[serde(default)]
    pub stack: Vec<String>,
    #[serde(default)]
    pub repo_name: String,
    #[serde(default)]
    pub descricao: String,
    #[serde(default)]
    pub next_action: String,
    #[serde(default)]
    pub pinned: bool,
}

fn default_proj_cat() -> String {
    "code".to_string()
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EventRecord {
    #[serde(default)]
    pub ts: Option<String>,
    #[serde(default)]
    pub timestamp: Option<String>,
    #[serde(default)]
    pub env: Option<String>,
    #[serde(rename = "type", default)]
    pub event_type: String,
    #[serde(default)]
    pub subject: Option<String>,
    #[serde(default)]
    pub project: Option<String>,
    #[serde(default)]
    pub category: Option<String>,
    #[serde(default)]
    pub questions: Option<u32>,
    #[serde(default)]
    pub reading_min: Option<u32>,
    #[serde(default)]
    pub pages: Option<u32>,
    #[serde(default)]
    pub duration_min: Option<u32>,
    #[serde(default)]
    pub mode: Option<String>,
    #[serde(default)]
    pub topic: Option<String>,
    #[serde(default)]
    pub result: Option<String>,
    #[serde(default)]
    pub summary: Option<String>,
    #[serde(default)]
    pub question_id: Option<String>,
}

impl EventRecord {
    pub fn effective_ts(&self) -> Option<&str> {
        self.ts.as_deref().or(self.timestamp.as_deref())
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HeatmapDay {
    pub date: String,
    pub questions: u32,
    pub reading_min: u32,
    pub focus_min: u32,
    pub project_min: u32,
    pub score: u32,
    pub level: u8, // 0..4
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SubjectMetric {
    pub subject_id: String,
    pub nome: String,
    pub cor: String,
    pub prioridade: String,
    pub week_questions: u32,
    pub week_reading_min: u32,
    pub week_sessions: u32,
    pub goal_questions: u32,
    pub goal_reading_min: u32,
    pub days_since_study: Option<i64>,
    pub days_since_reading: Option<i64>,
    pub syllabus_progress_pct: u32,
    pub reading_topics_done: u32,
    pub total_topics: u32,
    pub neglected: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetricsSummary {
    pub today_date: String,
    pub today_questions: u32,
    pub today_reading_min: u32,
    pub today_focus_min: u32,
    pub today_project_min: u32,
    pub daily_goals: DailyGoals,
    pub current_streak: u32,
    pub best_streak: u32,
    pub active_days_30d: u32,
    pub consistency_score: u32,
    pub week_questions: u32,
    pub week_reading_min: u32,
    pub week_project_min: u32,
    pub reading_ratio_pct: u32,
    pub heatmap: Vec<HeatmapDay>,
    pub subject_metrics: Vec<SubjectMetric>,
    pub recent_events: Vec<EventRecord>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StudyMaterial {
    pub name: String,
    pub rel_path: String,
    pub abs_path: String,
    pub ext: String,
    pub size_bytes: u64,
    pub modified_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GitRepoInfo {
    pub name: String,
    pub path: String,
    pub branch: String,
    pub dirty_files: usize,
    pub last_commit_msg: String,
    pub last_commit_rel: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SerialDevice {
    pub port: String,
    pub label: String,
    pub board_hint: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FirmwareItem {
    pub board: String,
    pub name: String,
    pub path: String,
    pub files: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgyStatus {
    pub cli_command: String,
    pub cli_available: bool,
    pub resolved_path: Option<String>,
    pub repo_dir: String,
    pub hud_cli_path: String,
}
