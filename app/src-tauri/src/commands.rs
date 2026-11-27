use crate::agy;
use crate::metrics;
use crate::models::{
    AgyStatus, AppData, Evaluation, EventRecord, FirmwareItem, GitRepoInfo, MetricsSummary,
    ProjectItem, Question, Semester, SerialDevice, StudyMaterial, Subject, SyllabusTopic,
};
use crate::scanner;
use crate::state::{self, RepoPaths};
use chrono::Local;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use tauri::State;

pub struct AppState {
    pub paths: RepoPaths,
}

#[derive(Debug, Serialize)]
pub struct HardwareSnapshot {
    pub serial_devices: Vec<SerialDevice>,
    pub firmwares: Vec<FirmwareItem>,
}

#[derive(Debug, Deserialize)]
pub struct LogStudyPayload {
    pub subject_id: String,
    pub questions: u32,
    pub reading_min: u32,
    pub pages: u32,
    pub duration_min: u32,
    pub mode: String,
    pub topic: String,
}

#[derive(Debug, Deserialize)]
pub struct QuestionAttemptPayload {
    pub subject_id: String,
    pub question_id: String,
    pub result: String, // acertei | errei | revisar
}

#[derive(Debug, Deserialize)]
pub struct LogProjectPayload {
    pub project_id: String,
    pub category: String,
    pub duration_min: u32,
    pub summary: String,
    pub next_action: Option<String>,
}

#[tauri::command]
pub fn get_app_data(state: State<'_, AppState>) -> Result<AppData, String> {
    state::load_app_data(&state.paths)
}

#[tauri::command]
pub fn save_app_data_cmd(state: State<'_, AppState>, data: AppData) -> Result<AppData, String> {
    state::save_app_data(&state.paths, &data)?;
    Ok(data)
}

#[tauri::command]
pub fn set_active_semester(
    state: State<'_, AppState>,
    semester_id: String,
) -> Result<AppData, String> {
    let mut data = state::load_app_data(&state.paths)?;
    if !data.semesters.contains_key(&semester_id) {
        return Err(format!("Semestre '{semester_id}' não encontrado."));
    }
    data.active_semester = semester_id;
    state::save_app_data(&state.paths, &data)?;
    Ok(data)
}

#[tauri::command]
pub fn create_semester(
    state: State<'_, AppState>,
    id: String,
    nome: String,
) -> Result<AppData, String> {
    let mut data = state::load_app_data(&state.paths)?;
    if data.semesters.contains_key(&id) {
        return Err(format!("Semestre '{id}' já existe."));
    }
    data.semesters.insert(
        id.clone(),
        Semester {
            id: id.clone(),
            nome,
            status: "ativo".to_string(),
            inicio: None,
            fim: None,
            disciplinas: Vec::new(),
        },
    );
    data.active_semester = id;
    state::save_app_data(&state.paths, &data)?;
    Ok(data)
}

#[tauri::command]
pub fn upsert_subject(
    state: State<'_, AppState>,
    semester_id: String,
    mut subject: Subject,
) -> Result<AppData, String> {
    let mut data = state::load_app_data(&state.paths)?;
    if subject.materiais_dir.trim().is_empty() {
        subject.materiais_dir = format!("estudos/{}", subject.id);
    }
    if subject.questoes_file.trim().is_empty() {
        subject.questoes_file = format!("{}.json", subject.id);
    }

    let mat_dir = state.paths.repo_dir.join(&subject.materiais_dir);
    let _ = fs::create_dir_all(&mat_dir);

    let sem = data
        .semesters
        .get_mut(&semester_id)
        .ok_or_else(|| format!("Semestre '{semester_id}' não encontrado."))?;

    if let Some(existing) = sem.disciplinas.iter_mut().find(|d| d.id == subject.id) {
        *existing = subject;
    } else {
        sem.disciplinas.push(subject);
    }

    state::save_app_data(&state.paths, &data)?;
    Ok(data)
}

#[tauri::command]
pub fn delete_subject(
    state: State<'_, AppState>,
    semester_id: String,
    subject_id: String,
) -> Result<AppData, String> {
    let mut data = state::load_app_data(&state.paths)?;
    let sem = data
        .semesters
        .get_mut(&semester_id)
        .ok_or_else(|| format!("Semestre '{semester_id}' não encontrado."))?;
    sem.disciplinas.retain(|d| d.id != subject_id);
    state::save_app_data(&state.paths, &data)?;
    Ok(data)
}

#[tauri::command]
pub fn update_topic_state(
    state: State<'_, AppState>,
    semester_id: String,
    subject_id: String,
    topic_id: String,
    status: String,
    leitura_concluida: bool,
) -> Result<AppData, String> {
    let mut data = state::load_app_data(&state.paths)?;
    let now = Local::now().format("%Y-%m-%dT%H:%M:%S").to_string();
    let sem = data
        .semesters
        .get_mut(&semester_id)
        .ok_or_else(|| "Semestre não encontrado".to_string())?;
    let subj = sem
        .disciplinas
        .iter_mut()
        .find(|d| d.id == subject_id)
        .ok_or_else(|| "Disciplina não encontrada".to_string())?;

    let mut topic_title = String::new();
    if let Some(topic) = subj.topicos.iter_mut().find(|t| t.id == topic_id) {
        topic.status = status.clone();
        topic.leitura_concluida = leitura_concluida;
        topic_title = topic.titulo.clone();
    }
    subj.ultimo_estudo = Some(now.clone());
    if leitura_concluida {
        subj.ultima_leitura = Some(now.clone());
    }

    state::save_app_data(&state.paths, &data)?;
    let _ = state::append_event(
        &state.paths,
        &EventRecord {
            ts: Some(now),
            timestamp: None,
            env: Some(state::hostname()),
            event_type: "topic_update".to_string(),
            subject: Some(subject_id),
            project: None,
            category: None,
            questions: None,
            reading_min: None,
            pages: None,
            duration_min: None,
            mode: Some(status),
            topic: Some(topic_title),
            result: None,
            summary: None,
            question_id: None,
        },
    );
    Ok(data)
}

#[tauri::command]
pub fn add_topic(
    state: State<'_, AppState>,
    semester_id: String,
    subject_id: String,
    titulo: String,
) -> Result<AppData, String> {
    let mut data = state::load_app_data(&state.paths)?;
    let sem = data
        .semesters
        .get_mut(&semester_id)
        .ok_or_else(|| "Semestre não encontrado".to_string())?;
    let subj = sem
        .disciplinas
        .iter_mut()
        .find(|d| d.id == subject_id)
        .ok_or_else(|| "Disciplina não encontrada".to_string())?;

    let id = format!(
        "{}_t{}",
        subject_id,
        Local::now().timestamp_millis() % 1_000_000
    );
    subj.topicos.push(SyllabusTopic {
        id,
        titulo,
        status: "nao_iniciado".to_string(),
        leitura_concluida: false,
        questoes_resolvidas: 0,
    });
    state::save_app_data(&state.paths, &data)?;
    Ok(data)
}

#[tauri::command]
pub fn update_evaluations(
    state: State<'_, AppState>,
    semester_id: String,
    subject_id: String,
    avaliacoes: Vec<Evaluation>,
) -> Result<AppData, String> {
    let mut data = state::load_app_data(&state.paths)?;
    let sem = data
        .semesters
        .get_mut(&semester_id)
        .ok_or_else(|| "Semestre não encontrado".to_string())?;
    let subj = sem
        .disciplinas
        .iter_mut()
        .find(|d| d.id == subject_id)
        .ok_or_else(|| "Disciplina não encontrada".to_string())?;
    subj.avaliacoes = avaliacoes;
    state::save_app_data(&state.paths, &data)?;
    Ok(data)
}

#[tauri::command]
pub fn log_study_session(
    state: State<'_, AppState>,
    payload: LogStudyPayload,
) -> Result<MetricsSummary, String> {
    let mut data = state::load_app_data(&state.paths)?;
    let now = Local::now().format("%Y-%m-%dT%H:%M:%S").to_string();

    for sem in data.semesters.values_mut() {
        if let Some(subj) = sem.disciplinas.iter_mut().find(|d| d.id == payload.subject_id) {
            subj.ultimo_estudo = Some(now.clone());
            if payload.reading_min > 0 || payload.pages > 0 {
                subj.ultima_leitura = Some(now.clone());
            }
        }
    }
    state::save_app_data(&state.paths, &data)?;

    let ev = EventRecord {
        ts: Some(now),
        timestamp: None,
        env: Some(state::hostname()),
        event_type: "study_session".to_string(),
        subject: Some(payload.subject_id),
        project: None,
        category: None,
        questions: Some(payload.questions),
        reading_min: Some(payload.reading_min),
        pages: Some(payload.pages),
        duration_min: Some(if payload.duration_min > 0 {
            payload.duration_min
        } else {
            payload.reading_min
        }),
        mode: Some(payload.mode),
        topic: Some(payload.topic),
        result: None,
        summary: None,
        question_id: None,
    };
    state::append_event(&state.paths, &ev)?;

    let events = state::load_events(&state.paths);
    Ok(metrics::compute_metrics(&data, &events))
}

#[tauri::command]
pub fn get_metrics(state: State<'_, AppState>) -> Result<MetricsSummary, String> {
    let data = state::load_app_data(&state.paths)?;
    let events = state::load_events(&state.paths);
    Ok(metrics::compute_metrics(&data, &events))
}

#[tauri::command]
pub fn get_questions(
    state: State<'_, AppState>,
    subject_id: String,
) -> Result<Vec<Question>, String> {
    state::load_questions(&state.paths, &subject_id)
}

#[tauri::command]
pub fn record_question_attempt(
    state: State<'_, AppState>,
    payload: QuestionAttemptPayload,
) -> Result<Vec<Question>, String> {
    let mut questions = state::load_questions(&state.paths, &payload.subject_id)?;
    let now = Local::now().format("%Y-%m-%dT%H:%M:%S").to_string();
    let mut topic = String::new();

    if let Some(q) = questions.iter_mut().find(|q| q.id == payload.question_id) {
        q.status = payload.result.clone();
        q.attempts += 1;
        q.last_attempt = Some(now.clone());
        topic = q.topico.clone();
    }
    state::save_questions(&state.paths, &payload.subject_id, &questions)?;

    // Touch subject ultimo_estudo
    if let Ok(mut data) = state::load_app_data(&state.paths) {
        for sem in data.semesters.values_mut() {
            if let Some(subj) = sem.disciplinas.iter_mut().find(|d| d.id == payload.subject_id) {
                subj.ultimo_estudo = Some(now.clone());
            }
        }
        let _ = state::save_app_data(&state.paths, &data);
    }

    let _ = state::append_event(
        &state.paths,
        &EventRecord {
            ts: Some(now),
            timestamp: None,
            env: Some(state::hostname()),
            event_type: "question_attempt".to_string(),
            subject: Some(payload.subject_id),
            project: None,
            category: None,
            questions: Some(1),
            reading_min: None,
            pages: None,
            duration_min: None,
            mode: Some("exercicios".to_string()),
            topic: Some(topic),
            result: Some(payload.result),
            summary: None,
            question_id: Some(payload.question_id),
        },
    );

    Ok(questions)
}

#[tauri::command]
pub fn import_questions_json(
    state: State<'_, AppState>,
    subject_id: String,
    raw_json: String,
) -> Result<Vec<Question>, String> {
    let incoming: Vec<Question> =
        serde_json::from_str(&raw_json).map_err(|e| format!("JSON inválido: {e}"))?;
    let mut existing = state::load_questions(&state.paths, &subject_id)?;

    for q in incoming {
        if let Some(slot) = existing.iter_mut().find(|e| e.id == q.id) {
            *slot = q;
        } else {
            existing.push(q);
        }
    }
    state::save_questions(&state.paths, &subject_id, &existing)?;
    Ok(existing)
}

#[tauri::command]
pub fn list_materials(
    state: State<'_, AppState>,
    materiais_dir: String,
) -> Result<Vec<StudyMaterial>, String> {
    Ok(scanner::scan_materials(&state.paths, &materiais_dir))
}

#[tauri::command]
pub fn get_projects(state: State<'_, AppState>) -> Result<Vec<ProjectItem>, String> {
    state::load_projects(&state.paths)
}

#[tauri::command]
pub fn save_projects_cmd(
    state: State<'_, AppState>,
    projects: Vec<ProjectItem>,
) -> Result<Vec<ProjectItem>, String> {
    state::save_projects(&state.paths, &projects)?;
    Ok(projects)
}

#[tauri::command]
pub fn log_project_session(
    state: State<'_, AppState>,
    payload: LogProjectPayload,
) -> Result<MetricsSummary, String> {
    let now = Local::now().format("%Y-%m-%dT%H:%M:%S").to_string();
    if let Some(next_act) = payload.next_action {
        if !next_act.trim().is_empty() {
            if let Ok(mut projs) = state::load_projects(&state.paths) {
                if let Some(p) = projs.iter_mut().find(|p| p.id == payload.project_id) {
                    p.next_action = next_act;
                }
                let _ = state::save_projects(&state.paths, &projs);
            }
        }
    }

    state::append_event(
        &state.paths,
        &EventRecord {
            ts: Some(now),
            timestamp: None,
            env: Some(state::hostname()),
            event_type: "project_session".to_string(),
            subject: None,
            project: Some(payload.project_id),
            category: Some(payload.category),
            questions: None,
            reading_min: None,
            pages: None,
            duration_min: Some(payload.duration_min),
            mode: Some("projeto".to_string()),
            topic: None,
            result: None,
            summary: Some(payload.summary),
            question_id: None,
        },
    )?;

    let data = state::load_app_data(&state.paths)?;
    let events = state::load_events(&state.paths);
    Ok(metrics::compute_metrics(&data, &events))
}

#[tauri::command]
pub fn scan_repos(state: State<'_, AppState>) -> Result<Vec<GitRepoInfo>, String> {
    let data = state::load_app_data(&state.paths)?;
    Ok(scanner::scan_git_repos(
        &data.agy_config.develop_dirs,
        &state.paths.repo_dir,
    ))
}

#[tauri::command]
pub fn scan_hardware(state: State<'_, AppState>) -> Result<HardwareSnapshot, String> {
    Ok(HardwareSnapshot {
        serial_devices: scanner::scan_serial_devices(),
        firmwares: scanner::scan_firmwares(&state.paths),
    })
}

#[tauri::command]
pub fn get_agy_status(state: State<'_, AppState>) -> Result<AgyStatus, String> {
    let data = state::load_app_data(&state.paths)?;
    Ok(agy::check_agy_status(&data.agy_config, &state.paths))
}

#[tauri::command]
pub fn launch_agy(
    state: State<'_, AppState>,
    working_dir: Option<String>,
    prompt: Option<String>,
) -> Result<String, String> {
    let data = state::load_app_data(&state.paths)?;
    let dir = match working_dir {
        Some(raw) if !raw.trim().is_empty() => scanner::expand_tilde(&raw),
        _ => PathBuf::from(&state.paths.repo_dir),
    };
    agy::launch_antigravity(&data.agy_config, &dir, prompt.as_deref())
}

#[tauri::command]
pub fn open_path(state: State<'_, AppState>, path: String) -> Result<(), String> {
    let target = if path.starts_with("http://") || path.starts_with("https://") || path.starts_with('/') {
        path
    } else if path.starts_with("~/") {
        scanner::expand_tilde(&path).to_string_lossy().to_string()
    } else {
        state.paths.repo_dir.join(&path).to_string_lossy().to_string()
    };
    agy::open_with_xdg(&target)
}

#[tauri::command]
pub fn git_sync_now(state: State<'_, AppState>) -> Result<String, String> {
    agy::trigger_git_sync(&state.paths)
}
