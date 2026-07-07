import json
import math
import time
from pathlib import Path
from typing import Any

import pyglet

EYE_TRACKERS = {
    "eyelink-1000-plus": "Eyelink 1000 Plus",
    "eyelink-portable-duo": "Eyelink Portable Duo",
}
TRACKING_MODES = {
    "head-stabilized": "Head-stabilized (with chinrest or headrest)",
    "remote": "Remote (without headrest)",
}

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
        if self.latest_setup is not None:
            # Latest setup exists
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

        okay = False
        while not okay:
            new_setup["eye_tracker"] = self._select_from_list(
                "Select eye tracker:", EYE_TRACKERS
            )
            new_setup["tracking_mode"] = self._select_from_list(
                "Select tracking mode:", TRACKING_MODES
            )

            new_setup["stimulus_area_width_mm"] = self._get_float_measurement(
                "Measure the WIDTH of the black rectangle on this screen.\n\n"
                "Enter the measurement in millimeters as a number (e.g., 605), then press [ENTER].",
                rectangle=True,
            )

            new_setup["stimulus_area_height_mm"] = self._get_float_measurement(
                "Measure the HEIGHT of the black rectangle on this screen.\n\n"
                "Enter the measurement in millimeters as a number (e.g., 605), then press [ENTER].",
                rectangle=True,
            )

            if new_setup["tracking_mode"] == "head-stabilized":
                new_setup["eye_to_screen_distance_mm"] = self._get_float_measurement(
                    "Measure the shortest distance from the participant's eyes to the screen.\n\n"
                    "Enter the measurement in millimeters as a number (e.g., 605), then press [ENTER]."
                )

            elif new_setup["tracking_mode"] == "remote":
                new_setup["eye_to_screen_distance_mm"] = self._get_float_measurement(
                    "Measure the expected shortest distance from the participant's eyes to the screen.\n\n"
                    "Enter the measurement in millimeters as a number (e.g., 605), then press [ENTER]."
                )
                new_setup["camera_to_screen_distance_mm"] = self._get_float_measurement(
                    "Measure the shortest distance from the back of the camera case to the screen.\n\n"
                    "IMPORTANT: Make sure to update this setting on the host PC, too! "
                    "Refer to your eye tracker's instruction manual for more information.\n\n"
                    "Enter the measurement in millimeters as a number (e.g., 605), then press [ENTER]."
                )
            okay = self._check_trackable_range(new_setup)

        return new_setup

    def _save_setup(self, setup: dict[str, Any]):
        if self.latest_setup is None or self.latest_setup | {
            "timestamp": None
        } != setup | {"timestamp": None}:
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
            x=self.display_width // 2,
            y=self.display_height // 2,
            anchor_x="center",
            anchor_y="center",
            width=self.display_width // 2,
            multiline=True,
            font_size=self.font_size,
            color=(0, 0, 0),
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

    def _select_from_list(self, instructions: str, items: dict[str, Any]) -> str:
        device_keys = {str(i): key for i, key in enumerate(items, start=1)}
        text = f"{instructions}\n\n"
        text += "\n".join(f"[{i}] {items[key]}" for i, key in device_keys.items())
        text += "\n\nPress the corresponding number key to select."
        label = pyglet.text.Label(
            text=text,
            x=self.display_width // 2,
            y=self.display_height // 2,
            anchor_x="center",
            anchor_y="center",
            width=self.display_width * 0.9,
            multiline=True,
            font_size=self.font_size,
            color=(0, 0, 0),
        )

        selected = None

        def on_key_press(symbol, modifiers):
            nonlocal selected
            number = pyglet.window.key.symbol_string(symbol).removeprefix("_").removeprefix("NUM_")
            if number in device_keys:
                selected = device_keys[number]

        self.window.push_handlers(on_key_press=on_key_press)
        self.window.clear()
        label.draw()
        self.window.flip()

        while selected is None:
            pyglet.app.platform_event_loop.step(0.001)
            self.window.dispatch_events()

        self.window.remove_handlers(on_key_press=on_key_press)

        return selected

    def _check_trackable_range(self, setup: dict[str, Any]) -> bool:
        distance_mm = setup["eye_to_screen_distance_mm"]
        width_mm = setup["stimulus_area_width_mm"]
        height_mm = setup["stimulus_area_height_mm"]
        width_deg = 2 * math.degrees(math.atan(width_mm / 2 / distance_mm))
        height_deg = 2 * math.degrees(math.atan(height_mm / 2 / distance_mm))
        max_width_deg, max_height_deg = TRACKABLE_RANGES[setup["eye_tracker"]]
        min_distance_mm = max(
            width_mm / 2 / math.sin(math.radians(max_width_deg / 2)),
            height_mm / 2 / math.sin(math.radians(max_height_deg / 2)),
        )

        if width_deg > max_width_deg or height_deg > max_height_deg:
            label = pyglet.text.Label(
                f"The stimulus area exceeds the eye tracker's trackable range.\n\n"
                f"Stimulus area: {width_deg:.1f}° x {height_deg:.1f}°\n"
                f"Maximum trackable area: {max_width_deg:.1f}° x {max_height_deg:.1f}°\n\n"
                "Options:\n"
                "- Reduce the size of the stimulus area in config.yaml and rebuild the experiment.\n"
                f"- Increase the eye-to-screen distance to at least {min_distance_mm:.1f} mm.\n\n"
                "Press [SPACE] to repeat the measurements or [ESCAPE] to exit.",
                x=self.display_width // 2,
                y=self.display_height // 2,
                anchor_x="center",
                anchor_y="center",
                width=self.display_width * 0.9,
                multiline=True,
                font_size=self.font_size,
                color=(0, 0, 0),
            )

            repeat = None

            def on_key_press(symbol, modifiers):
                nonlocal repeat
                if pyglet.window.key.symbol_string(symbol) == "SPACE":
                    repeat = True
                elif pyglet.window.key.symbol_string(symbol) == "ESCAPE":
                    repeat = False

            self.window.push_handlers(on_key_press=on_key_press)
            self.window.clear()
            label.draw()
            self.window.flip()

            while repeat is None:
                pyglet.app.platform_event_loop.step(0.001)
                self.window.dispatch_events()

            self.window.remove_handlers(on_key_press=on_key_press)

            if not repeat:
                exit(1)
            return False

        return True
