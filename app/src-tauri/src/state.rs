use crate::models::{AppData, EventRecord, ProjectItem, Question};
use chrono::Local;
use serde::Serialize;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone)]
pub struct RepoPaths {
    pub repo_dir: PathBuf,
    pub data_dir: PathBuf,
    pub data_file: PathBuf,
    pub events_file: PathBuf,
    pub projects_file: PathBuf,
    pub questoes_dir: PathBuf,
    pub estudos_dir: PathBuf,
    pub firmwares_dir: PathBuf,
    pub hud_cli_path: PathBuf,
}

impl RepoPaths {
    pub fn discover() -> Self {
        let repo_dir = resolve_repo_dir();
        let data_dir = repo_dir.join("data");
        Self {
            data_file: data_dir.join("data.json"),
            events_file: data_dir.join("events.jsonl"),
            projects_file: data_dir.join("projects.json"),
            questoes_dir: data_dir.join("questoes"),
            estudos_dir: repo_dir.join("estudos"),
            firmwares_dir: repo_dir.join("firmwares"),
            hud_cli_path: repo_dir.join("hud_cli.py"),
            data_dir,
            repo_dir,
        }
    }

    pub fn ensure_dirs(&self) -> Result<(), String> {
        fs::create_dir_all(&self.data_dir).map_err(|e| e.to_string())?;
        fs::create_dir_all(&self.questoes_dir).map_err(|e| e.to_string())?;
        fs::create_dir_all(&self.estudos_dir).map_err(|e| e.to_string())?;
        Ok(())
    }
}

fn resolve_repo_dir() -> PathBuf {
    if let Ok(env_dir) = std::env::var("VECTOR_REPO_DIR") {
        let p = PathBuf::from(env_dir);
        if p.join("data").exists() {
            return p;
        }
    }

    let mut candidates: Vec<PathBuf> = Vec::new();
    if let Ok(cwd) = std::env::current_dir() {
        candidates.push(cwd.clone());
        if let Some(p) = cwd.parent() {
            candidates.push(p.to_path_buf());
            if let Some(gp) = p.parent() {
                candidates.push(gp.to_path_buf());
            }
        }
    }
    if let Ok(exe) = std::env::current_exe() {
        let mut cur = exe.parent().map(|p| p.to_path_buf());
        for _ in 0..6 {
            if let Some(dir) = cur {
                candidates.push(dir.clone());
                cur = dir.parent().map(|p| p.to_path_buf());
            }
        }
    }

    for cand in candidates {
        if cand.join("data").join("data.json").exists() {
            return cand;
        }
    }

    std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."))
}

pub fn write_json_atomic<T: Serialize>(path: &Path, value: &T) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| format!("mkdir failed: {e}"))?;
    }
    let tmp = path.with_extension(format!(
        "tmp.{}",
        Local::now().timestamp_nanos_opt().unwrap_or(0)
    ));
    let body = serde_json::to_string_pretty(value).map_err(|e| format!("serialize failed: {e}"))?;
    fs::write(&tmp, body).map_err(|e| format!("write tmp failed: {e}"))?;
    fs::rename(&tmp, path).map_err(|e| {
        let _ = fs::remove_file(&tmp);
        format!("atomic rename failed: {e}")
    })
}

pub fn load_app_data(paths: &RepoPaths) -> Result<AppData, String> {
    if !paths.data_file.exists() {
        return Ok(AppData::default());
    }
    let raw = fs::read_to_string(&paths.data_file)
        .map_err(|e| format!("Erro lendo data.json: {e}"))?;
    serde_json::from_str::<AppData>(&raw)
        .map_err(|e| format!("Erro parseando data.json: {e}"))
}

pub fn save_app_data(paths: &RepoPaths, data: &AppData) -> Result<(), String> {
    paths.ensure_dirs()?;
    write_json_atomic(&paths.data_file, data)
}

pub fn load_projects(paths: &RepoPaths) -> Result<Vec<ProjectItem>, String> {
    if !paths.projects_file.exists() {
        return Ok(Vec::new());
    }
    let raw = fs::read_to_string(&paths.projects_file)
        .map_err(|e| format!("Erro lendo projects.json: {e}"))?;
    serde_json::from_str::<Vec<ProjectItem>>(&raw)
        .map_err(|e| format!("Erro parseando projects.json: {e}"))
}

pub fn save_projects(paths: &RepoPaths, items: &[ProjectItem]) -> Result<(), String> {
    paths.ensure_dirs()?;
    write_json_atomic(&paths.projects_file, &items)
}

pub fn load_questions(paths: &RepoPaths, subject_id: &str) -> Result<Vec<Question>, String> {
    let safe_id: String = subject_id
        .chars()
        .filter(|c| c.is_alphanumeric() || *c == '_' || *c == '-')
        .collect();
    let file = paths.questoes_dir.join(format!("{safe_id}.json"));
    if !file.exists() {
        return Ok(Vec::new());
    }
    let raw = fs::read_to_string(&file).map_err(|e| format!("Erro lendo questões: {e}"))?;
    serde_json::from_str::<Vec<Question>>(&raw)
        .map_err(|e| format!("Erro parseando questões: {e}"))
}

pub fn save_questions(
    paths: &RepoPaths,
    subject_id: &str,
    questions: &[Question],
) -> Result<(), String> {
    paths.ensure_dirs()?;
    let safe_id: String = subject_id
        .chars()
        .filter(|c| c.is_alphanumeric() || *c == '_' || *c == '-')
        .collect();
    let file = paths.questoes_dir.join(format!("{safe_id}.json"));
    write_json_atomic(&file, &questions)
}

pub fn load_events(paths: &RepoPaths) -> Vec<EventRecord> {
    let Ok(raw) = fs::read_to_string(&paths.events_file) else {
        return Vec::new();
    };
    raw.lines()
        .filter_map(|line| {
            let trimmed = line.trim();
            if trimmed.is_empty() {
                return None;
            }
            serde_json::from_str::<EventRecord>(trimmed).ok()
        })
        .collect()
}

pub fn append_event(paths: &RepoPaths, event: &EventRecord) -> Result<(), String> {
    paths.ensure_dirs()?;
    let mut file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(&paths.events_file)
        .map_err(|e| format!("Erro abrindo events.jsonl: {e}"))?;
    let line = serde_json::to_string(event).map_err(|e| format!("Erro serializando evento: {e}"))?;
    writeln!(file, "{line}").map_err(|e| format!("Erro gravando events.jsonl: {e}"))
}

pub fn hostname() -> String {
    fs::read_to_string("/etc/hostname")
        .ok()
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .unwrap_or_else(|| "linux-host".to_string())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::{ProjectItem, Question};

    fn temp_repo(name: &str) -> RepoPaths {
        let root = std::env::temp_dir().join(format!(
            "vector_prod_test_{}_{}",
            name,
            Local::now().timestamp_nanos_opt().unwrap_or(0)
        ));
        let data_dir = root.join("data");
        let paths = RepoPaths {
            data_file: data_dir.join("data.json"),
            events_file: data_dir.join("events.jsonl"),
            projects_file: data_dir.join("projects.json"),
            questoes_dir: data_dir.join("questoes"),
            estudos_dir: root.join("estudos"),
            firmwares_dir: root.join("firmwares"),
            hud_cli_path: root.join("hud_cli.py"),
            data_dir,
            repo_dir: root,
        };
        paths.ensure_dirs().unwrap();
        paths
    }

    #[test]
    fn roundtrip_app_data_projects_questions_and_events() {
        let paths = temp_repo("roundtrip");

        let mut app = AppData::default();
        app.active_semester = "2027.1".to_string();
        app.daily_goals.leitura_min = 60;
        save_app_data(&paths, &app).unwrap();
        let loaded = load_app_data(&paths).unwrap();
        assert_eq!(loaded.daily_goals.leitura_min, 60);

        let projs = vec![ProjectItem {
            id: "rl-robot".to_string(),
            nome: "RL Robot".to_string(),
            categoria: "robotics".to_string(),
            status: "ativo".to_string(),
            prioridade: "alta".to_string(),
            stack: vec!["Rust".to_string()],
            repo_name: "rl-robot".to_string(),
            descricao: "Test".to_string(),
            next_action: "Train".to_string(),
            pinned: true,
        }];
        save_projects(&paths, &projs).unwrap();
        assert_eq!(load_projects(&paths).unwrap().len(), 1);

        let qs = vec![Question {
            id: "q1".to_string(),
            topico: "Gauss".to_string(),
            dificuldade: "media".to_string(),
            enunciado: "$E = F/q$".to_string(),
            dica: "dica".to_string(),
            gabarito: "resp".to_string(),
            status: "pendente".to_string(),
            attempts: 0,
            last_attempt: None,
        }];
        // Path traversal characters should be sanitized cleanly
        save_questions(&paths, "../fisica3", &qs).unwrap();
        let loaded_qs = load_questions(&paths, "fisica3").unwrap();
        assert_eq!(loaded_qs.len(), 1);
        assert_eq!(loaded_qs[0].id, "q1");

        let ev = EventRecord {
            ts: Some("2026-11-26T12:00:00".to_string()),
            timestamp: None,
            env: Some("test".to_string()),
            event_type: "study_session".to_string(),
            subject: Some("fisica3".to_string()),
            project: None,
            category: None,
            questions: Some(3),
            reading_min: Some(40),
            pages: Some(10),
            duration_min: Some(40),
            mode: Some("leitura".to_string()),
            topic: Some("Gauss".to_string()),
            result: None,
            summary: None,
            question_id: None,
        };
        append_event(&paths, &ev).unwrap();
        let events = load_events(&paths);
        assert_eq!(events.len(), 1);
        assert_eq!(events[0].reading_min, Some(40));

        let _ = fs::remove_dir_all(&paths.repo_dir);
    }

    #[test]
    fn loads_real_repository_data_json() {
        let paths = RepoPaths::discover();
        let data = load_app_data(&paths).expect("real data/data.json must deserialize cleanly");
        assert!(data.semesters.contains_key("2027.1"));
        assert_eq!(data.semesters["2027.1"].disciplinas.len(), 7);
    }
}

