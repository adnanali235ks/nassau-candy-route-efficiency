"""Startup environment check: a wrong Python / missing package produces one clear, actionable message."""
import pathlib
import re
import sys

from streamlit.testing.v1 import AppTest

from ui import environment as env

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_all_required_packages_are_present_in_this_interpreter():
    assert env.missing_packages() == []


def test_missing_packages_reports_only_what_is_missing():
    required = {"sys": "sys", "definitely_not_installed_pkg_xyz": "xyz-pip-name"}
    assert env.missing_packages(required) == ["definitely_not_installed_pkg_xyz"]


def test_message_names_the_interpreter_the_missing_package_and_the_fix(tmp_path):
    text = env.problem_message(["ortools"], executable="C:/some/other/python.exe", project_dir=tmp_path)
    assert "ortools" in text and "C:/some/other/python.exe" in text
    assert "pip install -r requirements.txt" in text and "-m streamlit run app.py" in text
    assert str(tmp_path) in text and ".venv" in text


def test_required_packages_are_all_listed_in_requirements_txt():
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    for pip_name in env.REQUIRED_PACKAGES.values():
        assert re.search(rf"^{re.escape(pip_name)}\b", requirements, re.M), f"{pip_name} missing from requirements.txt"


def test_ortools_is_pinned_with_a_lower_bound():
    assert re.search(r"^ortools>=\d", (ROOT / "requirements.txt").read_text(encoding="utf-8"), re.M)


def test_environment_module_works_even_when_packages_are_missing():
    # It must import nothing heavy, so it can still explain the problem when the app's packages are absent.
    source = (ROOT / "ui" / "environment.py").read_text(encoding="utf-8")
    imports = set(re.findall(r"^(?:import|from) (\w+)", source, re.M))
    assert imports <= {"importlib", "pathlib", "sys"}


def test_dashboard_shows_the_message_instead_of_a_traceback_when_a_package_is_missing(monkeypatch):
    monkeypatch.setattr(env, "REQUIRED_PACKAGES", {**env.REQUIRED_PACKAGES, "definitely_not_installed_pkg_xyz": "xyz"})
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120).run()
    assert not at.exception
    assert any("Missing Python packages" in e.value for e in at.error)
    body = " ".join(m.value for m in at.markdown)
    assert "definitely_not_installed_pkg_xyz" in body and sys.executable.replace("\\", "/") in body.replace("\\", "/")
    assert "-m streamlit run app.py" in body
    assert not any(t.value == "Executive Overview" for t in at.title)      # the dashboard itself did not start


def test_normal_start_is_unaffected():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120).run()
    assert not at.exception, [e.value for e in at.exception]
    assert not any("Missing Python packages" in e.value for e in at.error)
