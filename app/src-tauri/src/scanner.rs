use crate::models::{FirmwareItem, GitRepoInfo, SerialDevice, StudyMaterial};
use crate::state::RepoPaths;
use chrono::{DateTime, Local};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use walkdir::WalkDir;

pub fn expand_tilde(raw: &str) -> PathBuf {
    if let Some(rest) = raw.strip_prefix("~/") {
        if let Some(home) = dirs::home_dir() {
            return home.join(rest);
        }
    }
    PathBuf::from(raw)
}

pub fn scan_materials(paths: &RepoPaths, rel_dir: &str) -> Vec<StudyMaterial> {
    let target = if Path::new(rel_dir).is_absolute() {
        PathBuf::from(rel_dir)
    } else {
        paths.repo_dir.join(rel_dir)
    };
    if !target.exists() {
        return Vec::new();
    }

    let mut out = Vec::new();
    for entry in WalkDir::new(&target).max_depth(4).into_iter().flatten() {
        if !entry.file_type().is_file() {
            continue;
        }
        let name = entry.file_name().to_string_lossy().to_string();
        if name.starts_with('.') {
            continue;
        }
        let path = entry.path();
        let ext = path
            .extension()
            .map(|e| e.to_string_lossy().to_lowercase())
            .unwrap_or_default();
        let meta = fs::metadata(path).ok();
        let size_bytes = meta.as_ref().map(|m| m.len()).unwrap_or(0);
        let modified_at = meta
            .and_then(|m| m.modified().ok())
            .map(|st| {
                let dt: DateTime<Local> = st.into();
                dt.format("%Y-%m-%d %H:%M").to_string()
            })
            .unwrap_or_default();
        let rel_path = path
            .strip_prefix(&paths.repo_dir)
            .unwrap_or(path)
            .to_string_lossy()
            .to_string();

        out.push(StudyMaterial {
            name,
            rel_path,
            abs_path: path.to_string_lossy().to_string(),
            ext,
            size_bytes,
            modified_at,
        });
    }
    out.sort_by(|a, b| a.name.to_lowercase().cmp(&b.name.to_lowercase()));
    out
}

pub fn scan_serial_devices() -> Vec<SerialDevice> {
    let mut devices = Vec::new();
    let Ok(entries) = fs::read_dir("/dev") else {
        return devices;
    };
    for entry in entries.flatten() {
        let name = entry.file_name().to_string_lossy().to_string();
        if name.starts_with("ttyUSB") || name.starts_with("ttyACM") {
            let port = format!("/dev/{name}");
            let board_hint = if name.starts_with("ttyUSB") {
                "ESP32 / CP210x / CH340 (USB-Serial)".to_string()
            } else {
                "Arduino / ESP32-S3 / STM32 (CDC ACM)".to_string()
            };
            devices.push(SerialDevice {
                port,
                label: name,
                board_hint,
            });
        }
    }
    devices.sort_by(|a, b| a.port.cmp(&b.port));
    devices
}

pub fn scan_firmwares(paths: &RepoPaths) -> Vec<FirmwareItem> {
    let mut out = Vec::new();
    if !paths.firmwares_dir.exists() {
        return out;
    }
    let Ok(boards) = fs::read_dir(&paths.firmwares_dir) else {
        return out;
    };
    for board_entry in boards.flatten() {
        if !board_entry.path().is_dir() {
            continue;
        }
        let board = board_entry.file_name().to_string_lossy().to_string();
        let Ok(sketches) = fs::read_dir(board_entry.path()) else {
            continue;
        };
        for sketch in sketches.flatten() {
            if !sketch.path().is_dir() {
                continue;
            }
            let name = sketch.file_name().to_string_lossy().to_string();
            let files: Vec<String> = fs::read_dir(sketch.path())
                .ok()
                .map(|rd| {
                    rd.flatten()
                        .filter(|e| e.path().is_file())
                        .map(|e| e.file_name().to_string_lossy().to_string())
                        .collect()
                })
                .unwrap_or_default();
            out.push(FirmwareItem {
                board: board.clone(),
                name,
                path: sketch.path().to_string_lossy().to_string(),
                files,
            });
        }
    }
    out.sort_by(|a, b| (&a.board, &a.name).cmp(&(&b.board, &b.name)));
    out
}

fn inspect_git_repo(dir: &Path) -> Option<GitRepoInfo> {
    if !dir.join(".git").exists() {
        return None;
    }
    let name = dir.file_name()?.to_string_lossy().to_string();
    let branch = Command::new("git")
        .args(["rev-parse", "--abbrev-ref", "HEAD"])
        .current_dir(dir)
        .output()
        .ok()
        .filter(|o| o.status.success())
        .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
        .unwrap_or_else(|| "main".to_string());

    let dirty_files = Command::new("git")
        .args(["status", "--porcelain"])
        .current_dir(dir)
        .output()
        .ok()
        .filter(|o| o.status.success())
        .map(|o| {
            String::from_utf8_lossy(&o.stdout)
                .lines()
                .filter(|l| !l.trim().is_empty())
                .count()
        })
        .unwrap_or(0);

    let log_out = Command::new("git")
        .args(["log", "-1", "--pretty=format:%s|||%cr"])
        .current_dir(dir)
        .output()
        .ok()
        .filter(|o| o.status.success())
        .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
        .unwrap_or_default();

    let (last_commit_msg, last_commit_rel) = log_out
        .split_once("|||")
        .map(|(m, r)| (m.to_string(), r.to_string()))
        .unwrap_or_else(|| ("Sem commits".to_string(), "—".to_string()));

    Some(GitRepoInfo {
        name,
        path: dir.to_string_lossy().to_string(),
        branch,
        dirty_files,
        last_commit_msg,
        last_commit_rel,
    })
}

pub fn scan_git_repos(develop_dirs: &[String], repo_dir: &Path) -> Vec<GitRepoInfo> {
    let mut repos = Vec::new();
    let mut seen = std::collections::HashSet::new();

    if let Some(info) = inspect_git_repo(repo_dir) {
        seen.insert(info.path.clone());
        repos.push(info);
    }

    for raw in develop_dirs {
        let base = expand_tilde(raw);
        let Ok(entries) = fs::read_dir(&base) else {
            continue;
        };
        for entry in entries.flatten() {
            let p = entry.path();
            if !p.is_dir() {
                continue;
            }
            let key = p.to_string_lossy().to_string();
            if seen.contains(&key) {
                continue;
            }
            if let Some(info) = inspect_git_repo(&p) {
                seen.insert(key);
                repos.push(info);
            }
        }
    }

    repos.sort_by(|a, b| a.name.to_lowercase().cmp(&b.name.to_lowercase()));
    repos
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::state::RepoPaths;

    #[test]
    fn scans_real_repo_firmwares_and_materials() {
        let paths = RepoPaths::discover();
        let fws = scan_firmwares(&paths);
        assert!(!fws.is_empty(), "should detect ESP32/Arduino firmwares");
        assert!(fws.iter().any(|f| f.board == "esp32"));

        let mats = scan_materials(&paths, "estudos/calculo-3");
        assert!(!mats.is_empty(), "should detect Calculo 3 PDFs");
        assert!(mats.iter().all(|m| !m.name.starts_with('.')));
    }

    #[test]
    fn scans_repo_git_info() {
        let paths = RepoPaths::discover();
        let repos = scan_git_repos(&[], &paths.repo_dir);
        assert_eq!(repos.len(), 1);
        assert_eq!(repos[0].name, "vector-prod-maxxing");
        assert!(!repos[0].branch.is_empty());
    }
}

