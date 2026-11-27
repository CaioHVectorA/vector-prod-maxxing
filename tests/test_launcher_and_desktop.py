"""Unit tests for launch.sh, install-desktop.sh, and uninstall-desktop.sh."""

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_launch_fingerprint_is_deterministic_and_check_passes():
    fp1 = subprocess.check_output(
        [str(REPO_ROOT / "launch.sh"), "--fingerprint"],
        text=True,
    ).strip()
    fp2 = subprocess.check_output(
        [str(REPO_ROOT / "launch.sh"), "--fingerprint"],
        text=True,
    ).strip()
    assert len(fp1) == 64
    assert fp1 == fp2

    res = subprocess.run(
        [str(REPO_ROOT / "launch.sh"), "--check"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "[OK] cargo" in res.stdout
    assert "[OK] node" in res.stdout
    assert "[OK] webkit2gtk-4.1" in res.stdout


def test_install_and_uninstall_desktop_entries_isolated(tmp_path):
    fake_home = tmp_path / "home"
    fake_data = fake_home / ".local" / "share"
    fake_desktop = fake_home / "Desktop"
    fake_desktop.mkdir(parents=True)

    env = os.environ.copy()
    env["HOME"] = str(fake_home)
    env["XDG_DATA_HOME"] = str(fake_data)
    env["XDG_CONFIG_HOME"] = str(fake_home / ".config")
    # Ensure xdg-user-dir resolves to fake_desktop
    (fake_home / ".config").mkdir(parents=True, exist_ok=True)
    (fake_home / ".config" / "user-dirs.dirs").write_text(
        'XDG_DESKTOP_DIR="$HOME/Desktop"\n', encoding="utf-8"
    )

    install = subprocess.run(
        [str(REPO_ROOT / "install-desktop.sh"), "--no-pin"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert install.returncode == 0, install.stderr

    app_entry = fake_data / "applications" / "vector-prod-maxxing.desktop"
    desk_entry = fake_desktop / "vector-prod-maxxing.desktop"
    icon_file = fake_data / "icons" / "hicolor" / "128x128" / "apps" / "vector-prod-maxxing.png"

    assert app_entry.exists()
    assert desk_entry.exists()
    assert icon_file.exists()
    assert os.access(app_entry, os.X_OK)
    assert os.access(desk_entry, os.X_OK)

    content = app_entry.read_text(encoding="utf-8")
    assert f"Exec={REPO_ROOT}/launch.sh" in content
    assert "StartupWMClass=vector-prod-maxxing" in content
    assert "[Desktop Action Release]" in content
    assert "[Desktop Action Test]" in content

    # Verify uninstall removes everything cleanly
    uninstall = subprocess.run(
        [str(REPO_ROOT / "uninstall-desktop.sh")],
        env=env,
        capture_output=True,
        text=True,
    )
    assert uninstall.returncode == 0, uninstall.stderr
    assert not app_entry.exists()
    assert not desk_entry.exists()
    assert not icon_file.exists()
