from __future__ import annotations

import atexit
import json
import shutil
import time
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any

import pyglet

from eidon.run.events import Event
from eidon.run.devices.eyetracker import EyeLink, MouseTracker
from eidon.run.devices.microphone import Microphone
from eidon.run.stages import ExperimentStage
from eidon.setup.setup import HardwareSetup
from eidon.utils import get_package_version, import_custom_code


class ExperimentRunner:
    def __init__(
        self,
        experiment_path: str | Path,
        session_name: str,
        dummy: bool = False,
        participant_control: bool = False,
        recording_name: str | None = None,
        screen: int = 0,
    ):
        self.experiment_path = Path(experiment_path).absolute()
        self.dummy = dummy

        with open(self.experiment_path / "experiment.json") as f:
            experiment_definition = json.load(f)

        with open(self.experiment_path / "sessions" / f"{session_name}.json") as f:
            session_definition = json.load(f)

        # TODO: Raise an error and add a flag to ignore
        if experiment_definition["eidon_version"] != get_package_version():
            warnings.warn(
                f"Experiment was built with eidon version {experiment_definition['eidon_version']}, "
                + f"but you are running version {get_package_version()}. "
                + "This may cause compatibility issues."
            )

        import_custom_code(self.experiment_path)

        setup = HardwareSetup(self.experiment_path)
        if not setup.confirm_setup():
            setup.do_setup()

        self.display_width, self.display_height = experiment_definition["display_size_px"]
        background_color = experiment_definition["background_color"]
        # Convert color to OpenGL's [0, 1] range, add alpha
        background_color = tuple([c / 0xFF for c in background_color] + [1.0])

        if recording_name is None:
            recording_name = f"{experiment_definition['name']}.{session_name}.{time.strftime('%Y%m%d-%H%M%S')}"
        self.recording_name = recording_name
        self.recording_path = (self.experiment_path / "recordings" / recording_name).absolute()
        self.recording_path.mkdir(parents=True, exist_ok=True)

        self.logfile = open(
            self.recording_path / f"{recording_name}.log", "w", encoding="utf-8"
        )

        # copy hardware settings to recording folder
        shutil.copy(setup.last_config_path, self.recording_path)

        self.clock = pyglet.clock.get_default()

        screen = pyglet.display.get_display().get_screens()[screen]
        self.screen_scale = screen.get_scale()
        self.window = pyglet.window.Window(fullscreen=True, screen=screen)
        self.window.set_mouse_visible(False)

        def on_resize(width, height):
            # Set viewport to use display coordinates (centered in the window)
            viewport_x = int((width * self.screen_scale - self.display_width) // 2)
            viewport_y = int((height * self.screen_scale - self.display_height) // 2)
            pyglet.gl.glViewport(
                viewport_x, viewport_y, self.display_width, self.display_height
            )
            self.window.projection = pyglet.math.Mat4.orthogonal_projection(
                0, self.display_width, 0, self.display_height, -1, 1
            )

        self.window._on_internal_resize = on_resize
        self.window.dispatch_events()  # Trigger initial on_resize()

        pyglet.gl.glClearColor(*background_color)
        self.window.clear()

        self.event_queue: list[Event] = []

        def on_key_press(symbol: str, modifiers: int):
            time = self.clock.time()
            symbol = pyglet.window.key.symbol_string(symbol)
            self.event_queue.append(
                Event("key", time, {"symbol": symbol, "modifiers": modifiers})
            )
            return True

        def on_text(text: str):
            time = self.clock.time()
            self.event_queue.append(Event("text", time, {"text": text}))
            return True

        self.window.on_key_press = on_key_press
        self.window.on_text = on_text

        # Initialize eye tracker
        if self.dummy:
            self.eyetracker = MouseTracker(
                self.window,
                origin_x=(self.window.width - self.display_width) // 2,
                origin_y=(self.window.height - self.display_height) // 2,
            )
        else:
            edf_path = self.recording_path / f"{recording_name}.edf"
            eyelink_settings = experiment_definition.get("eyelink_settings")
            self.eyetracker = EyeLink(
                edf_path,
                self,
                participant_control=participant_control,
                settings=eyelink_settings,
            )
        atexit.register(self.eyetracker.save_data)

        # Initialize microphone
        if any(
            stage_data.get("$record_audio")
            for stage_data in session_definition["stages"]
        ):
            self.microphone = Microphone()
        else:
            self.microphone = None

        self.session: list[tuple[ExperimentStage, ExperimentStage | None]] = []

        for stage_data in session_definition["stages"]:
            after_stage_definition = stage_data.pop("$after", None)
            stage = ExperimentStage.from_definition(self, stage_data)
            if after_stage_definition is None:
                # Clear window between stages
                after_stage = None
            elif after_stage_definition == "keep":
                # Keep showing the previous stage
                after_stage = stage
            else:
                # Show intermediate stage
                after_stage = ExperimentStage.from_definition(
                    self, after_stage_definition
                )
            self.session.append((stage, after_stage))

        # Check for duplicate stage names
        stage_names = [stage.name for stage, _ in self.session]
        for name in set(stage_names):
            if stage_names.count(name) > 1:
                raise ValueError(f"Duplicate stage name '{name}' found in session.")

    def run(
        self,
        start_from_stage: str | None = None,
    ):
        session = self.session
        if start_from_stage is not None:
            # Find the stage with the given name
            for i, (stage, _) in enumerate(session):
                if stage.name == start_from_stage:
                    session = session[i:]
                    break
            else:
                raise ValueError(f"Stage '{start_from_stage}' not found in session.")

        for stage, after_stage in session:
            self.eyetracker.send_message(f"TRIALID {stage.name}")
            self.eyetracker.set_backdrop(stage.get_backdrop())

            # Flush event queues
            self.event_queue.clear()
            self.eyetracker.poll_events()
            self.eyetracker.poll_host_events()

            start_time = datetime.now()

            if stage.record_eyes:
                self.eyetracker.send_status_message(stage.name)
                self.eyetracker.start_recording()

            if stage.record_audio:
                audio_path = (
                    self.recording_path / f"{self.recording_name}.{stage.name}.wav"
                )
                relative_audio_path = audio_path.relative_to(self.recording_path)
                self.microphone.start_recording(audio_path)
                self.eyetracker.send_message(f"AUDIO_REC_START {relative_audio_path}")

            stage.start()
            stage_result = self._stage_loop(stage)

            if stage.record_audio:
                self.eyetracker.send_message(f"AUDIO_REC_END {relative_audio_path}")
                self.microphone.stop_recording()

            if stage.record_eyes:
                self.eyetracker.stop_recording()

            end_time = datetime.now()

            self.eyetracker.send_message(f"TRIAL_RESULT {stage.name}")

            # Between stages: clear window, keep previous stage, or show after_stage
            if after_stage is None:
                self.window.clear()
                self.window.flip()
            elif after_stage is stage:
                pass
            else:
                after_stage.start()

            self.logfile.write(
                json.dumps(
                    {
                        "start": start_time.isoformat(),
                        "end": end_time.isoformat(),
                        "stage": stage.name,
                        "result": stage_result,
                    }
                )
                + "\n"
            )
            self.logfile.flush()

    def _stage_loop(self, stage: ExperimentStage) -> dict[str, Any]:
        while True:
            self.clock.tick()

            # Poll user events
            pyglet.app.platform_event_loop.step(0.001)  # TODO: is this needed?
            self.window.dispatch_events()

            # Poll eyetracker events
            # TODO: Only if necessary?
            self.event_queue.extend(self.eyetracker.poll_events())

            # Poll host events
            # TODO: Only if necessary?
            self.event_queue.extend(self.eyetracker.poll_host_events())

            for event in self.event_queue:
                stage.on_event(event)
            self.event_queue.clear()

            if (result := stage.update()) is not None:
                return result
