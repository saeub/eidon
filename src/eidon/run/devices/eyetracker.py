from abc import ABC, abstractmethod
from hashlib import md5
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
import pyglet

try:
    import pylink

    PYLINK_AVAILABLE = True
except ImportError:
    PYLINK_AVAILABLE = False

from eidon.run.stages import Backdrop, DriftCorrect, Setup
from eidon.run.events import Event

if TYPE_CHECKING:
    from eidon.run import ExperimentRunner


class EyeTracker(ABC):
    @abstractmethod
    def get_setup_stage_type(self) -> type[Setup]:
        pass

    @abstractmethod
    def get_drift_correct_stage_type(self) -> type[DriftCorrect]:
        pass

    @abstractmethod
    def start_recording(self) -> None:
        pass

    @abstractmethod
    def stop_recording(self) -> None:
        pass

    @abstractmethod
    def send_message(self, message: str) -> None:
        pass

    @abstractmethod
    def send_status_message(self, message: str) -> None:
        pass

    @abstractmethod
    def set_backdrop(self, backdrop: Backdrop | None, title: str | None = None) -> None:
        pass

    @abstractmethod
    def poll_events(self) -> list[Event]:
        pass

    @abstractmethod
    def poll_host_events(self) -> list[Event]:
        pass

    @abstractmethod
    def save_data(self) -> None:
        pass


class MouseTracker(EyeTracker):
    def __init__(self, window: pyglet.window.BaseWindow, origin_x: int, origin_y: int):
        self.window = window
        self.window.set_mouse_visible(True)
        self.window.push_handlers(
            on_mouse_motion=self.on_mouse_motion,
            on_mouse_press=self.on_mouse_press,
        )
        self.origin_x = origin_x
        self.origin_y = origin_y
        self.clock = pyglet.clock.get_default()
        self.current_position = (None, None)
        self.events: list[Event] = []

    # TODO: type hints
    def on_mouse_motion(self, x, y, dx, dy):
        self.current_position = (
            x - self.origin_x,
            self.window.height - y - self.origin_y,
        )

    def on_mouse_press(self, x, y, button, modifiers):
        time = self.clock.time()
        x, y = self.current_position
        self.events.append(Event("fixation", time, {"x": x, "y": y}))

    class MouseTrackerSetup(Setup):
        """Do not use this stage directly. Use Setup instead."""

        def start(self):
            self.finished = False

            self.runner.window.clear()
            label = pyglet.text.Label(
                "Eye tracker setup\n[ESC] to continue",
                color=(0, 0, 0, 255),
                x=self.runner.display_width / 2,
                y=self.runner.display_height / 2,
                anchor_x="center",
                font_size=30,
                multiline=True,
                width=self.runner.display_width,
                align="center",
            )
            label.draw()
            self.runner.window.flip()

        def on_event(self, event: Event):
            if event.type == "key" and event.data["symbol"] == "ESCAPE":
                self.finished = True

        def update(self) -> None | dict[str, Any]:
            if self.finished:
                return {}

    def get_setup_stage_type(self) -> type[MouseTrackerSetup]:
        return self.MouseTrackerSetup

    class MouseTrackerDriftCorrect(DriftCorrect):
        """Do not use this stage directly. Use DriftCorrect instead."""

        def start(self):
            self.finished = False

            self.runner.window.clear()
            cross_x, cross_y = self.location
            cross_y = self.runner.display_height - cross_y  # Invert y-axis
            hline = pyglet.shapes.Line(
                cross_x - 10,
                cross_y,
                cross_x + 10,
                cross_y,
                thickness=2,
                color=(0, 0, 0),
            )
            vline = pyglet.shapes.Line(
                cross_x,
                cross_y - 10,
                cross_x,
                cross_y + 10,
                thickness=2,
                color=(0, 0, 0),
            )
            label = pyglet.text.Label(
                "Drift correct\n[SPACE] to continue",
                color=(0, 0, 0, 255),
                x=self.runner.display_width / 2,
                y=self.runner.display_height / 2,
                anchor_x="center",
                font_size=30,
                multiline=True,
                width=self.runner.display_width,
                align="center",
            )
            hline.draw()
            vline.draw()
            label.draw()
            self.runner.window.flip()

        def on_event(self, event: Event):
            if event.type == "key" and event.data["symbol"] == "SPACE":
                self.finished = True

        def update(self) -> None | dict[str, Any]:
            if self.finished:
                return {}

    def get_drift_correct_stage_type(self) -> type[MouseTrackerDriftCorrect]:
        return self.MouseTrackerDriftCorrect

    def start_recording(self) -> None:
        # TODO
        pass

    def stop_recording(self) -> None:
        # TODO
        pass

    def send_message(self, message: str) -> None:
        # TODO
        pass

    def send_status_message(self, message: str) -> None:
        # TODO
        pass

    def set_backdrop(self, backdrop: Backdrop | None, title: str | None = None) -> None:
        pass

    def poll_events(self) -> list[tuple]:
        events = self.events.copy()
        self.events.clear()
        return events

    def poll_host_events(self) -> list[tuple]:
        return []

    def save_data(self) -> None:
        # TODO
        pass


class EyeLink(EyeTracker):
    def __new__(cls, *args, **kwargs):
        if not PYLINK_AVAILABLE:
            raise ImportError("pylink is required for EyeLink support.")
        return super().__new__(cls)

    def __init__(
        self,
        edf_path: Path | str,
        runner: "ExperimentRunner",
        participant_control: bool = False,
        settings: dict[str, Any] | None = None,
    ):
        self.runner = runner
        self.eyelink = pylink.EyeLink()

        # pylink.beginRealTimeMode(100)

        self.graphics = _EyeLinkGraphics(self.runner, participant_control)
        pylink.openGraphicsEx(self.graphics)

        edf_path = Path(edf_path)
        self.local_filename = str(edf_path)
        self.host_filename = (
            "".join(c if c.isalnum() else "_" for c in edf_path.stem[:4])
            + md5(edf_path.stem.encode("utf-8")).hexdigest()[:4]
            + ".edf"
        )
        self.eyelink.openDataFile(self.host_filename)

        display_coords = (
            f"0 0 {self.runner.display_width - 1} {self.runner.display_height - 1}"
        )
        self.eyelink.sendMessage(f"DISPLAY_COORDS {display_coords}")
        self.eyelink.sendCommand(f"screen_pixel_coords = {display_coords}")

        if settings is not None:
            for setting, value in settings.items():
                self.eyelink.sendCommand(f"{setting} = {value}")

    class EyeLinkSetup(Setup):
        """Do not use this stage directly. Use Setup instead."""

        def start(self):
            # TODO: Configure accept_keys in stage definition (or runner?)
            self.runner.eyetracker.graphics.enable()
            self.runner.eyetracker.eyelink.doTrackerSetup()
            self.runner.eyetracker.graphics.disable()
            self.finished = True

        def on_event(self, event: Event):
            # Events are handled in _EyeLinkGraphics
            pass

        def update(self):
            return {}

    def get_setup_stage_type(self):
        return self.EyeLinkSetup

    class EyeLinkDriftCorrect(DriftCorrect):
        """Do not use this stage directly. Use DriftCorrect instead."""

        def start(self):
            self.runner.eyetracker.graphics.enable()
            while True:
                try:
                    self.runner.eyetracker.eyelink.doDriftCorrect(*self.location, 1, 0)
                    self.runner.eyetracker.eyelink.stopRecording()
                except RuntimeError as e:
                    if e.args[0] == "Escape key pressed":
                        self.runner.eyetracker.eyelink.doTrackerSetup()
                        continue  # Back to drift correct
                    else:
                        raise e
                break
            self.runner.eyetracker.graphics.disable()
            self.finished = True

        def on_event(self, event: Event):
            # Events are handled in _EyeLinkGraphics
            pass

        def update(self):
            return {}

    def get_drift_correct_stage_type(self):
        return self.EyeLinkDriftCorrect

    def start_recording(self) -> None:
        self.eyelink.startRecording(1, 1, 1, 1)

    def stop_recording(self) -> None:
        self.eyelink.stopRecording()

    def send_message(self, message: str) -> None:
        self.eyelink.sendMessage(message)

    def send_status_message(self, message: str) -> None:
        self.eyelink.sendCommand(f"record_status_message '{message}'")

    def set_backdrop(self, backdrop: Backdrop | None) -> None:
        self.eyelink.sendCommand("clear_screen 0")

        if backdrop is None:
            return

        x, y = backdrop.sprite.x, backdrop.sprite.y
        width, height = backdrop.sprite.width, backdrop.sprite.height

        # Invert y-axis
        y = self.runner.display_height - y - height

        # Convert to integer
        x = round(x)
        y = round(y)
        width = round(width)
        height = round(height)

        imgpath = str(backdrop.image_path)
        relative_imgpath = str(
            backdrop.image_path.relative_to(self.runner.recording_path, walk_up=True)
        )
        # TODO: Use bitmapBackdrop to avoid re-reading the file
        self.eyelink.imageBackdrop(imgpath, 0, 0, width, height, x, y, 0)
        self.send_message(
            f"!V IMGLOAD TOP_LEFT {relative_imgpath} {x} {y} {width} {height}"
        )

    def poll_events(self) -> list[Event]:
        events = []
        while self.eyelink.getNextData() != 0:
            eyelink_event = self.eyelink.getFloatData()

            if isinstance(eyelink_event, pylink.EndSaccadeEvent):
                time = eyelink_event.getTime()  # TODO: Convert to experiment time
                x, y = eyelink_event.getEndGaze()
                events.append(Event("fixation", time, {"x": x, "y": y}))

            elif isinstance(eyelink_event, pylink.ButtonEvent):
                for button, state in zip(
                    eyelink_event.getButtons(), eyelink_event.getButtonStates()
                ):
                    if state == 1:
                        # TODO: Convert to experiment time
                        time = eyelink_event.getTime()
                        events.append(Event("button", time, {"button": button}))

        return events

    def poll_host_events(self) -> list[tuple]:
        events = []
        while (host_event := self.eyelink.readKeyButton())[0] != 0:
            symbol = self._host_key_to_symbol(host_event[0])
            events.append(Event("hostkey", None, {"symbol": symbol}))
        return events

    def save_data(self) -> None:
        self.eyelink.closeDataFile()
        self.eyelink.receiveDataFile(self.host_filename, self.local_filename)

    def _host_key_to_symbol(self, key: int) -> str:
        key_map = {
            pylink.ENTER_KEY: "ENTER",
            pylink.ESC_KEY: "ESCAPE",
            pylink.CURS_UP: "UP",
            pylink.CURS_DOWN: "DOWN",
            pylink.CURS_LEFT: "LEFT",
            pylink.CURS_RIGHT: "RIGHT",
            ord(" "): "SPACE",
            ord("+"): "PLUS",
            ord("-"): "MINUS",
        }
        if key in key_map:
            return key_map[key]
        else:
            return chr(key)

    def _symbol_to_host_key(self, symbol: str) -> int | None:
        key_map = {
            "ENTER": pylink.ENTER_KEY,
            "ESCAPE": pylink.ESC_KEY,
            "UP": pylink.CURS_UP,
            "DOWN": pylink.CURS_DOWN,
            "LEFT": pylink.CURS_LEFT,
            "RIGHT": pylink.CURS_RIGHT,
            "SPACE": ord(" "),
            "PLUS": ord("+"),
            "MINUS": ord("-"),
            "NUM_ADD": ord("+"),
            "NUM_SUBTRACT": ord("-"),
            "PAGEUP": pylink.PAGE_UP,
            "PAGEDOWN": pylink.PAGE_DOWN,
        }
        if symbol in key_map:
            return key_map[symbol]
        elif len(symbol) == 1:
            return ord(symbol)
        else:
            return None


if PYLINK_AVAILABLE:

    class _EyeLinkGraphics(pylink.EyeLinkCustomDisplay):
        def __init__(self, runner: "ExperimentRunner", accept_keys: bool):
            super().__init__()
            self.runner = runner
            self.accept_keys = accept_keys

            self.calibration_target = [
                pyglet.shapes.Circle(0, 0, 8, color=(0, 0, 0)),
                pyglet.shapes.Circle(0, 0, 2, color=(255, 255, 255)),
            ]

            self.camera_image_title = pyglet.text.Label(
                "",
                anchor_x="center",
                font_size=20,
                color=(0, 0, 0, 255),
            )
            self.image_scale = 3
            self.image_width = 0
            self.image_height = 0

            self.enabled = False

        def enable(self):
            self.enabled = True

        def disable(self):
            self.enabled = False

        def _camera_image_to_window_coords(self, x: float, y: float):
            x = (
                x * self.image_scale
                + self.runner.display_width / 2
                - self.image_width / 2
            )
            y = (
                -y * self.image_scale
                + self.runner.display_height / 2
                + self.image_height / 2
            )
            return x, y

        def setup_cal_display(self):
            self.clear_cal_display()

        def exit_cal_display(self):
            self.clear_cal_display()

        def record_abort_hide(self):
            pass

        def setup_image_display(self, width, height):
            self.clear_cal_display()
            self.camera_image_data = np.zeros(
                (height // 2, width // 2, 4),
                dtype=np.uint8,
            )

        def image_title(self, title):
            self.camera_image_title.text = title

        def draw_image_line(self, width, line, totlines, buff):
            if not self.enabled:
                return

            for i in range(width):
                if buff[i] < len(self.camera_image_palette):
                    self.camera_image_data[line - 1, i] = self.camera_image_palette[
                        buff[i]
                    ]
                else:
                    self.camera_image_data[line - 1, i] = [0, 0, 0, 0xFF]

            if line == totlines:
                image = pyglet.image.create(width, totlines)
                image.set_data("RGBA", -width * 4, self.camera_image_data.tobytes())

                self.image_width = width * self.image_scale
                self.image_height = totlines * self.image_scale

                self.runner.window.clear()
                image.blit(
                    *self._camera_image_to_window_coords(0, totlines),
                    width=self.image_width,
                    height=self.image_height,
                )
                self.camera_image_title.x, self.camera_image_title.y = (
                    self._camera_image_to_window_coords(width / 2, 0)
                )
                self.camera_image_title.y += 20
                self.draw_cross_hair()
                self.camera_image_title.draw()
                self.runner.window.flip()

        def set_image_palette(self, red, green, blue):
            self.camera_image_palette = np.zeros((len(red), 4), dtype=np.uint8)
            for i in range(len(red)):
                self.camera_image_palette[i] = [red[i], green[i], blue[i], 0xFF]

        def exit_image_display(self):
            self.clear_cal_display()

        def clear_cal_display(self):
            if not self.enabled:
                return

            self.runner.window.clear()
            self.runner.window.flip()

        def erase_cal_target(self):
            self.clear_cal_display()

        def draw_cal_target(self, x, y):
            if not self.enabled:
                return

            self.runner.window.clear()
            y = self.runner.display_height - y
            for shape in self.calibration_target:
                shape.x, shape.y = x, y
                shape.draw()
            self.runner.window.flip()

        def play_beep(self, beepid):
            pass

        def get_input_key(self):
            if not self.enabled or not self.accept_keys:
                return

            self.runner.window.dispatch_events()
            keys = []
            for event in self.runner.event_queue:
                if event.type == "key":
                    symbol = event.data["symbol"]
                    key = self.runner.eyetracker._symbol_to_host_key(symbol)
                    if key is not None:
                        keys.append(pylink.KeyInput(key))
            self.runner.event_queue.clear()
            return keys

        def alert_printf(self, msg):
            pass

        def _get_color(self, colorindex: int) -> tuple[int, int, int]:
            """Convert pylink color index to RGB tuple."""
            return {
                pylink.CR_HAIR_COLOR: (255, 255, 255),
                pylink.PUPIL_HAIR_COLOR: (255, 255, 255),
                pylink.PUPIL_BOX_COLOR: (0, 255, 0),
                pylink.SEARCH_LIMIT_BOX_COLOR: (255, 0, 0),
                pylink.MOUSE_CURSOR_COLOR: (255, 0, 0),
            }.get(colorindex, (0, 0, 0))

        def draw_line(self, x1, y1, x2, y2, colorindex):
            if not self.enabled:
                return

            line = pyglet.shapes.Line(
                *self._camera_image_to_window_coords(x1, y1),
                *self._camera_image_to_window_coords(x2, y2),
                color=self._get_color(colorindex),
                thickness=self.image_scale,
            )
            line.draw()

        def draw_lozenge(self, x, y, width, height, colorindex):
            if not self.enabled:
                return

            rect = pyglet.shapes.Rectangle(
                *self._camera_image_to_window_coords(x - width / 2, y + height / 2),
                width * self.image_scale,
                height * self.image_scale,
                color=self._get_color(colorindex),
            )
            rect.draw()

        def get_mouse_state(self):
            pass
