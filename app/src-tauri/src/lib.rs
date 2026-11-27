mod agy;
mod commands;
mod metrics;
mod models;
mod scanner;
mod state;
mod watcher;

use commands::AppState;
use state::RepoPaths;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let paths = RepoPaths::discover();
    let _ = paths.ensure_dirs();
    let watcher_paths = paths.clone();

    tauri::Builder::default()
        .manage(AppState { paths })
        .setup(move |app| {
            watcher::start_workspace_watcher(app.handle().clone(), watcher_paths.clone());
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::get_app_data,
            commands::save_app_data_cmd,
            commands::set_active_semester,
            commands::create_semester,
            commands::upsert_subject,
            commands::delete_subject,
            commands::update_topic_state,
            commands::add_topic,
            commands::update_evaluations,
            commands::log_study_session,
            commands::get_metrics,
            commands::get_questions,
            commands::record_question_attempt,
            commands::import_questions_json,
            commands::list_materials,
            commands::get_projects,
            commands::save_projects_cmd,
            commands::log_project_session,
            commands::scan_repos,
            commands::scan_hardware,
            commands::get_agy_status,
            commands::launch_agy,
            commands::open_path,
            commands::git_sync_now,
        ])
        .run(tauri::generate_context!())
        .expect("error while running Vector Prod Maxxing Tauri application");
}
