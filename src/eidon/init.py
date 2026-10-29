import csv
import dataclasses
from pathlib import Path
from typing import Union, get_origin

import yaml

from eidon.build.types import ExperimentType


class ExperimentInitializer:
    def __init__(self, experiment_path: Path, experiment_type: str):
        self.experiment_path = experiment_path
        experiment_type_classes = ExperimentType.get_subclasses()
        if experiment_type not in experiment_type_classes:
            raise ValueError(
                f"Unknown experiment type: {experiment_type}"
                + f"\nAvailable types: {list(experiment_type_classes.keys())}"
            )
        self.experiment_type = experiment_type_classes[experiment_type]

    def initialize(self):
        docs_url = (
            f"https://saeub.github.io/eidon/reference/experiment-types/"
            f"{self.experiment_type.__name__}.html"
        )
        self.experiment_path.mkdir(parents=True, exist_ok=True)
        (self.experiment_path / "materials").mkdir(exist_ok=True)

        # Create config.yaml
        config = {
            "name": self.experiment_path.name,
            "type": self.experiment_type.__name__,
        }
        fields = self.experiment_type.__dataclass_fields__
        for field_name, field in fields.items():
            if field_name in {"experiment_path", "MATERIALS_SCHEMA"}:
                continue
            default_value = field.default
            if default_value is dataclasses.MISSING:
                config[field_name] = self._get_example_value(field.type)
            else:
                if isinstance(default_value, tuple):
                    default_value = list(default_value)
                config[field_name] = default_value
        with open(self.experiment_path / "config.yaml", "w", encoding="utf-8") as f:
            config = yaml.safe_dump(config, sort_keys=False)
            # Add empty lines between top-level keys for better readability
            spaced_config = "\n".join(
                line if not line[0].isidentifier() else "\n" + line
                for line in config.splitlines()
            )
            f.write(
                "# See documentation for all configuration options:\n"
                f"# {docs_url}#configuration\n" + spaced_config + "\n"
            )

        # Create materials files
        schema = self.experiment_type.MATERIALS_SCHEMA
        if schema is not None:
            for file_path, file_schema in schema.items():
                # TODO: Support wildcards
                file_path = self.experiment_path / "materials" / file_path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_description = file_schema.get("description", "")
                if file_path.suffix == ".csv":
                    columns = []
                    for column_name in file_schema.get("columns", {}):
                        columns.append(
                            column_name.replace("#", "0").replace(
                                "*", self._get_example_value(str)
                            )
                        )
                    with open(file_path, "w", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerow(columns)
                else:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(
                            file_description
                            + "\n\n"
                            + f"Documentation: {docs_url}#materials\n"
                        )

    def _get_example_value(self, field_type):
        if field_type == str:
            return "example"
        elif field_type == int:
            return 123
        elif field_type == float:
            return 1.23
        elif field_type == bool:
            return False
        elif field_type == list:
            return []
        elif field_type == dict:
            return {}
        elif (origin := get_origin(field_type)) is not None:
            if origin == Union:
                return self._get_example_value(field_type.__args__[0])
            elif origin == list:
                (inner_type,) = field_type.__args__
                return [self._get_example_value(inner_type)]
            elif origin == dict:
                key_type, value_type = field_type.__args__
                return {
                    self._get_example_value(key_type): self._get_example_value(
                        value_type
                    )
                }
            else:
                raise ValueError(f"Unsupported field type: {field_type}")
        else:
            raise ValueError(f"Unsupported field type: {field_type}")
