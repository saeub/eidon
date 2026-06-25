import json
from pathlib import Path
from typing import Any

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
            print(f"Converting {recording_name}...")
            session_name = recording_name.removeprefix(
                self.experiment_definition["name"] + "."
            )
            session_name = "".join(session_name.split(".")[:-1])
            session_path = self.experiment_path / "sessions" / f"{session_name}.json"
            samples, metadata = self.convert_recording(asc_path, session_path)
            samples.write_csv(asc_path.with_suffix(".csv"))
            asc_path.with_suffix(".json").write_text(json.dumps(metadata, indent=4))

    def convert_recording(
        self, asc_path: Path, session_path: Path
    ) -> tuple[pl.DataFrame, dict[str, Any]]:
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
        samples = samples.select(pl.col(self.columns))

        calibration_data = self.get_calibration_data(gaze)
        metadata = {
            "session_name": session_path.stem,
            "eye": gaze._metadata["tracked_eye"],
            "calibrations": calibration_data.to_dicts(),
        }

        return samples, metadata

    def get_calibration_data(self, gaze: pm.Gaze) -> pl.DataFrame:
        trials = gaze.messages.filter(pl.col("content").str.contains("TRIALID")).select(
            pl.col("time"),
            pl.col("content").str.extract(r"TRIALID (?P<stage>.+)").alias("stage"),
        )

        # Map stage names to calibrations
        stage_calibrations = gaze.calibrations.join_asof(
            trials,
            left_on="time",
            right_on="time",
            strategy="backward",
        )
        # Only keep the final calibration for each stage
        stage_calibrations = stage_calibrations.group_by(
            "stage", maintain_order=True
        ).last()

        # Map stage names to validations
        stage_validations = gaze.validations.join_asof(
            trials,
            left_on="time",
            right_on="time",
            strategy="backward",
        )
        # Only keep the final validation for each stage
        stage_validations = stage_validations.group_by(
            "stage", maintain_order=True
        ).last()

        # Join the stage calibrations and validations
        calibration_data = stage_calibrations.select(
            pl.col("stage"),
            pl.col("time", "num_points", "eye").name.prefix("calibration_"),
            pl.col("tracking_mode"),
        ).join(
            stage_validations.select(
                pl.col("stage"),
                pl.col("time", "num_points", "eye").name.prefix("validation_"),
                pl.col("accuracy_avg").alias("avg_error"),
                pl.col("accuracy_max").alias("max_error"),
            ),
            on="stage",
        )

        # Remove validations that occurred after the last calibration
        validation_columns = [
            "validation_time",
            "validation_num_points",
            "validation_eye",
            "avg_error",
            "max_error",
        ]
        calibration_data = calibration_data.with_columns(
            [
                pl.when(pl.col("calibration_time") < pl.col("validation_time"))
                .then(pl.col(column))
                .otherwise(None)
                .alias(column)
                for column in validation_columns
            ]
        )
        return calibration_data
