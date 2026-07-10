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

def find_recordings(experiment_path: Path, experiment_name: str, recording_or_session_names: list[str] | None = None) -> list[str]:
    """Find names of existing recordings that match the given recording or session names."""
    all_recording_names = [
        path.name for path in (experiment_path / "recordings").glob("*")
        if path.name.startswith(experiment_name + ".")
    ]
    if recording_or_session_names is None:
        return all_recording_names

    matching_recording_names = []
    for name in recording_or_session_names:
        if name in all_recording_names:
            matching_recording_names.append(name)
        else:
            # Check if it is a session name
            found = False
            for other_recording_name in all_recording_names:
                other_session_name = get_session_name(
                    other_recording_name, experiment_name
                )
                if name == other_session_name:
                    matching_recording_names.append(
                        other_recording_name
                    )
                    found = True
            if not found:
                raise ValueError(
                    f"Recording or session '{name}' not found in {experiment_path / 'recordings'}"
                )
    return matching_recording_names
