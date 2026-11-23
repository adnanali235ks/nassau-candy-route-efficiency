"""Launch workflow: the project must always start with, and install into, its OWN virtual environment."""
import json
import pathlib
import shutil
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
windows_only = pytest.mark.skipif(sys.platform != "win32", reason="the .bat launchers are for Windows")

TEXT_SUFFIXES = {".py", ".md", ".txt", ".toml", ".yml", ".yaml", ".bat", ".json", ".ini", ".cfg"}


def read(name):
    return (ROOT / name).read_text(encoding="utf-8")


def test_run_script_uses_the_project_venv_and_python_dash_m_streamlit():
    text = read("run_app.bat")
    assert r".venv\Scripts\python.exe" in text and "-m streamlit run app.py" in text
    assert "%*" in text                                           # extra Streamlit arguments are passed through
    for line in text.splitlines():                                # never a bare `streamlit run`
        if "streamlit run" in line and not line.lstrip().startswith(("rem", "echo")):
            assert "-m streamlit run" in line, line


def test_run_script_checks_the_environment_before_starting():
    text = read("run_app.bat")
    assert "if not exist" in text and "import streamlit, pandas, numpy, plotly, ortools, openpyxl, reportlab" in text
    assert "setup_env.bat" in text


def test_setup_script_installs_only_into_the_project_venv():
    text = read("setup_env.bat")
    assert r'".venv\Scripts\python.exe" -m pip install -r requirements.txt' in text
    for line in text.splitlines():                                # no bare `pip install`
        if "pip install" in line and not line.lstrip().startswith(("rem", "echo")):
            assert ".venv" in line, line


def test_vscode_settings_point_at_the_project_venv():
    settings = json.loads(read(".vscode/settings.json"))
    assert settings["python.defaultInterpreterPath"].replace("\\\\", "\\").endswith(r".venv\Scripts\python.exe")
    assert settings["python.terminal.activateEnvironment"] is True


def test_no_project_file_refers_to_a_temporary_or_scratch_interpreter():
    offenders = []
    for path in ROOT.rglob("*"):
        parts = set(path.parts)
        if (not path.is_file() or ".venv" in parts or "__pycache__" in parts or ".git" in parts
                or path.suffix.lower() not in TEXT_SUFFIXES or path.name == "test_launch.py"
                or "screenshots" in parts):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        if "scratchpad" in text or "temp\\claude" in text or "temp/claude" in text:
            offenders.append(path.relative_to(ROOT).as_posix())
    assert offenders == [], f"files that reference a temporary interpreter folder: {offenders}"


@windows_only
def test_run_script_starts_streamlit_from_the_project_venv():
    # `streamlit run --help` exercises the exact launch line (interpreter check, package check, -m streamlit) without
    # starting a server.
    out = subprocess.run(["cmd", "/c", str(ROOT / "run_app.bat"), "--help"], capture_output=True, text=True,
                         timeout=180, cwd=ROOT)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "Starting the dashboard with:" in out.stdout and r".venv\Scripts\python.exe" in out.stdout
    assert "Usage: python -m streamlit run" in out.stdout or "streamlit run" in out.stdout


@windows_only
def test_run_script_refuses_to_start_without_a_project_environment(tmp_path):
    shutil.copy(ROOT / "run_app.bat", tmp_path / "run_app.bat")      # a folder with no .venv
    out = subprocess.run(["cmd", "/c", str(tmp_path / "run_app.bat")], capture_output=True, text=True, timeout=60,
                         cwd=tmp_path)
    assert out.returncode == 1
    assert "virtual environment was not found" in out.stdout and "setup_env.bat" in out.stdout
