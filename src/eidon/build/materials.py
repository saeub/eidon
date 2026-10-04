import csv
import json
import re
import warnings
from fnmatch import fnmatch
from pathlib import Path
from typing import Any
from PIL import Image


def load_txt(path: Path, schema: dict[str, Any] | None = None) -> str:
    with open(path, encoding="utf8") as f:
        return f.read().rstrip("\r\n")


def load_json(path: Path, schema: dict[str, Any] | None = None) -> Any:
    with open(path, encoding="utf8") as f:
        return json.load(f)


def load_csv(path: Path, schema: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    with open(path, encoding="utf8") as f:
        reader = csv.DictReader(f)
        subcolumn_paths = {
            column: _get_subcolumn_path(column) for column in reader.fieldnames
        }
        subcolumn_rows = []
        for row in reader:
            _check_columns(row, schema["columns"], path)
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


def _check_columns(
    row: dict[str, Any], columns_schema: dict[str, dict[str, Any]], path: Path
):
    """Validate a table row against column definitions and convert data types."""
    # Convert column names to regular expressions (* for string keys, # for integer indices)
    column_name_patterns = {
        name: re.compile(
            "^" + re.escape(name).replace(r"\*", r"\w+").replace(r"\#", r"\d+") + "$"
        )
        for name in columns_schema
    }

    # TODO: Refactor to avoid pattern matching multiple times

    # Check for missing and unknown columns
    required_columns = {
        name for name, schema in columns_schema.items() if schema.get("required")
    }
    allowed_columns = set(columns_schema.keys())
    missing_columns = [
        name
        for name in required_columns
        if not any(column_name_patterns[name].match(col) for col in row)
    ]
    if missing_columns:
        raise ValueError(
            f"Missing required columns in {path}: {', '.join(missing_columns)}"
        )
    unknown_columns = [
        col
        for col in row
        if not any(column_name_patterns[name].match(col) for name in allowed_columns)
    ]
    if unknown_columns:
        warnings.warn(f"Unknown columns in {path}: {', '.join(unknown_columns)}")

    # Convert data types
    for col, value in row.items():
        schema, = [
            schema
            for name, schema in columns_schema.items()
            if column_name_patterns[name].match(col)
        ]
        if "type" in schema:
            try:
                row[col] = schema["type"](value)
            except (ValueError, TypeError) as e:
                raise ValueError(
                    f"Error while converting column {col} in {path} "
                    f"to type {schema['type'].__name__}: {e}"
                )


def load_png(path: Path) -> Image.Image:
    return Image.open(path)


def load_jpeg(path: Path) -> Image.Image:
    warnings.warn(
        f"JPEG images ({path}) are not recommended for stimuli, as they use lossy compression. "
        "Consider using PNG images instead.",
        UserWarning,
    )
    return Image.open(path)


_load_functions = {
    ".txt": load_txt,
    ".json": load_json,
    ".csv": load_csv,
    ".png": load_png,
    ".jpg": load_jpeg,
    ".jpeg": load_jpeg,
}


def load_file(path: Path, schema: dict[str, Any] | None = None) -> Any:
    extension = path.suffix
    if extension in _load_functions:
        return _load_functions[extension](path, schema)
    else:
        # Unknown extension, return the path itself to allow custom loading in ExperimentType
        return path


def load_materials(
    materials_path: Path, materials_schema: dict[str, dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Load all files in a materials directory and validate them against a schema."""
    materials = {}
    material_paths = list(materials_path.glob("**/*"))
    for material_path in material_paths:
        if material_path.is_file():
            path = material_path.relative_to(materials_path).as_posix()
            if materials_schema is not None:
                matching_schemas = [
                    schema
                    for pattern, schema in materials_schema.items()
                    if fnmatch(path, pattern)
                ]
                if len(matching_schemas) == 0:
                    raise ValueError(
                        f"No matching schema for materials file {path}."
                    )
                elif len(matching_schemas) > 1:
                    raise ValueError(
                        f"Multiple matching schemas for materials file {path}: "
                        f"{', '.join(matching_schemas)}"
                    )
                schema = matching_schemas[0]
            else:
                schema = None
            materials[path] = load_file(material_path, schema)
    if materials_schema is not None:
        _check_materials(materials, materials_schema)
    return materials


def _check_materials(
    materials: dict[str, Any], materials_schema: dict[str, dict[str, Any]]
):
    """Validate loaded materials against a schema."""
    # Check for missing and unknown materials
    required_materials = {
        path for path, schema in materials_schema.items() if schema.get("required")
    }
    allowed_materials = set(materials_schema.keys())
    missing_materials = [path for path in required_materials if path not in materials]
    if missing_materials:
        raise ValueError(f"Missing required materials: {', '.join(missing_materials)}")
    unknown_materials = [
        path
        for path in materials
        if not any(fnmatch(path, pattern) for pattern in allowed_materials)
    ]
    if unknown_materials:
        warnings.warn(f"Unknown materials: {', '.join(unknown_materials)}")
