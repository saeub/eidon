import csv
import json
from pathlib import Path
from typing import Any
import warnings
from PIL import Image


def load_txt(path: Path) -> str:
    with open(path) as f:
        return f.read().rstrip("\r\n")


def load_json(path: Path) -> Any:
    with open(path) as f:
        return json.load(f)


def load_csv(path: Path) -> list[dict[str, Any]]:
    with open(path) as f:
        reader = csv.DictReader(f)
        subcolumn_paths = {
            column: _get_subcolumn_path(column) for column in reader.fieldnames
        }
        subcolumn_rows = []
        for row in reader:
            subcolumn_row = {}
            # Fill in subcolumn values
            for column, value in row.items():
                subcolumn_path = subcolumn_paths[column]
                _set_subcolumn_value(subcolumn_row, subcolumn_path, value)
            # Strip None values from the end of lists
            _strip_none_from_end(subcolumn_row)
            subcolumn_rows.append(subcolumn_row)
        return subcolumn_rows


def _get_subcolumn_path(column: str) -> list[str | int]:
    return [
        int(component) if component.isdigit() else component
        for component in column.split(".")
    ]


def _set_subcolumn_value(
    subcolumn_row: dict[str, Any], path: list[str | int], value: Any
):
    parent_container: dict[str | int, Any] | list[Any] | None = None
    parent_key: str | int | None = None
    container: dict[str | int, Any] | list[Any] = subcolumn_row

    for i, component in enumerate(path):
        # Extend container if necessary
        if isinstance(component, int):
            # Integer key -> list container required
            if parent_container is None:
                raise ValueError(
                    f"Invalid column name {'.'.join(map(str, path))!r}: "
                    "first component cannot be a number"
                )
            if container is None:
                container = []
                parent_container[parent_key] = container
            if not isinstance(container, list):
                raise ValueError(
                    f"Invalid column name {'.'.join(map(str, path))!r}: "
                    f"expected a string key after {'.'.join(map(str, path[:i]))!r}, "
                    f"but got {component!r}"
                )
            if component >= len(container):
                container.extend(None for _ in range(component - len(container) + 1))
        else:
            # String key -> dictionary container required
            if container is None:
                container = {}
                parent_container[parent_key] = container
            if not isinstance(container, dict):
                raise ValueError(
                    f"Invalid column name {'.'.join(map(str, path))!r}: "
                    f"expected an integer key after {'.'.join(map(str, path[:i]))!r}, "
                    f"but got {component!r}"
                )
            if component not in container:
                container[component] = None

        # Index into container unless we've reached the last component
        if i < len(path) - 1:
            parent_container = container
            parent_key = component
            container = container[component]

    # Set value at last path component
    container[path[-1]] = value


def _strip_none_from_end(container):
    if isinstance(container, list):
        while container and container[-1] is None:
            container.pop()
        for item in container:
            _strip_none_from_end(item)
    elif isinstance(container, dict):
        for item in container.values():
            _strip_none_from_end(item)


def load_png(path: Path) -> Image.Image:
    return Image.open(path)


def load_jpeg(path: Path) -> Image.Image:
    warnings.warn(
        f"JPEG images ({path}) are not recommended for stimuli, as they use lossy compression. "
        "Consider using PNG images instead.",
        UserWarning,
    )
    return Image.open(path)


LOAD_FUNCTIONS = {
    ".txt": load_txt,
    ".json": load_json,
    ".csv": load_csv,
    ".png": load_png,
    ".jpg": load_jpeg,
    ".jpeg": load_jpeg,
}


def load_materials_file(path: Path) -> Any:
    extension = path.suffix
    if extension in LOAD_FUNCTIONS:
        return LOAD_FUNCTIONS[extension](path)
    else:
        # Unknown extension, return the path itself to allow custom loading in ExperimentType
        return path
