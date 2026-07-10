import json
import tkinter as tk
import warnings
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import PIL.Image
import PIL.ImageTk
import skimage

from eidon.utils import find_recordings


class RecordingCleaner:
    def __init__(self, experiment_path: Path):
        self.experiment_path = experiment_path
        self.experiment_definition = json.loads(
            (self.experiment_path / "experiment.json").read_text()
        )

    def clean(self, recording_name: str, area_type: str = None, vertical: bool = False):
        matching_recording_names = find_recordings(
            self.experiment_path, self.experiment_definition["name"], [recording_name]
        )
        if len(matching_recording_names) > 1:
            raise ValueError(
                f"Multiple recordings found for {recording_name}: {matching_recording_names}"
            )
        recording_name = matching_recording_names[0]
        gaze_path = (
            self.experiment_path
            / "recordings"
            / recording_name
            / f"{recording_name}.csv"
        )
        gaze, stimuli = self._load_gaze(gaze_path)

        corrections_path = gaze_path.with_suffix(".corrections.json")
        if corrections_path.exists():
            corrections = self._load_corrections(corrections_path)
        else:
            corrections = {}
            for stage, page, imgpath in stimuli:
                if pd.isna(page):
                    page = None
                corrections.setdefault(stage, {})[page] = {
                    "transform": (None, None),
                    "remove": [],
                }

        stimulus_index = 0
        while True:
            stage, page, imgpath = stimuli[stimulus_index]
            stage_condition = gaze["stage"] == stage
            page_condition = (
                gaze["page"] == page if page is not None else gaze["page"].isna()
            )
            stimulus_gaze = gaze[stage_condition & page_condition]
            backdrop_path_suffix = ".png"
            if area_type is not None:
                backdrop_path_suffix = f".{area_type}.png"
            backdrop_path = (self.experiment_path / imgpath).with_suffix(
                backdrop_path_suffix
            )
            stimulus_image = PIL.Image.open(backdrop_path)
            if pd.isna(page):
                page = None
            src_points, dst_points = corrections[stage][page]["transform"]
            remove = corrections[stage][page]["remove"]
            app = App(
                stimulus_gaze,
                stimulus_image,
                src_points=src_points,
                dst_points=dst_points,
                remove=remove,
                scale=1.0,
                vertical=vertical,
                stage=stage,
            )
            corrections[stage][page]["transform"] = (app.src_points, app.dst_points)
            corrections[stage][page]["remove"] = app.remove
            if app.action == "next":
                stimulus_index += 1
                if stimulus_index >= len(stimuli):
                    # stimulus_index = 0
                    break
            elif app.action == "previous":
                stimulus_index -= 1
                if stimulus_index < 0:
                    # stimulus_index = len(stimuli) - 1
                    break
            else:
                break

        self._save_corrections(corrections, corrections_path)

    def apply(self, recording_names: list[str] | None = None):
        recording_names = find_recordings(
            self.experiment_path, self.experiment_definition["name"], recording_names
        )

        for recording_name in recording_names:
            gaze_path = (
                self.experiment_path
                / "recordings"
                / recording_name
                / f"{recording_name}.csv"
            )

            corrections_path = gaze_path.with_suffix(".corrections.json")
            if not corrections_path.exists():
                warnings.warn(f"No corrections file found for {gaze_path}. Skipping.")
                continue

            print(f"Applying corrections for {recording_name}...")
            self._apply_corrections(
                gaze_path, corrections_path, gaze_path.with_suffix(".clean.csv")
            )

    def _load_gaze(
        self, gaze_path: Path
    ) -> tuple[pd.DataFrame, list[tuple[str, str, str]]]:
        gaze = pd.read_csv(gaze_path, dtype={"stage": str, "page": str, "imgpath": str})
        gaze["page"] = gaze["page"].replace({np.nan: None})
        stimuli = gaze[["stage", "page", "imgpath"]].drop_duplicates()
        stimuli = stimuli[stimuli["imgpath"].notna()]
        stimuli = list(stimuli.itertuples(index=False, name=None))
        return gaze, stimuli

    def _load_corrections(
        self, corrections_path: Path
    ) -> dict[str, dict[Any, dict[str, Any]]]:
        with open(corrections_path) as f:
            corrections_list = json.load(f)
        corrections_dict = {}
        for correction in corrections_list:
            stage = correction["stage"]
            page = correction["page"]
            transform = correction["transform"]
            remove = correction["remove"]
            if stage not in corrections_dict:
                corrections_dict[stage] = {}
            corrections_dict[stage][page] = {
                "transform": transform,
                "remove": remove,
            }
        return corrections_dict

    def _save_corrections(self, corrections: dict, corrections_path: Path):
        corrections_list = []
        for stage, pages in corrections.items():
            for page, correction in pages.items():
                corrections_list.append(
                    {
                        "stage": stage,
                        "page": page,
                        "transform": correction["transform"],
                        "remove": correction["remove"],
                    }
                )
        with open(corrections_path, "w") as f:
            json.dump(corrections_list, f, indent=4, allow_nan=False)

    def _apply_corrections(
        self, gaze_path: Path, corrections_path: Path, output_path: Path
    ):
        gaze, stimuli = self._load_gaze(gaze_path)
        corrections = self._load_corrections(corrections_path)

        gaze_corrected = pd.DataFrame()
        for stage, page, imgpath in stimuli:
            stage_condition = gaze["stage"] == stage
            page_condition = (
                gaze["page"] == page if page is not None else gaze["page"].isna()
            )
            stimulus_gaze = gaze[stage_condition & page_condition]
            if pd.isna(page):
                page = None
            transform_src, transform_dst = corrections[stage][page]["transform"]
            remove = corrections[stage][page]["remove"]
            if remove:
                stimulus_gaze.loc[:, ["pixel_x", "pixel_y", "pupil"]] = np.nan
            elif (
                    transform_src is not None
                    and transform_dst is not None
                    and transform_src != transform_dst
                ):
                    transform = get_transform(transform_src, transform_dst)
                    stimulus_gaze.loc[:, ["pixel_x", "pixel_y"]] = transform(
                        stimulus_gaze[["pixel_x", "pixel_y"]]
                    )
            gaze_corrected = pd.concat([gaze_corrected, stimulus_gaze])

        gaze_corrected.to_csv(output_path, index=False)


def get_transform(src_points, dst_points):
    src = np.array(src_points)
    dst = np.array(dst_points)
    transform = skimage.transform.ThinPlateSplineTransform.from_estimate(src, dst)
    return transform


class App(tk.Tk):
    POINT_RADIUS = 5

    def __init__(
        self,
        gaze,
        image,
        src_points=None,
        dst_points=None,
        remove=False,
        margin=100,
        scale=1.0,
        fixation_cross=None,
        vertical=False,
        stage=None,
    ):
        super().__init__()

        if stage is not None:
            self.title(f"{stage} | eidon clean")
        else:
            self.title("eidon clean")

        self.gaze = gaze
        self.image = PIL.ImageTk.PhotoImage(
            image.resize((round(image.width * scale), round(image.height * scale)))
        )

        self.margin = margin
        self.scale = scale
        self.fixation_cross = fixation_cross
        self.vertical = vertical

        self.simplified_gaze = self._simplify_gaze(10)

        if src_points is None:
            src_points = [
                (0, 0),
                (image.width / 2, 0),
                (image.width, 0),
                # (0, image.height / 2),
                # (image.width / 2, image.height / 2),
                # (image.width, image.height / 2),
                (0, image.height),
                (image.width / 2, image.height),
                (image.width, image.height),
            ]
        if dst_points is None:
            dst_points = src_points.copy()
        self.src_points = src_points
        self.dst_points = dst_points
        self.remove = remove

        self.hover_point_index = None
        self.dragging_point_index = None
        self.history = []
        self.action = None

        self.resizable(False, False)
        self.canvas = tk.Canvas(
            self,
            width=self.image.width() + 2 * self.margin,
            height=self.image.height() + 2 * self.margin,
            background="white",
        )
        self.canvas.pack()

        self.canvas.bind("<Button-1>", self._on_left_mouse_down)
        self.canvas.bind("<Button-3>", self._on_right_mouse_down)
        self.canvas.bind("<ButtonRelease-1>", self._on_left_mouse_up)
        self.canvas.bind("<Motion>", self._on_left_mouse_move)
        self.canvas.bind("<B1-Motion>", self._on_left_mouse_drag)
        self.bind("<x>", lambda _: self._toggle_remove())
        self.bind("<Control-z>", lambda _: self._undo())
        self.bind("<Right>", lambda _: self._exit("next"))
        self.bind("<Left>", lambda _: self._exit("previous"))
        self.bind("<Escape>", lambda _: self._exit("exit"))

        self._draw()

        # Windows fix
        self.after(100, self._take_focus)

        self.mainloop()

    def _gaze_to_window_coords(self, x, y):
        return x * self.scale + self.margin, y * self.scale + self.margin

    def _window_to_gaze_coords(self, x, y):
        return (x - self.margin) / self.scale, (y - self.margin) / self.scale

    def _simplify_gaze(self, n=10):
        gaze = self.gaze[["time", "pixel_x", "pixel_y"]]
        gaze = gaze.groupby(gaze.index // n).mean().reset_index(drop=True)
        return gaze

    def _on_left_mouse_down(self, event):
        if self.hover_point_index is not None:
            self._store_history()
            self.dragging_point_index = self.hover_point_index
        else:
            self._store_history()
            self.src_points.append(self._window_to_gaze_coords(event.x, event.y))
            self.dst_points.append(self._window_to_gaze_coords(event.x, event.y))
            self.dragging_point_index = len(self.dst_points) - 1
        self._draw()

    def _on_right_mouse_down(self, event):
        if self.hover_point_index is not None:
            self._store_history()
            del self.src_points[self.hover_point_index]
            del self.dst_points[self.hover_point_index]
            self.dragging_point_index = None
        self._draw()

    def _on_left_mouse_up(self, event):
        self.dragging_point_index = None
        self._draw()

    def _on_left_mouse_move(self, event):
        hover_point_index_before = self.hover_point_index
        for i, (x, y) in enumerate(self.dst_points):
            x, y = self._gaze_to_window_coords(x, y)
            dx = event.x - x
            dy = event.y - y
            if dx * dx + dy * dy < self.POINT_RADIUS**2:
                self.hover_point_index = i
                break
        else:
            self.hover_point_index = None

        if hover_point_index_before != self.hover_point_index:
            self._draw()

    def _on_left_mouse_drag(self, event):
        if self.dragging_point_index is not None:
            self.hover_point_index = None
            x, y = self._window_to_gaze_coords(event.x, event.y)
            if self.vertical:
                x = self.dst_points[self.dragging_point_index][0]
            self.dst_points[self.dragging_point_index] = (x, y)
            self._draw()

    def _toggle_remove(self):
        self._store_history()
        self.remove = not self.remove
        self._draw()

    def _undo(self):
        if self.history:
            previous_state = self.history.pop()
            self.src_points, self.dst_points = previous_state["transform"]
            self.remove = previous_state["remove"]
            self._draw()

    def _store_history(self):
        self.history.append(
            {
                "transform": [self.src_points.copy(), self.dst_points.copy()],
                "remove": self.remove,
            }
        )

    def _draw(self):
        self.canvas.delete("all")

        self.canvas.create_image(
            *self._gaze_to_window_coords(0, 0), anchor=tk.NW, image=self.image
        )

        if self.fixation_cross:
            x, y = self._gaze_to_window_coords(*self.fixation_cross)
            x1 = x - 10
            y1 = y - 10
            x2 = x + 10
            y2 = y + 10
            self.canvas.create_line(x1, y, x2, y, fill="red", width=2)
            self.canvas.create_line(x, y1, x, y2, fill="red", width=2)

        gaze = self.simplified_gaze
        gaze = pd.concat([gaze, gaze.shift(-1).add_prefix("next_")], axis=1)

        transform = get_transform(self.src_points, self.dst_points)
        transformed_gaze = gaze.copy()
        transformed_gaze[["pixel_x", "pixel_y"]] = transform(
            gaze[["pixel_x", "pixel_y"]]
        )
        transformed_gaze[["next_pixel_x", "next_pixel_y"]] = transform(
            gaze[["next_pixel_x", "next_pixel_y"]]
        )

        # Transform replaces NA with -1, so we need to set them back to NA
        transformed_gaze.loc[gaze["pixel_x"].isna(), "pixel_x"] = None
        transformed_gaze.loc[gaze["pixel_y"].isna(), "pixel_y"] = None
        transformed_gaze.loc[gaze["next_pixel_x"].isna(), "next_pixel_x"] = None
        transformed_gaze.loc[gaze["next_pixel_y"].isna(), "next_pixel_y"] = None

        for _, row in transformed_gaze.iterrows():
            x = row["pixel_x"]
            y = row["pixel_y"]
            next_x = row["next_pixel_x"]
            next_y = row["next_pixel_y"]
            self.canvas.create_line(
                *self._gaze_to_window_coords(x, y),
                *self._gaze_to_window_coords(next_x, next_y),
                fill="black" if not self.remove else "red",
                width=2,
            )
        if self.remove:
            self.canvas.create_text(
                *self._gaze_to_window_coords(
                    self.image.width() / 2, self.image.height() / 2
                ),
                text="REMOVED",
                fill="red",
                font=("sans-serif", 48, "bold"),
            )

        for i, ((src_x, src_y), (dst_x, dst_y)) in enumerate(
            zip(self.src_points, self.dst_points)
        ):
            src_x, src_y = self._gaze_to_window_coords(src_x, src_y)
            dst_x, dst_y = self._gaze_to_window_coords(dst_x, dst_y)
            self.canvas.create_oval(
                src_x - self.POINT_RADIUS,
                src_y - self.POINT_RADIUS,
                src_x + self.POINT_RADIUS,
                src_y + self.POINT_RADIUS,
                fill="lightblue",
                outline="lightblue",
            )
            self.canvas.create_line(
                src_x,
                src_y,
                dst_x,
                dst_y,
                fill="lightblue",
            )
            self.canvas.create_oval(
                dst_x - self.POINT_RADIUS,
                dst_y - self.POINT_RADIUS,
                dst_x + self.POINT_RADIUS,
                dst_y + self.POINT_RADIUS,
                fill=(
                    "red"
                    if i == self.hover_point_index or i == self.dragging_point_index
                    else "blue"
                ),
            )

    def _take_focus(self):
        self.deiconify()
        self.lift()
        self.focus_force()
        self.canvas.focus_set()

    def _exit(self, action):
        self.action = action
        self.destroy()
