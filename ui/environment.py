"""
Startup check: are the required packages installed in the Python that is running the app?

The classic failure is starting Streamlit from a different Python than the one the project was installed into
(for example a global Python or an old virtual environment), which shows up as an obscure
"No module named 'ortools'" deep inside a page. This module turns that into one clear message that names the
interpreter in use and the exact commands that fix it. It imports nothing heavy, so it works even when the
packages are missing.
"""

import importlib.util
import pathlib
import sys

# import name -> pip name (all of these are listed in requirements.txt)
REQUIRED_PACKAGES = {
    "streamlit": "streamlit", "pandas": "pandas", "numpy": "numpy", "plotly": "plotly",
    "ortools": "ortools", "openpyxl": "openpyxl", "reportlab": "reportlab",
}

PROJECT_DIR = pathlib.Path(__file__).resolve().parents[1]


def missing_packages(required=None):
    """Import names from `required` (default REQUIRED_PACKAGES) that this interpreter cannot find."""
    required = REQUIRED_PACKAGES if required is None else required
    return [name for name in required if importlib.util.find_spec(name) is None]


def problem_message(missing, executable=None, project_dir=None):
    """Plain-language explanation of a missing-package problem, with the commands that fix it."""
    executable = executable or sys.executable
    project_dir = pathlib.Path(project_dir or PROJECT_DIR)
    venv_python = project_dir / ".venv" / "Scripts" / "python.exe"       # Windows layout (macOS/Linux: .venv/bin/python)
    pip_names = ", ".join(REQUIRED_PACKAGES.get(name, name) for name in missing)
    return (
        f"These required packages are not installed in the Python that is running this app: {', '.join(missing)}\n\n"
        f"Python in use : {executable}\n"
        f"Project folder: {project_dir}\n\n"
        "This usually means Streamlit was started from a different Python (a global install or an old virtual "
        "environment) than the one the project was installed into.\n\n"
        "Fix (Windows, from the project folder):\n"
        f"  {venv_python} -m pip install -r requirements.txt\n"
        f"  {venv_python} -m streamlit run app.py\n"
        "On macOS/Linux use .venv/bin/python instead. Then stop the old server and reload the page.\n"
        f"(Missing: {pip_names})"
    )
