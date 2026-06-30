import json
from pathlib import Path
import shutil
import sys

import yaml

from eidon.build.stimuli import TextImage
from eidon.build.types import ExperimentType
from eidon.utils import ask_user_yes_no, get_package_version, import_custom_code


class ExperimentBuilder:
    def __init__(self, experiment_path: Path):
        self.experiment_path = experiment_path

    def build(self, generate_area_images: bool = False):
        if generate_area_images:
            TextImage.generate_area_images = True

        with open(self.experiment_path / "config.yaml", "r") as f:
            config = yaml.safe_load(f)

        experiment_name = config.pop("name")
        experiment_type_name = config.pop("type")
        eyelink_settings = config.pop("eyelink", None)

        import_custom_code(self.experiment_path)
        experiment_type_classes = ExperimentType.get_subclasses()
        if experiment_type_name not in experiment_type_classes:
            raise ValueError(
                f"Unknown experiment type: {experiment_type_name}"
                + f"\nAvailable types: {list(experiment_type_classes.keys())}"
            )
        experiment_type = experiment_type_classes[experiment_type_name](**config)

        if (self.experiment_path / "recordings").exists() and any(
            (self.experiment_path / "recordings").iterdir()
        ):
            user_confirms = ask_user_yes_no(
                "WARNING: There are already some recordings in this experiment. "
                "Rebuilding the experiment will delete the stimuli referenced in these recordings. "
                "The recordings will not be deleted, but they may become unusable.\n"
                "Do you really want to rebuild the experiment?"
            )
            if not user_confirms:
                sys.exit(1)
        shutil.rmtree(self.experiment_path / "stimuli", ignore_errors=True)
        shutil.rmtree(self.experiment_path / "sessions", ignore_errors=True)
        (self.experiment_path / "stimuli").mkdir(exist_ok=True)
        (self.experiment_path / "sessions").mkdir(exist_ok=True)
        (self.experiment_path / "recordings").mkdir(exist_ok=True)

        sessions = experiment_type.build(self.experiment_path)
        for name, session in sessions.items():
            with open(self.experiment_path / "sessions" / f"{name}.json", "w") as f:
                json.dump(session, f, indent=4)

        metadata = {
            "name": experiment_name,
            "eidon_version": get_package_version(),
            "tracking_mode": experiment_type.tracking_mode,
            # TODO: Move these settings to session?
            "background_color": experiment_type.background_color,
            "stimulus_area_px": experiment_type.stimulus_area_px,
            "margin_px": experiment_type.margin_px,
        }
        if eyelink_settings is not None:
            metadata["eyelink_settings"] = eyelink_settings
        with open(self.experiment_path / "experiment.json", "w") as f:
            json.dump(metadata, f, indent=4)
