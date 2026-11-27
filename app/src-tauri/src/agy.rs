use crate::models::{AgyConfig, AgyStatus};
use crate::state::RepoPaths;
use std::path::Path;
use std::process::Command;

pub fn which_cmd(cmd: &str) -> Option<String> {
    let first = cmd.split_whitespace().next()?;
    Command::new("which")
        .arg(first)
        .output()
        .ok()
        .filter(|o| o.status.success())
        .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
        .filter(|s| !s.is_empty())
}

pub fn check_agy_status(config: &AgyConfig, paths: &RepoPaths) -> AgyStatus {
    let resolved = which_cmd(&config.cli_command)
        .or_else(|| which_cmd("antigravity"))
        .or_else(|| which_cmd("agy"));
    AgyStatus {
        cli_command: config.cli_command.clone(),
        cli_available: resolved.is_some(),
        resolved_path: resolved,
        repo_dir: paths.repo_dir.to_string_lossy().to_string(),
        hud_cli_path: paths.hud_cli_path.to_string_lossy().to_string(),
    }
}

pub fn launch_antigravity(
    config: &AgyConfig,
    working_dir: &Path,
    prompt: Option<&str>,
) -> Result<String, String> {
    let cli = which_cmd(&config.cli_command)
        .or_else(|| which_cmd("antigravity"))
        .or_else(|| which_cmd("agy"));

    if let Some(bin) = cli {
        let mut cmd = Command::new(&bin);
        cmd.current_dir(working_dir);
        cmd.arg(working_dir);
        if let Some(p) = prompt {
            if !p.trim().is_empty() {
                cmd.arg("--prompt").arg(p);
            }
        }
        cmd.spawn()
            .map_err(|e| format!("Falha ao iniciar {bin}: {e}"))?;
        return Ok(format!("Antigravity iniciado ({bin}) em {}", working_dir.display()));
    }

    // Fallback: open terminal in the working directory
    let terminals = [
        config.terminal_command.as_str(),
        "x-terminal-emulator",
        "gnome-terminal",
        "kitty",
        "alacritty",
        "konsole",
        "xfce4-terminal",
    ];
    for term in terminals {
        if which_cmd(term).is_some() {
            let mut cmd = Command::new(term);
            cmd.current_dir(working_dir);
            if cmd.spawn().is_ok() {
                return Ok(format!(
                    "CLI '{}' não encontrada no PATH; terminal aberto em {} (prompt copiado).",
                    config.cli_command,
                    working_dir.display()
                ));
            }
        }
    }

    Err(format!(
        "CLI '{}' não encontrada no PATH. Prompt pronto foi copiado para a área de transferência.",
        config.cli_command
    ))
}

pub fn open_with_xdg(target: &str) -> Result<(), String> {
    Command::new("xdg-open")
        .arg(target)
        .spawn()
        .map_err(|e| format!("Erro abrindo '{target}': {e}"))?;
    Ok(())
}

pub fn trigger_git_sync(paths: &RepoPaths) -> Result<String, String> {
    let output = Command::new("python3")
        .arg(&paths.hud_cli_path)
        .arg("sync")
        .current_dir(&paths.repo_dir)
        .output()
        .map_err(|e| format!("Erro executando hud_cli.py sync: {e}"))?;

    let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
    if output.status.success() {
        Ok(if stdout.is_empty() {
            "Sincronizado com sucesso.".to_string()
        } else {
            stdout
        })
    } else {
        Err(if stderr.is_empty() { stdout } else { stderr })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn resolves_known_linux_commands_and_checks_agy_status() {
        assert!(which_cmd("git").is_some());
        assert!(which_cmd("definitely_nonexistent_binary_xyz_123").is_none());

        let paths = RepoPaths::discover();
        let cfg = AgyConfig::default();
        let status = check_agy_status(&cfg, &paths);
        assert_eq!(status.cli_command, "antigravity");
        assert!(status.hud_cli_path.ends_with("hud_cli.py"));
    }
}

