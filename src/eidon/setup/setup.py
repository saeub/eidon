import json
from datetime import date
from pathlib import Path

import pyglet
import yaml

from eidon.run.events import Event
from eidon.run.devices.eyetracker import EyeLink, MouseTracker
from eidon.run.devices.microphone import Microphone
from eidon.run.stages import ExperimentStage
from eidon.utils import get_package_version, import_custom_code

class HardwareSetup:

    def __init__(self,
                 experiment_path: str | Path | None = None,
                 screen: int = 0):

        self.experiment_path = Path(experiment_path).absolute()

        with open(self.experiment_path / "experiment.json") as f:
            experiment_definition = json.load(f)

        # with open(self.experiment_path / "config.yaml") as f:
        #     config = yaml.safe_load(f)

        self.display_width, self.display_height = experiment_definition["stimulus_area_px"]
        self.margin_px = experiment_definition["margin_px"]

        self.display_width = self.display_width - 2 * self.margin_px
        self.display_height = self.display_height - 2 * self.margin_px

        background_color = (204, 204, 204)
        # Convert color to OpenGL's [0, 1] range, add alpha
        background_color = tuple([c / 0xFF for c in background_color] + [1.0])
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
            self._viewport_x = int((width * self.screen_scale - self.display_width) // 2)
            self._viewport_y = int((height * self.screen_scale - self.display_height) // 2)
            pyglet.gl.glViewport(
                self._viewport_x, self._viewport_y, self.display_width, self.display_height
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

        # TODO: where to put these?
        self.instruction_texts  = {
            "start": "In order to proceed with data collection, the hardware for the experiment needs to be setup and "
                     "measured.\n\nIn general, please read and follow the setup instructions of your eye-tracker manufacturer "
                     "and follow their recommendations!\n\n"
                     "Please set up the eye-tracker and monitor exactly as you will for the experiment. "
                     "You will need a second person who can sit where the participants will be sitting or do "
                     "the setup with a participant. In addition, please prepare a measuring tape."
                     "\n\nWhen you are ready, press [SPACE] to continue.",
            "eye_to_screen_distance_mm": "Seat the participant as they would for an actual experiment.\n\n"
                                         "Using the measuring tape, measure the distance from the participants eyes "
                                         "to the screen in a 90 degrees angle, i.e., in a horizontal line from the eyes "
                                         "to the screen. Note your measurement in millimeters (mm)."
                                         "\n\nPress [SPACE] to continue.",
            "screen_width_mm": "Please measure the WIDTH of the white rectangle (stimulus area) shown on this screen. "
                              "Note your measurement in millimeters (mm)."
                              "\n\nPress [SPACE] when you did so",
            "screen_height_mm": "Please measure the HEIGHT of the white rectangle (stimulus area) shown on this screen. "
                              "Note your measurement in millimeters (mm)."
                              "\n\nPress [SPACE] when you did so.",
            "enter_measurement": "Please enter the measurement in millimeters (mm) as a number (e.g., 605).",
        }

        self.hardware_config = {}
        self.last_config = {}
        self.last_config_path = None
        self.config_folder = self.experiment_path / "hardware_config"

        if not self.config_folder.exists():
            self.config_folder.mkdir(parents=True, exist_ok=True)
        else:
            # get last used config
            all_configs_sorted = sorted(self.config_folder.glob("*.json"))
            last_config = all_configs_sorted[-1]
            self.last_config_path = last_config
            with open(last_config, 'r', encoding='utf8') as f:
                self.last_config = json.load(f)


    def do_setup(self):

        self._show_instruction_text(self.instruction_texts["start"])

        self._show_instruction_text(self.instruction_texts["eye_to_screen_distance_mm"])
        self.hardware_config['eye_to_screen_distance_mm'] = self._get_float_measurement(self.instruction_texts["enter_measurement"])

        self._measure_screen_size(self.instruction_texts["screen_width_mm"])
        self.hardware_config['stimulus_area_width_mm'] = self._get_float_measurement(self.instruction_texts["enter_measurement"])

        self._measure_screen_size(self.instruction_texts["screen_height_mm"])
        self.hardware_config['stimulus_area_height_mm'] = self._get_float_measurement(self.instruction_texts["enter_measurement"])

        if self.confirm_setup():
            self._save_config()
        else:
            self.do_setup()

    def _save_config(self) -> None:

        today = date.today()

        filename = f'hardware_config_{today.strftime("%Y%m%d")}.json'
        config_path = self.config_folder / filename

        vs_tag = 1

        while config_path.exists():
            filename = f'hardware_config_{today.strftime("%Y%m%d")}_v{vs_tag}.json'
            config_path = self.config_folder / filename
            vs_tag += 1

        else:
            # check if the latest config contains the exact same data! If yes, don't write a new version
            if self.last_config != self.hardware_config:
                with open(config_path, 'w') as f:
                    json.dump(self.hardware_config, f, indent=4)
                self.last_config_path = config_path
                self.last_config = self.hardware_config


    def confirm_setup(self) -> bool:

        text = "Please confirm the correctness of these measurements:\n\n"

        if not self.last_config and not self.hardware_config:
            self.do_setup()

        config = self.last_config if not self.hardware_config else self.hardware_config
        for k, v in config.items():
            setting = f'{k}: {v}\n'.replace('_', ' ')
            setting = setting.capitalize()
            text += setting

        batch = pyglet.graphics.Batch()
        text = pyglet.text.Label(
            text=text,
            color=(0, 0, 0),
            font_name='Times New Roman',
            font_size=self.font_size,
            anchor_x='center',
            anchor_y='center',
            x=self.display_width // 2,
            y=self.display_height // 2,
            multiline=True,
            width=self.display_width // 2,
            batch=batch,
        )

        rect = pyglet.shapes.Rectangle(
            x=0,
            y=0,
            width=self.display_width,
            height=self.display_height,
            color=(255, 255, 255),
            batch=batch,
        )

        btn_width, btn_height = 200, 50

        confirm_x = 3 * self.display_width // 4 - btn_width // 2
        change_x  = self.display_width // 4 - btn_width // 2
        btn_y     = self.display_height // 3

        confirm_rect = pyglet.shapes.Rectangle(
            x=confirm_x, y=btn_y,
            width=btn_width, height=btn_height,
            color=(180, 180, 180), batch=batch,
        )

        confirm_label = pyglet.text.Label(
            "Confirm",
            font_name='Times New Roman',
            font_size=self.font_size,
            color=(0, 0, 0, 255),
            anchor_x='center', anchor_y='center',
            x=confirm_x + btn_width // 2,
            y=btn_y + btn_height // 2,
            batch=batch,
        )

        change_rect = pyglet.shapes.Rectangle(
            x=change_x, y=btn_y,
            width=btn_width, height=btn_height,
            color=(180, 180, 180), batch=batch,
        )

        change_label = pyglet.text.Label(
            "Change",
            font_name='Times New Roman',
            font_size=self.font_size,
            color=(0, 0, 0, 255),
            anchor_x='center', anchor_y='center',
            x=change_x + btn_width // 2,
            y=btn_y + btn_height // 2,
            batch=batch,
        )

        results = {}

        def on_mouse_press(mx, my, btn, modifiers):
            # Convert logical window coords to display coords
            dx = int(mx * self.screen_scale) - self._viewport_x
            dy = int(my * self.screen_scale) - self._viewport_y
            if confirm_x <= dx <= confirm_x + btn_width and btn_y <= dy <= btn_y + btn_height:
                results['confirmed'] = True
            elif change_x <= dx <= change_x + btn_width and btn_y <= dy <= btn_y + btn_height:
                results['confirmed'] = False

        self.window.push_handlers(on_mouse_press=on_mouse_press)

        self.window.clear()
        batch.draw()
        self.window.flip()

        while "confirmed" not in results:
            pyglet.app.platform_event_loop.step(0.001)
            self.window.dispatch_events()
            self.window.clear()
            batch.draw()
            self.window.flip()

        self.window.remove_handlers(on_mouse_press=on_mouse_press)

        return results['confirmed']


    def _measure_screen_size(self, text: str):

        batch = pyglet.graphics.Batch()

        rect = pyglet.shapes.Rectangle(
            x=0,
            y=0,
            width=self.display_width,
            height=self.display_height,
            color=(255, 255, 255),
            batch=batch,
        )

        label = pyglet.text.Label(
            text=text,
            color=(0, 0, 0),
            font_name='Times New Roman',
            font_size=self.font_size,
            anchor_x='center',
            anchor_y='center',
            x=self.display_width // 2,
            y=self.display_height // 2,
            multiline=True,
            width=self.display_width // 2,
            batch=batch,
        )

        self.window.clear()
        batch.draw()
        self.window.flip()

        while True:
            pyglet.app.platform_event_loop.step(0.001)
            self.window.dispatch_events()
            for event in self.event_queue:
                if event.type == "key" and event.data["symbol"] == "SPACE":
                    self.event_queue.clear()
                    return

    def _show_instruction_text(self, text: str ):

        text_to_show = pyglet.text.Label(
            text=text,
            color=(0, 0, 0),
            font_name='Times New Roman',
            font_size=self.font_size,
            anchor_x='center',
            anchor_y='center',
            x=self.display_width // 2,
            y=self.display_height // 2,
            multiline=True,
            width=self.display_width,
        )

        self.window.clear()
        text_to_show.draw()
        self.window.flip()

        while True:

            self.clock.tick()

            # Poll user events
            pyglet.app.platform_event_loop.step(0.001)  # TODO: is this needed?
            self.window.dispatch_events()

            for event in self.event_queue:
                if event.type == "key" and event.data["symbol"] == "SPACE":
                    self.event_queue.clear()
                    return


    def _get_float_measurement(self, text: str) -> float:

        batch = pyglet.graphics.Batch()

        _ = pyglet.text.Label(
            text=text,
            color=(0, 0, 0),
            font_name='Times New Roman',
            font_size=self.font_size,
            anchor_x='right',
            anchor_y='center',
            x=self.display_width // 2,
            y=self.display_height // 2,
            multiline=True,
            width=self.display_width // 2.2,
            batch=batch,
        )

        text_entry = pyglet.gui.TextEntry(
            text="",
            x=self.display_width // 2,
            y=self.display_height // 2,
            width=self.display_width // 2,
            batch=batch,

        )

        text_entry._layout.document.set_style(0, len(text_entry.value), {'font_size': self.font_size})
        font = pyglet.font.load(size=self.font_size)
        text_entry.height = font.ascent - font.descent

        text_entry.focus = True
        self.window.push_handlers(text_entry)

        result = {}

        @text_entry.event
        def on_commit(_widget, value):
            result["value"] = value


        self.window.clear()
        batch.draw()
        self.window.flip()

        value = ""
        float_value = 0.0

        while not float_value:
            try:
                float_value = float(value)
                break
            except ValueError:
                text_entry._layout.document.text = ""
                text_entry.focus = True
                while "value" not in result:
                    pyglet.app.platform_event_loop.step(0.001)
                    self.window.dispatch_events()
                    self.window.clear()
                    batch.draw()
                    self.window.flip()
                value = result["value"]
                result.pop("value")


        self.window.remove_handlers(text_entry)
        self.event_queue.clear()

        return float_value









