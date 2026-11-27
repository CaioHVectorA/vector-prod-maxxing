use crate::state::RepoPaths;
use notify::{Event, RecommendedWatcher, RecursiveMode, Watcher};
use std::sync::mpsc;
use std::thread;
use std::time::{Duration, Instant};
use tauri::{AppHandle, Emitter};

pub fn start_workspace_watcher(app: AppHandle, paths: RepoPaths) {
    thread::spawn(move || {
        let (tx, rx) = mpsc::channel::<notify::Result<Event>>();
        let Ok(mut watcher) = RecommendedWatcher::new(
            move |res| {
                let _ = tx.send(res);
            },
            notify::Config::default(),
        ) else {
            return;
        };

        let _ = watcher.watch(&paths.data_dir, RecursiveMode::Recursive);
        if paths.estudos_dir.exists() {
            let _ = watcher.watch(&paths.estudos_dir, RecursiveMode::Recursive);
        }

        let mut last_emit = Instant::now() - Duration::from_secs(1);
        for res in rx {
            if let Ok(event) = res {
                // Ignore temp atomic files
                let is_tmp = event
                    .paths
                    .iter()
                    .any(|p| p.to_string_lossy().contains(".tmp"));
                if is_tmp {
                    continue;
                }
                if last_emit.elapsed() >= Duration::from_millis(250) {
                    let _ = app.emit("workspace-changed", "data");
                    last_emit = Instant::now();
                }
            }
        }
    });
}
