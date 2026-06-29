import importlib.util
import importlib.metadata
from pathlib import Path


def import_custom_code(experiment_path: Path):
    """Import all .py files in the given directory and its subdirectories."""
    for filename in (experiment_path / "code").rglob("*.py"):
        spec = importlib.util.spec_from_file_location("custom_code", filename)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)


def get_package_version() -> str:
    """Get the installed version of the eidon package."""
    return importlib.metadata.version("eidon")


def ask_user_yes_no(question: str) -> bool:
    """Ask the user a yes/no question and return True for yes and False for no."""
    while True:
        answer = input(f"{question} (y/n): ").strip().lower()
        if answer in ["y", "yes"]:
            return True
        elif answer in ["n", "no"]:
            return False
        else:
            print("Please enter 'y' or 'n'.")

def get_session_name(recording_name: str, experiment_name: str) -> str:
    """Extract the session name from a recording name."""
    session_name = recording_name.removeprefix(experiment_name + ".")
    session_name = "".join(session_name.split(".")[:-1])
    return session_name
