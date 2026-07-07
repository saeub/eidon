import json
import time
from pathlib import Path
from typing import Any

import pyglet

from eidon.run.events import Event

TRACKABLE_RANGES = {  # (horizontal, vertical) in degrees
    "eyelink-1000-plus": (32, 25),
    "eyelink-portable-duo": (32, 25),
}


class HardwareSetup:
    def __init__(self, experiment_path: str | Path | None = None, screen: int = 0):
        self.experiment_path = Path(experiment_path).absolute()

        with open(self.experiment_path / "experiment.json") as f:
            experiment_definition = json.load(f)

        self.display_width, self.display_height = experiment_definition[
            "stimulus_area_px"
        ]
        # TODO: Ask about eye-tracker settings during setup instead of defining them in experiment.json
        self.eye_tracker = experiment_definition["eye_tracker"]
        self.tracking_mode = experiment_definition["tracking_mode"]

        assert self.eye_tracker in TRACKABLE_RANGES, (
            f"Unknown eye_tracker specified in config.yaml: {self.eye_tracker}. "
            f"Supported eye trackers: {list(TRACKABLE_RANGES.keys())}"
        )
        assert self.tracking_mode in ["head-stabilized", "remote"], (
            f"Unknown tracking_mode specified in config.yaml: {self.tracking_mode}. "
            f"Supported tracking modes: ['head-stabilized', 'remote']"
        )

        self.setups_path = self.experiment_path / "setups"
        self.setups_path.mkdir(parents=True, exist_ok=True)

        all_setups = sorted(self.setups_path.glob("*.json"))
        if all_setups:
            # Find most recent setup
            self.latest_setup = json.loads(all_setups[-1].read_text(encoding="utf-8"))
        else:
            # No previous setup found
            self.latest_setup = None

        self.font_size = self.display_height // 40

        self.clock = pyglet.clock.get_default()

        screen = pyglet.display.get_display().get_screens()[screen]
        self.screen_scale = screen.get_scale()
        self.window = pyglet.window.Window(fullscreen=True, screen=screen)
        self.window.set_mouse_visible(True)

        self._viewport_x = 0
        self._viewport_y = 0

        def on_resize(width, height):
            # Set viewport to use display coordinates (centered in the window)
            self._viewport_x = int(
                (width * self.screen_scale - self.display_width) // 2
            )
            self._viewport_y = int(
                (height * self.screen_scale - self.display_height) // 2
            )
            pyglet.gl.glViewport(
                self._viewport_x,
                self._viewport_y,
                self.display_width,
                self.display_height,
            )
            self.window.projection = pyglet.math.Mat4.orthogonal_projection(
                0, self.display_width, 0, self.display_height, -1, 1
            )

        self.window._on_internal_resize = on_resize
        self.window.dispatch_events()  # Trigger initial on_resize()

        pyglet.gl.glClearColor(1.0, 1.0, 1.0, 1.0)
        self.window.clear()

    def setup(self):
        if (
            self.latest_setup is not None
            and self.latest_setup.get("eye_tracker") == self.eye_tracker
            and self.latest_setup.get("tracking_mode") == self.tracking_mode
        ):
            # Latest setup exists and eye-tracker settings have not changed
            if self._confirm_setup(self.latest_setup):
                self.window.close()
                return
        # No setup exists, eye-tracker settings have changed, or user wants to redo it
        while True:
            new_setup = self._do_setup()
            if self._confirm_setup(new_setup):
                self._save_setup(new_setup)
                self.window.close()
                return

    def _do_setup(self) -> dict[str, Any]:
        new_setup = {
            "eye_tracker": self.eye_tracker,
            "tracking_mode": self.tracking_mode,
            "stimulus_area_width_px": self.display_width,
            "stimulus_area_height_px": self.display_height,
        }

        self._show_text(
            "Hardware setup\n\n"
            "In order to proceed with data collection, some measurements need to be taken. "
            "You will need a measuring tape.\n\n"
            "In general, please read the instruction manual of your eye-tracker manufacturer "
            "and follow their recommendations!\n\n"
            "Press [SPACE] to continue."
        )

        # TODO: Check if eye tracker and tracking mode are correctly defined

        if self.tracking_mode == "head-stabilized":
            new_setup["eye_to_screen_distance_mm"] = self._get_float_measurement(
                "Measure the shortest distance from the participant's eyes to the screen.\n"
                "Enter the measurement in millimeters as a number (e.g., 605), then press [ENTER]."
            )

        elif self.tracking_mode == "remote":
            new_setup["camera_to_screen_distance_mm"] = self._get_float_measurement(
                "Measure the shortest distance from the back of the camera case to the screen.\n"
                "IMPORTANT: Make sure to update this setting on the host PC, too! "
                "Refer to your eye tracker's instruction manual for more information.\n"
                "Enter the measurement in millimeters as a number (e.g., 605), then press [ENTER]."
            )

        new_setup["stimulus_area_width_mm"] = self._get_float_measurement(
            "Measure the WIDTH of the black rectangle on this screen.\n"
            "Enter the measurement in millimeters as a number (e.g., 605), then press [ENTER].",
            rectangle=True,
        )

        new_setup["stimulus_area_height_mm"] = self._get_float_measurement(
            "Measure the HEIGHT of the black rectangle on this screen.\n"
            "Enter the measurement in millimeters as a number (e.g., 605), then press [ENTER].",
            rectangle=True,
        )

        return new_setup

    def _save_setup(self, setup: dict[str, Any]):
        if self.latest_setup is None or self.latest_setup | {"timestamp": None} != setup | {"timestamp": None}:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"setup.{timestamp}.json"
            config_path = self.setups_path / filename
            setup["timestamp"] = timestamp
            with open(config_path, "w") as f:
                json.dump(setup, f, indent=4)
            self.latest_setup = setup

    def _confirm_setup(self, setup: dict[str, Any]) -> bool:
        text = "Are these measurements correct?\n\n"

        text += "\n".join(
            f"{key}: {value}" for key, value in setup.items() if key != "timestamp"
        )

        text += "\n\nPress [Y] for yes or [N] for no."

        batch = pyglet.graphics.Batch()

        label = pyglet.text.Label(
            text=text,
            color=(0, 0, 0),
            font_size=self.font_size,
            anchor_x="center",
            anchor_y="center",
            x=self.display_width // 2,
            y=self.display_height // 2,
            multiline=True,
            width=self.display_width // 2,
            batch=batch,
        )

        confirmed = None

        def on_key_press(symbol, modifiers):
            nonlocal confirmed
            if pyglet.window.key.symbol_string(symbol) == "Y":
                confirmed = True
            elif pyglet.window.key.symbol_string(symbol) == "N":
                confirmed = False

        self.window.push_handlers(on_key_press=on_key_press)
        self.window.clear()
        batch.draw()
        self.window.flip()

        while confirmed is None:
            pyglet.app.platform_event_loop.step(0.001)
            self.window.dispatch_events()

        self.window.remove_handlers(on_key_press=on_key_press)

        return confirmed

    def _show_text(self, text: str):
        label = pyglet.text.Label(
            text=text,
            x=self.display_width // 2,
            y=self.display_height // 2,
            anchor_x="center",
            anchor_y="center",
            width=self.display_width,
            multiline=True,
            font_size=self.font_size,
            color=(0, 0, 0),
        )

        done = False

        def on_key_press(symbol: int, modifiers: int):
            if pyglet.window.key.symbol_string(symbol) == "SPACE":
                nonlocal done
                done = True

        self.window.push_handlers(on_key_press=on_key_press)
        self.window.clear()
        label.draw()
        self.window.flip()

        while not done:
            pyglet.app.platform_event_loop.step(0.001)
            self.window.dispatch_events()

    def _get_float_measurement(
        self, instructions: str, rectangle: bool = False
    ) -> float:
        batch = pyglet.graphics.Batch()

        if rectangle:
            rect = pyglet.shapes.Rectangle(
                x=0,
                y=0,
                width=self.display_width,
                height=self.display_height,
                color=(0, 0, 0),
                batch=batch,
            )

        label = pyglet.text.Label(
            text=instructions,
            x=self.display_width // 2,
            y=self.display_height // 2,
            anchor_x="center",
            anchor_y="bottom",
            width=self.display_width * 0.9,
            multiline=True,
            font_size=self.font_size,
            color=(255, 255, 255) if rectangle else (0, 0, 0),
            batch=batch,
        )

        text_entry = pyglet.gui.TextEntry(
            text="",
            x=self.display_width // 4,
            y=self.display_height // 2,
            width=self.display_width // 2,
            batch=batch,
        )
        text_entry._layout.document.set_style(
            0, len(text_entry.value), {"font_size": self.font_size, "align": "center"}
        )
        text_entry.height = text_entry._layout.content_height
        text_entry.y = self.display_height // 2 - text_entry.height

        self.window.push_handlers(text_entry)

        measurement = None

        @text_entry.event
        def on_commit(widget, value):
            nonlocal measurement
            try:
                measurement = float(value)
            except ValueError:
                text_entry.value = ""

        while measurement is None:
            text_entry.focus = True
            pyglet.app.platform_event_loop.step(0.001)
            self.window.dispatch_events()
            self.window.clear()
            batch.draw()
            self.window.flip()

        self.window.remove_handlers(text_entry)

        return measurement
