import json
import random
import tkinter as tk
import warnings
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

    def clean(self, recording_name: str, area_type: str = None, stage_pattern: str = None):
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
        gaze, stimuli = self._load_gaze(gaze_path, stage_pattern=stage_pattern)

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
                    "remove": False,
                }

        stimulus_labels = [
            f"{stage}: {page}" if page is not None else stage
            for stage, page, imgpath in stimuli
        ]
        stimulus_index = 0
        app = None
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
            if not backdrop_path.exists():
                if area_type is not None:
                    warnings.warn(
                        f"Stimulus image with {area_type} areas not found: {backdrop_path}. "
                        "Using image without areas instead."
                    )
                    backdrop_path = (self.experiment_path / imgpath).with_suffix(".png")
                else:
                    raise ValueError(
                        f"Stimulus image not found: {backdrop_path}. "
                        "Make sure the experiment has been built correctly."
                    )
            stimulus_image = PIL.Image.open(backdrop_path)
            if pd.isna(page):
                page = None
            src_points, dst_points = corrections[stage][page]["transform"]
            remove = corrections[stage][page]["remove"]
            settings = {}
            if app is not None:
                # Transfer settings from previous app instance
                settings["scale"] = app.scale.get()
                settings["simplification"] = app.simplification.get()
                settings["velocity_threshold"] = app.velocity_threshold.get()
                settings["line_width"] = app.line_width.get()
                settings["vertical"] = app.vertical.get()
            app = App(
                stimulus_gaze,
                stimulus_image,
                src_points=src_points,
                dst_points=dst_points,
                remove=remove,
                stimulus_index=stimulus_index,
                stimulus_labels=stimulus_labels,
                **settings,
            )
            corrections[stage][page]["transform"] = (app.src_points, app.dst_points)
            corrections[stage][page]["remove"] = app.remove.get()
            self._save_corrections(corrections, corrections_path)
            if app.action == "next":
                stimulus_index += 1
                if stimulus_index >= len(stimuli):
                    stimulus_index = len(stimuli) - 1
            elif app.action == "previous":
                stimulus_index -= 1
                if stimulus_index < 0:
                    stimulus_index = 0
            elif app.action == "first":
                stimulus_index = 0
            elif app.action == "last":
                stimulus_index = len(stimuli) - 1
            elif app.action.startswith("goto:"):
                stimulus_index = int(app.action.split(":")[1])
            else:
                break

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
        self, gaze_path: Path, stage_pattern: str = None
    ) -> tuple[pd.DataFrame, list[tuple[str, str, str]]]:
        gaze = pd.read_csv(gaze_path, dtype={"stage": str, "page": str, "imgpath": str})
        if stage_pattern is not None:
            gaze = gaze[gaze["stage"].str.match(stage_pattern)]
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
        fixation_cross=None,
        margin=100,
        scale=1.0,
        simplification=10,
        velocity_threshold=10.0,
        vertical=True,
        line_width=2,
        stimulus_index=None,
        stimulus_labels=None,
    ):
        super().__init__()

        if stimulus_labels is not None and stimulus_index is not None:
            self.title(f"{stimulus_labels[stimulus_index]} | eidon clean")
        elif stimulus_index is not None:
            self.title(f"{stimulus_index} | eidon clean")
        else:
            self.title("eidon clean")

        self.gaze = gaze
        self.image = image

        self.margin = margin
        self.fixation_cross = fixation_cross

        # Variables for "Edit" menu
        self.remove = tk.BooleanVar(value=remove)
        self.remove.trace_add("write", lambda *_: self._update_remove())
        self.vertical = tk.BooleanVar(value=vertical)
        self.vertical.trace_add("write", lambda *_: self._draw())

        # Variables for "View" menu
        self.scale = tk.DoubleVar(value=scale)
        self.scale.trace_add("write", lambda *_: self._update_scale())
        self.simplification = tk.IntVar(value=simplification)
        self.simplification.trace_add("write", lambda *_: self._update_simplification())
        self.velocity_threshold = tk.DoubleVar(value=velocity_threshold)
        self.velocity_threshold.trace_add("write", lambda *_: self._update_simplification())
        self.line_width = tk.IntVar(value=line_width)
        self.line_width.trace_add("write", lambda *_: self._draw())

        self.hover_point_index = None
        self.dragging_point_index = None
        self.action = None

        self.resizable(False, False)
        self.canvas = tk.Canvas(
            self,
            background="white",
        )
        self.canvas.pack()

        if stimulus_labels is not None and stimulus_index is not None:
            self.stimulus_slider = tk.Scale(
                self,
                from_=0,
                to=len(stimulus_labels) - 1,
                orient=tk.HORIZONTAL,
                showvalue=False,
                label=stimulus_labels[stimulus_index],
                command=lambda value: self.stimulus_slider.config(label=stimulus_labels[int(value)]),
            )
            self.stimulus_slider.pack(side=tk.BOTTOM, fill=tk.X)
            self.stimulus_slider.set(stimulus_index)
            self.stimulus_slider.bind("<ButtonRelease-1>", lambda _: self._exit(f"goto:{self.stimulus_slider.get()}"))

        menu = tk.Menu(self)
        self.config(menu=menu)

        edit_menu = tk.Menu(menu, tearoff=0)
        edit_menu.add_command(label="Undo (Ctrl+Z)", command=self._undo)
        edit_menu.add_separator()
        edit_menu.add_command(label="Reset corrections", command=self._reset_points)
        edit_menu.add_checkbutton(
            label="Mark data as removed (X)",
            variable=self.remove,
            command=self._update_remove,
        )
        edit_menu.add_separator()
        edit_menu.add_checkbutton(
            label="Vertical correction only", variable=self.vertical
        )
        menu.add_cascade(label="Edit", menu=edit_menu)

        view_menu = tk.Menu(menu, tearoff=0)
        view_menu.add_radiobutton(label="Scale: 100%", variable=self.scale, value=1.0)
        view_menu.add_radiobutton(label="Scale: 75%", variable=self.scale, value=0.75)
        view_menu.add_radiobutton(label="Scale: 50%", variable=self.scale, value=0.5)
        view_menu.add_separator()
        view_menu.add_radiobutton(
            label="Gaze resolution: 100% (slow!)", variable=self.simplification, value=1
        )
        view_menu.add_radiobutton(
            label="Gaze resolution: 10%", variable=self.simplification, value=10
        )
        view_menu.add_radiobutton(
            label="Gaze resolution: 5%", variable=self.simplification, value=20
        )
        view_menu.add_radiobutton(
            label="Gaze resolution: 1%", variable=self.simplification, value=100
        )
        view_menu.add_separator()
        view_menu.add_radiobutton(
            label="Velocity filter: none", variable=self.velocity_threshold, value=-1.0
        )
        view_menu.add_radiobutton(
            label="Velocity filter: 20 px/ms", variable=self.velocity_threshold, value=20.0
        )
        view_menu.add_radiobutton(
            label="Velocity filter: 10 px/ms", variable=self.velocity_threshold, value=10.0
        )
        view_menu.add_radiobutton(
            label="Velocity filter: 5 px/ms", variable=self.velocity_threshold, value=5.0
        )
        view_menu.add_radiobutton(
            label="Velocity filter: 2 px/ms", variable=self.velocity_threshold, value=2.0
        )
        view_menu.add_separator()
        view_menu.add_radiobutton(
            label="Line width: 1", variable=self.line_width, value=1
        )
        view_menu.add_radiobutton(
            label="Line width: 2", variable=self.line_width, value=2
        )
        view_menu.add_radiobutton(
            label="Line width: 3", variable=self.line_width, value=3
        )
        menu.add_cascade(label="View", menu=view_menu)

        self.canvas.bind("<Button-1>", self._on_left_mouse_down)
        self.canvas.bind("<Button-3>", self._on_right_mouse_down)
        self.canvas.bind("<ButtonRelease-1>", self._on_left_mouse_up)
        self.canvas.bind("<Motion>", self._on_left_mouse_move)
        self.canvas.bind("<B1-Motion>", self._on_left_mouse_drag)
        self.bind("<x>", lambda _: self._toggle_remove())
        self.bind("<Control-z>", lambda _: self._undo())
        self.bind("<Right>", lambda _: self._exit("next"))
        self.bind("<Left>", lambda _: self._exit("previous"))
        self.bind("<Home>", lambda _: self._exit("first"))
        self.bind("<End>", lambda _: self._exit("last"))
        self.bind("<Escape>", lambda _: self._exit("exit"))

        self._update_scale(draw=False)
        self._update_simplification(draw=False)

        self.history = []
        if src_points is None:
            self._reset_points(draw=False)
        else:
            self.src_points = src_points
            self.dst_points = dst_points
            self._store_history()

        self._draw()

        # Windows fix
        self.after(100, self._take_focus)

        self.mainloop()

    def _gaze_to_window_coords(self, x, y):
        scale = self.scale.get()
        return x * scale + self.margin, y * scale + self.margin

    def _window_to_gaze_coords(self, x, y):
        scale = self.scale.get()
        return (x - self.margin) / scale, (y - self.margin) / scale

    def _update_scale(self, draw=True):
        scale = self.scale.get()
        self.scaled_image = PIL.ImageTk.PhotoImage(
            self.image.resize(
                (
                    round(self.image.width * scale),
                    round(self.image.height * scale),
                )
            )
        )
        self.canvas.config(
            width=self.scaled_image.width() + 2 * self.margin,
            height=self.scaled_image.height() + 2 * self.margin,
        )
        if draw:
            self._draw()

    def _update_simplification(self, draw=True):
        # Reduce gaze resolution
        n = self.simplification.get()  # Average over n adjacent samples
        gaze = self.gaze[["time", "pixel_x", "pixel_y"]]
        gaze = gaze.groupby(gaze.index // n).mean().reset_index(drop=True)

        # Filter out fast movements
        velocity_threshold = self.velocity_threshold.get()  # px/ms
        if velocity_threshold > 0:
            # TODO: Use actual sample rate instead of assuming 1000 Hz
            velocity_threshold = velocity_threshold * n  # Convert to pixels per n samples
            gaze["next_pixel_x"] = gaze["pixel_x"].shift(-1)
            gaze["next_pixel_y"] = gaze["pixel_y"].shift(-1)
            gaze["velocity"] = np.sqrt(
                (gaze["next_pixel_x"] - gaze["pixel_x"]) ** 2
                + (gaze["next_pixel_y"] - gaze["pixel_y"]) ** 2
            )
            # Filter out points with velocity above the threshold
            gaze.loc[gaze["velocity"] > velocity_threshold, ["pixel_x", "pixel_y"]] = np.nan

        self.simplified_gaze = gaze[["time", "pixel_x", "pixel_y"]]
        if draw:
            self._draw()

    def _toggle_remove(self):
        self.remove.set(not self.remove.get())

    def _update_remove(self):
        self._store_history()
        self._draw()

    def _reset_points(self, draw=True):
        self.src_points = [
            (0, 0),
            (self.image.width / 2, 0),
            (self.image.width, 0),
            (0, self.image.height),
            (self.image.width / 2, self.image.height),
            (self.image.width, self.image.height),
        ]
        self.dst_points = self.src_points.copy()
        self._store_history()
        if draw:
            self._draw()

    def _on_left_mouse_down(self, event):
        if self.hover_point_index is not None:
            self.dragging_point_index = self.hover_point_index
        else:
            self.src_points.append([*self._window_to_gaze_coords(event.x, event.y)])
            self.dst_points.append([*self._window_to_gaze_coords(event.x, event.y)])
            self.dragging_point_index = len(self.dst_points) - 1
        self._draw()

    def _on_right_mouse_down(self, event):
        if self.hover_point_index is not None:
            del self.src_points[self.hover_point_index]
            del self.dst_points[self.hover_point_index]
            self.dragging_point_index = None
            self._store_history()
            self._draw()

    def _on_left_mouse_up(self, event):
        if self.dragging_point_index is not None:
            self.hover_point_index = self.dragging_point_index
            self.dragging_point_index = None
            self._store_history()
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
            if self.vertical.get():
                x = self.dst_points[self.dragging_point_index][0]
            self.dst_points[self.dragging_point_index] = [x, y]
            self._draw()

    def _undo(self):
        if len(self.history) > 1:
            self.history.pop()
            previous_state = self.history[-1]
            self.src_points, self.dst_points = [
                previous_state["transform"][0].copy(),
                previous_state["transform"][1].copy(),
            ]
            self.remove.set(previous_state["remove"])
            self._draw()

    def _store_history(self):
        new_state = {
            "transform": [self.src_points.copy(), self.dst_points.copy()],
            "remove": self.remove.get(),
        }
        previous_state = self.history[-1] if self.history else None
        if new_state != previous_state:
            self.history.append(new_state)

    def _draw(self):
        self.canvas.delete("all")
        self.canvas.create_image(
            *self._gaze_to_window_coords(0, 0), anchor=tk.NW, image=self.scaled_image
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

        # Draw gaze data
        remove = self.remove.get()
        for _, row in transformed_gaze.iterrows():
            x, y = self._gaze_to_window_coords(row["pixel_x"], row["pixel_y"])
            next_x, next_y = self._gaze_to_window_coords(row["next_pixel_x"], row["next_pixel_y"])
            self.canvas.create_line(
                x, y,
                next_x, next_y,
                fill="black" if not remove else "red",
                width=self.line_width.get(),
            )
            # Draw scattered dots
            dot_x = random.randint(0, 10)
            self.canvas.create_line(
                dot_x, y,
                dot_x + 1, y,
                fill="black" if not remove else "red",
                width=1,
            )

        # Draw remove label
        if remove:
            self.canvas.create_text(
                *self._gaze_to_window_coords(
                    self.image.width / 2, self.image.height / 2
                ),
                text="REMOVED",
                fill="red",
                font=("sans-serif", 48, "bold"),
            )

        # Draw transform points
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
                fill="turquoise",
                outline="turquoise",
            )
            self.canvas.create_line(
                src_x,
                src_y,
                dst_x,
                dst_y,
                fill="turquoise",
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
