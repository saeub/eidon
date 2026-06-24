import json
from pathlib import Path

import polars as pl
import pymovements as pm


class RecordingConverter:
    def __init__(self, experiment_path: Path):
        self.experiment_path = experiment_path
        self.experiment_definition = json.loads(
            (self.experiment_path / "experiment.json").read_text()
        )
        self.columns = ["time", "stage", "imgpath", "pixel_x", "pixel_y", "pupil"]

    def convert(self, recording_names: list[str] | None = None):
        if recording_names is None:
            asc_paths = list((self.experiment_path / "recordings").glob("*/*.asc"))
        else:
            asc_paths = [
                self.experiment_path / "recordings" / name / f"{name}.asc"
                for name in recording_names
            ]

        for asc_path in asc_paths:
            recording_name = asc_path.parent.name
            session_name = recording_name.removeprefix(
                self.experiment_definition["name"] + "."
            )
            session_name = "".join(session_name.split(".")[:-1])
            session_path = self.experiment_path / "sessions" / f"{session_name}.json"
            samples = self.convert_recording(asc_path, session_path)
            samples = samples.select(pl.col(self.columns))
            samples.write_csv(asc_path.with_suffix(".csv"))

    def convert_recording(self, asc_path: Path, session_path: Path) -> pl.DataFrame:
        session = json.loads(session_path.read_text())
        stage_stimuli = {}
        for stage_data in session["stages"]:
            if "$name" not in stage_data:
                continue
            # TODO: Handle more complex stages (e.g., QuestionTree)
            if "imgpath" in stage_data:
                stage_stimuli[(stage_data["$name"], None)] = stage_data["imgpath"]
            if "imgpaths" in stage_data:
                for page, imgpath in enumerate(stage_data["imgpaths"]):
                    stage_stimuli[(stage_data["$name"], str(page))] = imgpath

        gaze = pm.gaze.from_asc(
            asc_path,
            patterns=[
                r"TRIALID (?P<stage>.+)",
                {
                    "pattern": r"TRIAL_RESULT .+",
                    "column": "stage",
                    "value": None,
                },
                r"PAGE (?P<page>\d+)",
                {
                    "pattern": r"TRIAL_RESULT .+",
                    "column": "page",
                    "value": None,
                },
            ],
            trial_columns=["stage", "page"],
            messages=True,
        )
        gaze.unnest()
        samples = gaze.samples

        # Map stage names to image paths
        samples = samples.with_columns(
            imgpath=pl.struct(["stage", "page"]).map_elements(
                lambda x: stage_stimuli.get((x["stage"], x["page"])),
                return_dtype=pl.Utf8,
            )
        )

        return samples
