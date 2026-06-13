from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pyglet

from eidon.run.events import Event

if TYPE_CHECKING:
    from eidon.run.runner import ExperimentRunner


@dataclass
class Backdrop:
    sprite: pyglet.sprite.Sprite
    image_path: Path


class ExperimentStage(ABC):
    """Base class for experiment stages."""

    def __init__(
        self,
        runner: ExperimentRunner,
        name: str,
        record_eyes: bool,
        record_audio: bool,
        data: dict[str, Any],
    ) -> None:
        self.runner = runner
        self.name = name
        self.record_eyes = record_eyes
        self.record_audio = record_audio
        self.init(**data)

    @classmethod
    def get_subclasses(cls) -> dict[str, type[ExperimentStage]]:
        """Recursively collect all subclasses (and subsubclasses etc.) of this class."""
        subclasses = {}
        for subclass in cls.__subclasses__():
            subclasses[subclass.__name__] = subclass
            subclasses.update(subclass.get_subclasses())
        return subclasses

    @classmethod
    def from_definition(
        cls, runner: ExperimentRunner, definition: dict[str, Any]
    ) -> ExperimentStage:
        """Instantiate a stage from a parsed JSON definition."""
        definition = definition.copy()
        stage_types = ExperimentStage.get_subclasses()
        stage_cls = stage_types[definition.pop("$type")]
        name = definition.pop("$name", None)
        if name is None:
            name = f"__unnamed_{stage_cls.__name__}_{random.randrange(16**8):08x}__"
        record_eyes = definition.pop("$record_eyes", False)
        record_audio = definition.pop("$record_audio", False)
        return stage_cls(
            runner=runner,
            name=name,
            record_eyes=record_eyes,
            record_audio=record_audio,
            data=definition,
        )

    @abstractmethod
    def init(self, **data) -> None:
        """
        This method is called when the experiment is initialized.

        This is where stages should load resources and perform any tasks that can be
        done before the experiment starts.

        :param **data:
            The data fields from the stage definition.
        """
        pass

    @abstractmethod
    def start(self) -> None:
        """
        This method is called when the experiment advances to this stage.

        This is where stages should set up their initial state and draw any stimuli
        that should be shown at the beginning of the stage.
        """
        pass

    @abstractmethod
    def on_event(self, event: Event) -> None:
        """
        This method is called when an event is received while this stage is running.

        Stimuli can be drawn in response to events can be done here.

        :param event:
            The event that was received.
        """
        pass

    @abstractmethod
    def update(self) -> dict[str, Any] | None:
        """
        This method is called periodically while this stage is running.

        The method is called after dispatching events. If the stage is not yet finished,
        it should return None. If the stage is finished, it should return a dictionary
        of results (may be empty).

        Returns:
            A dictionary of results if the stage is finished, or None if it is not yet.
        """
        pass

    def get_backdrop(self) -> Backdrop | None:
        """
        Get the backdrop image to show on the host PC during this stage.

        This is also used as the stimulus shown in SR Research's Data Viewer.

        Returns:
            The backdrop to show, or None if no backdrop should be shown.
        """
        return None


class Blank(ExperimentStage):
    """Shows a blank screen."""

    def init(self, continue_key: str):
        """
        :param continue_key:
            The key to press to continue to the next stage.
        """
        self.continue_key = continue_key

    def start(self):
        self.runner.window.clear()
        self.runner.window.flip()
        self.finished = False

    def on_event(self, event: Event):
        if event.type == "key" and event.data["symbol"] == self.continue_key:
            self.finished = True

    def update(self) -> dict[str, Any] | None:
        if self.finished:
            return {}
        return None


class Setup(ExperimentStage):
    """Starts the eye tracker's setup procedure (device-dependent)."""

    def __new__(cls, *args, **kwargs):
        if cls is Setup:
            runner = args[0] if len(args) > 0 else kwargs["runner"]
            return runner.eyetracker.get_setup_stage_type()(*args, **kwargs)
        else:
            return super(Setup, cls).__new__(cls)

    def init(self):
        pass


class DriftCorrect(ExperimentStage):
    """Starts the eye tracker's drift correction procedure (device-dependent)."""

    def __new__(cls, *args, **kwargs):
        if cls is DriftCorrect:
            runner = args[0] if len(args) > 0 else kwargs["runner"]
            return runner.eyetracker.get_drift_correct_stage_type()(*args, **kwargs)
        else:
            return super(DriftCorrect, cls).__new__(cls)

    def init(self, location: tuple[int, int] | None = None):
        """
        :param location:
            The (x, y) location in pixels where the drift correction target should be
            placed. By default, the target is in the center of the screen.
        """
        if location is None:
            location = (
                self.runner.display_width // 2,
                self.runner.display_height // 2,
            )
        self.location = location


class AudioCheck(ExperimentStage):
    """Shows a volume indicator to test the microphone."""

    def init(self):
        assert self.runner.microphone is not None, (
            "Microphone is required for AudioCheck stage"
            " (this probably means that the session does not have any stages that record audio)"
        )
        self.title = pyglet.text.Label(
            text="Audio check",
            x=self.runner.display_width / 2,
            y=self.runner.display_height - 50,
            anchor_x="center",
            anchor_y="center",
            font_size=50,
            color=(0, 0, 0),
        )
        self.volume_indicator = pyglet.shapes.Circle(
            x=self.runner.display_width / 2,
            y=self.runner.display_height / 2,
            radius=0,
            color=(0, 0, 0),
        )

    def start(self):
        self.runner.microphone.start_recording()
        self.finished = False

    def on_event(self, event: Event) -> None:
        # TODO: Make configurable
        if event.type == "key" and event.data["symbol"] == "ESCAPE":
            self.finished = True

    def update(self) -> dict[str, Any] | None:
        volume = self.runner.microphone.file.get_volume()
        self.volume_indicator.radius = volume
        self.runner.window.clear()
        self.volume_indicator.draw()
        self.title.draw()
        self.runner.window.flip()

        if self.finished:
            self.runner.microphone.stop_recording()
            return {}


class HostControlled(ExperimentStage):
    """Disables interaction on the display PC and waits for commands from the host PC."""

    def init(
        self,
        stage: dict[str, Any],
        continue_key: str,
        setup_key: str,
        host_imgpath: str | None = None,
    ):
        """
        :param stage:
            The stage to display while waiting for host input. This stage will not be
            interactive.
        :param continue_key:
            The key that the host PC should send to continue.
        :param setup_key:
            The key that the host PC should send to start the eyetracker setup.
        :param host_imgpath:
            Path to an image file to show on the host PC during this stage. By default,
            the backdrop of the inner stage is shown.
        """
        assert (
            self.record_eyes is False
        ), "In HostControlled stage, eyes cannot be recorded"
        self.stage = ExperimentStage.from_definition(self.runner, stage)
        assert (
            self.stage.record_eyes is False
        ), "In HostControlled stage, eyes cannot be recorded"
        self.continue_key = continue_key
        self.setup_key = setup_key
        if host_imgpath is not None:
            host_imgpath = (self.runner.experiment_path / host_imgpath).absolute()
            img = pyglet.image.load(host_imgpath)
            self._backdrop = Backdrop(
                pyglet.sprite.Sprite(img, x=0, y=self.runner.display_height - img.height),
                host_imgpath,
            )
        else:
            self._backdrop = None

        self._setup_stage = None

    def start(self):
        self.finished = False
        if self.runner.dummy and self._backdrop is not None:
            # In dummy mode, prefer drawing host image
            self.runner.window.clear()
            self._backdrop.sprite.draw()
            self.runner.window.flip()
        else:
            self.stage.start()

    def on_event(self, event: Event) -> None:
        if self._setup_stage is not None:
            self._setup_stage.on_event(event)
            return

        if (self.runner.dummy and event.type == "key") or (
            not self.runner.dummy and event.type == "hostkey"
        ):
            if event.data["symbol"] == self.continue_key:
                self.finished = True
            elif event.data["symbol"] == self.setup_key:
                self._setup_stage = Setup(self.runner, "", False, False, {})
                self._setup_stage.start()

    def update(self) -> dict[str, Any] | None:
        if not self.runner.dummy or self._backdrop is None:
            self.stage.update()

        if self.finished:
            return {}

        if self._setup_stage is not None:
            setup_done = self._setup_stage.update() is not None
            if setup_done:
                self._setup_stage = None
                if self.runner.dummy and self._backdrop is not None:
                    # In dummy mode, prefer drawing host image
                    self.runner.window.clear()
                    self._backdrop.sprite.draw()
                    self.runner.window.flip()
                else:
                    self.stage.start()
                # TODO: Flush eyetracker events?

    def get_backdrop(self) -> Backdrop | None:
        if self._backdrop is not None:
            return self._backdrop
        return self.stage.get_backdrop()


class StimulusPage(ExperimentStage):
    """Shows a single image stimulus."""

    def init(self, imgpath: str, continue_key: str, min_duration: float = 0.5):
        """
        :param imgpath:
            Path to the image file to display, relative to the experiment's root directory.
        :param continue_key:
            The key to press to continue to the next stage.
        :param min_duration:
            Minimum duration in seconds to display the stimulus before allowing continuation.
            Default is 0.5 seconds to prevent accidentally skipping the stimulus.
        """
        imgpath = (self.runner.experiment_path / imgpath).absolute()
        img = pyglet.image.load(imgpath)
        self.stimulus = pyglet.sprite.Sprite(
            img, x=0, y=self.runner.display_height - img.height
        )
        self._backdrop = Backdrop(self.stimulus, imgpath)

        self.continue_key = continue_key
        self.min_duration = min_duration

    def start(self):
        self.finished = False

        self.runner.window.clear()
        self.stimulus.draw()
        self.runner.window.flip()

        self.start_time = self.runner.clock.time()

    def on_event(self, event: Event):
        # Block events until the minimum duration has passed
        if self.runner.clock.time() - self.start_time < self.min_duration:
            return

        if event.type == "key" and event.data["symbol"] == self.continue_key:
            self.finished = True

    def update(self):
        if self.finished:
            return {}

    def get_backdrop(self) -> Backdrop:
        return self._backdrop


class StimulusMultiPage(ExperimentStage):
    """Shows multiple image stimuli that can be navigated."""

    def init(
        self,
        imgpaths: list[str],
        next_page_key: str,
        prev_page_key: str | None = None,
        min_duration: float = 0.5,
    ):
        """
        :param imgpaths:
            A list of paths to the image files to display, relative to the experiment's
            root directory.
        :param next_page_key:
            The key to press to go to the next page.
        :param prev_page_key:
            The key to press to go to the previous page. By default, going to the
            previous page is disabled.
        :param min_duration:
            Minimum duration in seconds to display each page before allowing navigation.
            Default is 0.5 seconds to prevent accidentally skipping pages.
        """
        imgpaths = [
            (self.runner.experiment_path / imgpath).absolute() for imgpath in imgpaths
        ]
        imgs = [pyglet.image.load(imgpath) for imgpath in imgpaths]
        self.stimuli = [
            pyglet.sprite.Sprite(img, x=0, y=self.runner.display_height - img.height)
            for img in imgs
        ]
        self.page_index = 0

        self._backdrop = Backdrop(
            self.stimuli[self.page_index], imgpaths[self.page_index]
        )

        self.page_next_key = next_page_key
        self.page_prev_key = prev_page_key

        self.min_duration = min_duration

    def start(self):
        self.finished = False

        self.runner.eyetracker.send_message(f"PAGE {self.page_index}")
        self.runner.window.clear()
        self.stimuli[self.page_index].draw()
        self.runner.window.flip()

        self.start_time = self.runner.clock.time()

    def on_event(self, event: Event):
        # Block events until the minimum duration has passed
        if self.runner.clock.time() - self.start_time < self.min_duration:
            return

        if event.type != "key":
            return

        # TODO: Log key presses
        if event.data["symbol"] == self.page_next_key:
            self.page_index += 1
            if self.page_index >= len(self.stimuli):
                self.finished = True
                return
            self.start_time = self.runner.clock.time()

        elif (
            self.page_prev_key is not None
            and event.data["symbol"] == self.page_prev_key
        ):
            self.page_index -= 1
            if self.page_index < 0:
                self.page_index = 0
            self.start_time = self.runner.clock.time()

        self.runner.eyetracker.send_message(f"PAGE {self.page_index}")
        self.runner.window.clear()
        self.stimuli[self.page_index].draw()
        self.runner.window.flip()

    def update(self):
        if self.finished:
            return {}

    def get_backdrop(self) -> pyglet.sprite.Sprite:
        return self._backdrop


class MultipleChoiceQuestion(ExperimentStage):
    """Shows an image stimulus and allows selecting a response option by pressing a key."""

    def init(
        self,
        imgpath: str,
        option_keys: list[str],
        option_values: list[str] | None = None,
        correct_option_index: int | None = None,
        option_boxes: list[tuple[float, float, float, float]] | None = None,
        confirm_key: str | None = None,
    ):
        """
        :param imgpath:
            Path to the image file to display, relative to the experiment's root directory.
        :param option_keys:
            The keys to select each answer option.
        :param option_values:
            The values for each answer option that will be returned and logged.
            By default, the option indices are used as values.
        :param correct_option_index:
            The index of the correct answer option.
            This does not affect the presentation, but is logged for convenience.
        :param option_boxes:
            A list of rectangles (x, y, width, height) in pixels defining the location of each
            answer options on the stimulus image. When `confirm_key` is provided, this is used to
            show a box around the currently selected option.
        :param confirm_key:
            The key to press to confirm the selected answer option. If not provided, the answer
            is confirmed immediately when an option key is pressed. Requires `option_boxes` to be
            defined.
        """
        imgpath = (self.runner.experiment_path / imgpath).absolute()
        img = pyglet.image.load(imgpath)
        self.stimulus = pyglet.sprite.Sprite(img, x=0, y=self.runner.display_height - img.height)

        self._backdrop = Backdrop(self.stimulus, imgpath)

        self.option_values = option_values
        self.option_keys = option_keys
        self.confirm_key = confirm_key
        self.option_boxes = None
        if self.option_values is not None:
            assert len(self.option_values) == len(
                self.option_keys
            ), "option_values must have the same length as option_keys"
        self.correct_option_index = correct_option_index
        if self.correct_option_index is not None:
            assert (
                0 <= self.correct_option_index < len(self.option_keys)
            ), "correct_option_index must be a valid index in option_keys"
        if self.confirm_key is not None:
            assert option_boxes is not None, "option_boxes must be defined if confirm_key is used"
            assert len(option_boxes) == len(
                self.option_keys
            ), "option_boxes must have the same length as option_keys"
            self.option_boxes = [
                pyglet.shapes.Box(
                    x, self.runner.display_height - y - height, width, height, color=(0, 0, 0), thickness=2
                )
                for x, y, width, height in option_boxes
            ]

    def start(self) -> dict[str, Any]:
        self.selected_option_index = None
        self.confirmed = False

        self.runner.window.clear()
        self.stimulus.draw()
        self.runner.window.flip()

    def on_event(self, event: Event):
        if event.type != "key":
            return

        # Select answer
        if event.data["symbol"] in self.option_keys:
            self.selected_option_index = self.option_keys.index(event.data["symbol"])
            if self.option_boxes is not None:
                self.runner.window.clear()
                self.stimulus.draw()
                for i, box in enumerate(self.option_boxes):
                    if i == self.selected_option_index:
                        box.draw()
                self.runner.window.flip()

        # Confirm answer
        if self.confirm_key is not None and event.data["symbol"] == self.confirm_key:
            if self.selected_option_index is not None:
                self.confirmed = True

    def update(self) -> dict[str, Any] | None:
        if self.confirm_key is not None and not self.confirmed:
            return
        if self.selected_option_index is not None:
            response = self.selected_option_index
            if self.option_values is not None:
                response = self.option_values[self.selected_option_index]
            data = {"response": response}
            if self.correct_option_index is not None:
                data["correct_response"] = (
                    self.option_values[self.correct_option_index]
                    if self.option_values is not None
                    else self.correct_option_index
                )
            return data

    def get_backdrop(self) -> pyglet.sprite.Sprite | None:
        return self._backdrop


class CursorMultipleChoiceQuestion(ExperimentStage):
    """Shows an image stimulus and allows selecting a response option by moving a cursor."""

    def init(
        self,
        imgpath: str,
        cursor_locations: list[tuple[float, float]],
        cursor_size: float,
        next_option_key: str,
        prev_option_key: str,
        confirm_key: str,
        option_values: list[str] | None = None,
    ):
        """
        :param imgpath:
            Path to the image file to display, relative to the experiment's root directory.
        :param cursor_locations:
            A list of (x, y) locations in pixels for the cursor positions of each answer option.
        :param cursor_size:
            The diameter of the cursor in pixels.
        :param next_option_key:
            The key that moves the cursor to the next option.
        :param prev_option_key:
            The key that moves the cursor to the previous option.
        :param confirm_key:
            The key that confirms the current selection.
        :param option_values:
            The values for each answer option that will be returned and logged.
            By default, the option indices are used as values.
        """
        imgpath = (self.runner.experiment_path / imgpath).absolute()
        img = pyglet.image.load(imgpath)
        self.stimulus = pyglet.sprite.Sprite(img, x=0, y=self.runner.display_height - img.height)

        self._backdrop = Backdrop(self.stimulus, imgpath)

        self.cursor_locations = [
            (x, self.runner.display_height - y) for x, y in cursor_locations
        ]
        self.cursor = pyglet.shapes.Circle(
            0, 0, radius=cursor_size / 2, color=(0, 0, 0)
        )
        self.cursor_index = -1

        self.prev_option_key = prev_option_key
        self.next_option_key = next_option_key
        self.confirm_key = confirm_key

        self.option_values = option_values
        if self.option_values is not None:
            assert len(self.option_values) == len(
                self.cursor_locations
            ), "option_values must have the same length as cursor_locations"

    def start(self) -> dict[str, Any]:
        self.finished = False

        self.runner.window.clear()
        self.stimulus.draw()
        self.runner.window.flip()

    def on_event(self, event: Event):
        if event.type != "key":
            return

        cursor_moved = False

        # Confirm answer
        if event.data["symbol"] == self.confirm_key:
            if self.cursor_index == -1:
                return
            self.finished = True

        # Move cursor
        elif event.data["symbol"] == self.prev_option_key:
            self.cursor_index -= 1
            if self.cursor_index < 0:
                self.cursor_index = len(self.cursor_locations) - 1
            cursor_moved = True
        elif event.data["symbol"] == self.next_option_key:
            self.cursor_index += 1
            if self.cursor_index >= len(self.cursor_locations):
                self.cursor_index = 0
            cursor_moved = True

        if cursor_moved:
            self.cursor.position = self.cursor_locations[self.cursor_index]
            self.runner.window.clear()
            self.stimulus.draw()
            self.cursor.draw()
            self.runner.window.flip()

    def update(self) -> dict[str, Any] | None:
        if self.finished:
            response = self.cursor_index
            if self.option_values is not None:
                response = self.option_values[self.cursor_index]
            data = {"response": response}
            if self.correct_option_index is not None:
                data["correct_response"] = (
                    self.option_values[self.correct_option_index]
                    if self.option_values is not None
                    else self.correct_option_index
                )
            return data

    def get_backdrop(self) -> pyglet.sprite.Sprite | None:
        return self._backdrop


class FreeTextQuestion(ExperimentStage):
    """Shows an image stimulus and allows entering a free text response."""

    # TODO: Customize font
    def init(
        self,
        imgpath: str,
        input_box: tuple[float, float, float, float],
        font_size: int,
        confirm_key: str,
        multiline: bool = False,
    ):
        """
        :param imgpath:
            Path to the image file to display, relative to the experiment's root directory.
        :param input_box:
            A rectangle (x, y, width, height) in pixels defining the location of the text input box.
        :param confirm_key:
            The key to press to confirm the entered text.
        """
        imgpath = (self.runner.experiment_path / imgpath).absolute()
        img = pyglet.image.load(imgpath)
        self.stimulus = pyglet.sprite.Sprite(img, x=0, y=self.runner.display_height - img.height)
        self._backdrop = Backdrop(self.stimulus, imgpath)

        self.confirm_key = confirm_key

        x, y, width, height = input_box
        y = self.runner.display_height - y - height  # Invert y-axis
        self.input_box = pyglet.shapes.Box(
            x, y, width, height, color=(0, 0, 0), thickness=2
        )

        self.text = ""
        margin = 5
        self.label = pyglet.text.Label(
            text=self.text,
            x=x + margin,
            y=y + height - margin,
            anchor_y="top",
            width=width - 2 * margin,
            height=height - 2 * margin,
            font_size=font_size,  # TODO: Convert pt to px
            color=(0, 0, 0, 255),
            multiline=multiline,
        )

    def start(self) -> dict[str, Any]:
        self.finished = False

        self.runner.window.clear()
        self.stimulus.draw()
        self.input_box.draw()
        self.label.draw()
        self.runner.window.flip()

    def on_event(self, event: Event):
        if event.type not in ["key", "text"]:
            return

        # TODO: Use proper text editor (arrow keys, mouse clicks, etc.)
        if event.type == "key":
            symbol = event.data["symbol"]
            if symbol == self.confirm_key:
                if self.text.strip() == "":
                    return
                self.finished = True
            elif symbol == "BACKSPACE":
                self.text = self.text[:-1]
        else:  # event.type == "text"
            self.text += event.data["text"]
        self.label.text = self.text

        self.runner.window.clear()
        self.stimulus.draw()
        self.input_box.draw()
        self.label.draw()
        self.runner.window.flip()

    def update(self) -> dict[str, Any] | None:
        if self.finished:
            return {"response": self.text}

    def get_backdrop(self) -> pyglet.sprite.Sprite | None:
        return self._backdrop


class LabelAnnotation(ExperimentStage):
    """Shows an image stimulus and allows selecting a label."""

    def init(
        self,
        imgpath: str,
        label_boxes: dict[str, tuple[float, float, float, float]],
        label_keys: dict[str, str],
        confirm_key: str,
    ):
        """
        :param imgpath:
            Path to the image file to display, relative to the experiment's root directory.
        :param label_boxes:
            An object mapping label names to rectangles (x, y, width, height) in pixels
            where the labels are located.
        :param label_keys:
            An object mapping keys to label names.
        :param confirm_key:
            The key to press to confirm the selected label.
        """
        imgpath = (self.runner.experiment_path / imgpath).absolute()
        img = pyglet.image.load(imgpath)
        self.stimulus = pyglet.sprite.Sprite(img, x=0, y=self.runner.display_height - img.height)
        self._backdrop = Backdrop(self.stimulus, imgpath)

        self.label_keys = label_keys
        self.confirm_key = confirm_key

        assert all(
            label in label_boxes for label in label_keys.values()
        ), "label_boxes must contain an entry for each label in label_keys"
        self.label_boxes = {}
        for label, box in label_boxes.items():
            x, y, width, height = box
            y = self.runner.display_height - y - height  # Invert y-axis
            # TODO: Make configurable
            self.label_boxes[label] = pyglet.shapes.Box(
                x, y, width, height, color=(0, 0, 0), thickness=2
            )

        self.selected_label = None

    def start(self) -> dict[str, Any]:
        self.finished = False

        self.runner.window.clear()
        self.stimulus.draw()
        self.runner.window.flip()

    def on_event(self, event: Event):
        # TODO: Accept any kind of event (e.g., button box)
        if event.type != "key":
            return

        if event.data["symbol"] in self.label_keys:
            self.selected_label = self.label_keys[event.data["symbol"]]
            self.runner.eyetracker.send_message(f"LABEL_SELECTED {self.selected_label}")
            self.runner.window.clear()
            self.stimulus.draw()
            self.label_boxes[self.selected_label].draw()
            self.runner.window.flip()

        elif (
            event.data["symbol"] == self.confirm_key and self.selected_label is not None
        ):
            self.runner.eyetracker.send_message(
                f"LABEL_CONFIRMED {self.selected_label}"
            )
            self.finished = True

    def update(self) -> dict[str, Any] | None:
        if self.finished:
            return {"response": self.selected_label}

    def get_backdrop(self) -> pyglet.sprite.Sprite | None:
        return self._backdrop


class QuestionTree(ExperimentStage):
    """Shows a series of question stages, where each stage is based on previous responses."""

    def init(
        self,
        tree: dict[str, Any],
    ):
        """
        :param tree:
            A nested object defining the question tree, for example:
            {
                "$type": "MultipleChoiceQuestion",
                "imgpath": ...,
                "branches": {
                    "0": { "$type": "FreeTextQuestion", ..., "branches": { ... } },
                    "1": { "$type": "MultipleChoiceQuestion", ..., "branches": { ... } },
                    ...
                }
            }
        """
        tree = tree.copy()
        self.branches = tree.pop("branches", {})
        self.stage = ExperimentStage.from_definition(self.runner, tree)
        self.results = []

    def start(self):
        self.finished = False

        self.stage.start()

    def on_event(self, event: Event):
        self.stage.on_event(event)

    def update(self) -> dict[str, Any] | None:
        result = self.stage.update()
        if result is not None:
            result["$name"] = self.stage.name
            self.results.append(result)
            if "response" in result:
                response = str(result["response"])
                if response in self.branches:
                    # Start next stage based on response
                    subtree = self.branches[response]
                    self.branches = subtree.pop("branches", {})
                    # TODO: Pre-initialize (or at least check) all stages in init(),
                    # to avoid errors after the experiment has started
                    self.stage = ExperimentStage.from_definition(self.runner, subtree)
                    self.stage.start()
                elif "*" in self.branches:
                    # No branch for this response -> use default branch
                    subtree = self.branches["*"]
                    self.branches = subtree.pop("branches", {})
                    self.stage = ExperimentStage.from_definition(self.runner, subtree)
                    self.stage.start()
                else:
                    # No default branch -> finish
                    self.finished = True
            else:
                # No response returned by stage -> finish
                self.finished = True

        if self.finished:
            return {"results": self.results}


class FixationCross(ExperimentStage):
    """Shows a fixation cross/trigger."""

    def init(
        self,
        location: tuple[float, float],
        fixation_trigger: bool = False,
        tolerance: float = 20,
        timeout: float = 0,
    ):
        """
        :param location:
            The (x, y) location of the fixation cross in pixels. (0, 0) = top left.
        :param fixation_trigger:
            Whether to wait for the participant to fixate on the cross before continuing.
        :param tolerance:
            The radius in pixels around the fixation cross that counts as a fixation.
            Default is 20 pixels.
        :param timeout:
            Maximum time in seconds to wait for fixation before continuing anyway.
            Set to 0 to wait indefinitely (default).
        """
        self.x, self.y = location
        self.fixation_trigger = fixation_trigger
        self.tolerance = tolerance
        self.timeout = timeout
        cross_x = self.x
        cross_y = self.runner.display_height - self.y  # Invert y-axis
        self.hline = pyglet.shapes.Line(
            cross_x - 10,
            cross_y,
            cross_x + 10,
            cross_y,
            thickness=2,
            color=(0, 0, 0),
        )
        self.vline = pyglet.shapes.Line(
            cross_x,
            cross_y - 10,
            cross_x,
            cross_y + 10,
            thickness=2,
            color=(0, 0, 0),
        )

    def start(self):
        self.finished = False
        self.fixation_location = None
        self.start_time = self.runner.clock.time()

        self.runner.window.clear()
        self.hline.draw()
        self.vline.draw()
        self.runner.window.flip()

    def on_event(self, event: Event):
        if not self.fixation_trigger or event.type != "fixation":
            return

        gaze_x = event.data["x"]
        gaze_y = event.data["y"]
        if (gaze_x - self.x) ** 2 + (gaze_y - self.y) ** 2 <= self.tolerance**2:
            self.finished = True
            self.fixaiton_location = (gaze_x, gaze_y)

    def update(self) -> dict[str, Any] | None:
        # FIXME
        if self.timeout > 0:
            if self.runner.clock.time() - self.start_time >= self.timeout:
                self.finished = True

        if self.finished:
            return {"fixation_location": self.fixation_location}
