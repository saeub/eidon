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
