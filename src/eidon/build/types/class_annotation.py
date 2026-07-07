from collections import defaultdict
import csv
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import warnings

from eidon.build import ExperimentType, stimuli
from eidon.fonts import FONTS


@dataclass(kw_only=True)
class ClassAnnotation(ExperimentType):
    """
    Annotation experiment for text classification.

    Each annotation item consists of a text and optionally one or more multiple-choice questions
    (e.g., confidence ratings). Every annotator annotates the same set of items, and the order of
    items is randomized for each participant.

    ### Required materials

    ```
    📂 my_experiment
    ├─ config.yaml
    └─ 📂 materials
       ├─ 📄 instructions.txt
       ├─ 📄 wait.txt (optional)
       ├─ 📄 break.txt (optional)
       ├─ 📄 end.txt
       └─ 📂 items
          ├─ 📄 01.txt
          ├─ 📄 02.txt
          ├─ 📄 03.txt
          ├─ 📄 ...
          ├─ 📄 practice.01.txt (optional)
          └─ 📄 practice.02.txt (optional)
          ├─ 📄 ...
    ```

    - `instructions.txt` contains the text for the instructions shown at the beginning of the experiment.
      The text is automatically split into multiple pages if necessary.
    - `wait.txt` (optional) contains the text shown after the instructions and after the practice trials,
      where the participant waits for the experimenter to start the experiment. This is an opportunity
      for the participant to ask questions or for the experimenter to perform calibration if necessary.
    - `break.txt` (optional) contains the text shown during breaks.
    - `end.txt` contains the text shown at the end of the experiment.

    #### Annotation items

    `01.txt`, `02.txt`, etc. each represent one item to be annotated. The file names (without `.txt`)
    are used as item IDs. Each file contains the text to be annotated.

    #### Practice items

    Practice items are optional and follow the same format as regular items. File names of practice
    items must start with `practice.` (e.g., `practice.01.txt`).

    #### Areas of interest

    Areas of interest can be defined in the text by surrounding them with
    [[area-name]]...[[/area-name]]. For example:

    ```
    [[subject]]The quick brown fox[[/subject]] jumps over [[object]]the lazy dog[[/object]].
    ```

    An item can contain any number of areas of interest. Discontinuous areas can be defined by
    using multiple tags with the same area name.

    #### Questions

    Multiple-choice questions are optional and can be defined in `config.yaml`. The questions
    are presented after a label has been selected. The questions are the same for every item.
    See [Configuration](#configuration) below for details. For example:

    ```yaml
    questions:
      - stem: "How confident are you in your label choice?"
        options:
          - "Very confident"
          - "Somewhat confident"
          - "Not confident at all"
      - stem: "Which label would be your second choice?"
        options:
        - ...
    ```

    :param num_participants: Number of participants in the experiment.
        Should be a multiple of the number of conditions.
    :param breaks_after: Insert a break after every N items.
    :param margin: Margin in pixels around the text on the stimulus pages.
    :param font_monospaced: Whether to use a monospaced font for the stimuli.
        This is recommended when controlling for word length effects.
    :param font_size: Font size for all text.
    :param line_spacing: Line spacing multiplier for all text.
    :param labels: Names of the labels to choose from.
    :param label_texts: Texts to display for each label. If not provided, the label names are used.
    :param label_option_keys: List of keys to use for selecting a label, in order.
        For example, `[Y, N]` to use the Y key for the first label and the N key for the second
        label.
    :param questions: List of multiple-choice questions to present after selecting a label.
        See [example above](#questions) for details.
    :param question_layout: Layout for multiple-choice questions.
        `horizontal` arranges options in a horizontal row, `diamond` arranges them in a diamond
        shape (requires exactly 4 options that are selected with the UP, LEFT, RIGHT, and DOWN
        keys), and `cursor` arranges them vertically with a visual selector that can be controlled
        with the UP and DOWN keys (requires `question_confirm_key`).
    :param question_option_keys: List of keys to use for selecting multiple-choice options, in order.
        For example, `[Y, N]` to use the Y key for the first option and the N key for the second
        option. Only required when question layout is `horizontal`.
    :param question_confirm_key: Key to use for confirming the selection of an option.
        If not specified, options are selected immediately when the corresponding option key is
        pressed.
    """

    num_participants: int
    breaks_after: int | None = None
    margin: int = 50
    font_monospaced: bool = False
    font_size: int = 25
    line_spacing: int = 2.0
    labels: list[str]
    label_texts: list[str] | None = None
    label_option_keys: list[str] | None
    label_confirm_key: str | None = None
    questions: list[dict[str, Any]] | None = None
    question_layout: str = "cursor"
    question_option_keys: list[str] | None = None
    question_confirm_key: str | None = "SPACE"

    def build(self, experiment_path: Path) -> dict[str, dict[str, Any]]:
        if self.questions is None:
            self.questions = []

        if self.question_layout == "horizontal":
            if self.question_option_keys is None:
                raise ValueError(
                    "option_keys must be provided for horizontal question layout."
                )
        elif self.question_layout == "diamond":
            if self.question_option_keys is None:
                self.question_option_keys = ["UP", "LEFT", "RIGHT", "DOWN"]
            if len(self.question_option_keys) != 4:
                raise ValueError(
                    "Exactly 4 option keys must be provided for diamond layout "
                    "(to select top/left/right/bottom option)."
                )
        elif self.question_layout == "cursor":
            if self.question_option_keys is None:
                self.question_option_keys = ["UP", "DOWN"]
            if len(self.question_option_keys) != 2:
                raise ValueError(
                    "Exactly 2 option keys must be provided for cursor layout "
                    "(to move cursor up and down)."
                )
            if self.question_confirm_key is None:
                raise ValueError("A confirm key must be provided for cursor layout.")

        if self.font_monospaced:
            font_path = FONTS["monospace"]
        else:
            font_path = FONTS["default"]

        text_config = {
            "width": self.display_size[0],
            "height": self.display_size[1],
            "margin": self.margin,
            "font_path": font_path,
            "font_size": self.font_size,
            "line_spacing": self.line_spacing,
            "background_color": self.background_color,
            "vertical_align": "center",
        }

        instructions_stage = self._generate_instructions_stage(
            experiment_path, text_config
        )
        end_stage = self._generate_end_stage(experiment_path, text_config)
        wait_stage = self._generate_wait_stage(experiment_path, text_config)
        if self.breaks_after is not None:
            break_stage = self._generate_break_stage(experiment_path, text_config)

        experimental_items, practice_items = self._parse_items(experiment_path)
        annotation_stages = self._generate_annotation_stages(
            experimental_items,
            practice_items,
            experiment_path,
            text_config,
        )

        question_stages = self._generate_question_stages(
            experiment_path,
            text_config,
        )

        assignments = self._build_item_assignments(experimental_items)
        # Save assignment table for convenience
        with open(experiment_path / "sessions" / "assignments.csv", "w") as f:
            csv_writer = csv.writer(f)
            for participant_id in assignments:
                csv_writer.writerow([participant_id] + assignments[participant_id])

        # Create sessions
        sessions = {}
        for participant_id, assignment in assignments.items():
            practice_stages = []
            if len(practice_items) > 0:
                for name in practice_items:
                    practice_stages.extend(annotation_stages[name])
                    for question_stage in question_stages:
                        practice_stages.append(
                            question_stage
                            | {"$name": f"{name}.{question_stage['$name']}"}
                        )
                practice_stages.append(wait_stage | {"$name": "wait.practice"})

            item_stages = []
            for i, name in enumerate(assignment):
                if (
                    self.breaks_after is not None
                    and i > 0
                    and i % self.breaks_after == 0
                ):
                    item_stages.append(break_stage | {"$name": f"break.{i}"})
                item_stages.extend(annotation_stages[name])
                for question_stage in question_stages:
                    item_stages.append(
                        question_stage | {"$name": f"{name}.{question_stage['$name']}"}
                    )

            session = {
                "stages": [
                    {"$name": "setup", "$type": "Setup"},
                    instructions_stage,
                    wait_stage,
                    *practice_stages,
                    *item_stages,
                    end_stage,
                ]
            }
            sessions[participant_id] = session

        return sessions

    def _parse_items(
        self, experiment_path: Path
    ) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
        experimental_items = {}
        practice_items = {}
        for item_path in (experiment_path / "materials" / "items").glob("*.txt"):
            item_text = item_path.read_text(encoding="utf8")
            item_text, custom_area_spans = self._parse_area_spans(item_text)
            item = {"text": item_text, "custom_area_spans": custom_area_spans}
            if item_path.name.startswith("practice."):
                practice_items[item_path.stem] = item
            else:
                experimental_items[f"item.{item_path.stem}"] = item
        if len(experimental_items) == 0:
            warnings.warn(
                f"No experimental items found in {experiment_path / 'materials' / 'items'}."
            )
        return experimental_items, practice_items

    def _parse_area_spans(
        self, text: str
    ) -> tuple[str, dict[str, list[tuple[int, int]]]]:
        """Extract custom area spans from text with tags like [[area_type]]...[[/area_type]]."""
        area_spans = defaultdict(list)
        tag_pattern = re.compile(r"\[\[([^\]]+)\]\](.*?)\[\[/\1\]\]")
        clean_text = ""
        last_index = 0

        for match in tag_pattern.finditer(text):
            area_type, span_text = match.groups()
            clean_start_index = len(clean_text) + (match.start() - last_index)
            clean_end_index = clean_start_index + len(span_text)
            area_spans[area_type].append((clean_start_index, clean_end_index))
            clean_text += text[last_index : match.start()] + span_text
            last_index = match.end()

        clean_text += text[last_index:]
        return clean_text, dict(area_spans)

    def _generate_instructions_stage(
        self, experiment_path: Path, text_config: dict[str, Any]
    ) -> dict[str, Any]:
        text = (
            (experiment_path / "materials" / "instructions.txt")
            .read_text(encoding="utf8")
            .strip()
        )
        # TODO: Allow manual page breaks
        images = stimuli.generate_text_pages(text, **text_config)
        for i, image in enumerate(images):
            image.save(experiment_path, f"instructions.{i}")
        return {
            "$type": "StimulusMultiPage",
            "$name": "instructions",
            "$record_eyes": True,
            "imgpaths": [image.imgpath for image in images],
            "next_page_key": "SPACE",
        }

    def _generate_end_stage(
        self, experiment_path: Path, text_config: dict[str, Any]
    ) -> dict[str, Any]:
        text = (
            (experiment_path / "materials" / "end.txt")
            .read_text(encoding="utf8")
            .strip()
        )
        (image,) = stimuli.generate_text_pages(
            text,
            **text_config,
        )
        image.save(experiment_path, "end")
        return {
            "$type": "StimulusPage",
            "$name": "end",
            "imgpath": image.imgpath,
            "continue_key": "SPACE",
        }

    def _generate_wait_stage(
        self,
        experiment_path: Path,
        text_config: dict[str, Any],
    ) -> dict[str, Any]:
        participant_text = ""
        if (experiment_path / "materials" / "wait.txt").exists():
            participant_text = (
                (experiment_path / "materials" / "wait.txt")
                .read_text(encoding="utf8")
                .strip()
            )
        (participant_image,) = stimuli.generate_text_pages(
            participant_text,
            **text_config,
        )
        participant_image.save(experiment_path, "wait.participant")
        (host_image,) = stimuli.generate_text_pages(
            "[SPACE] Setup\n[ESC] Continue",
            **text_config,
        )
        host_image.save(experiment_path, "wait.host")
        return {
            "$name": "wait",
            "$type": "HostControlled",
            "continue_key": "ESCAPE",
            "setup_key": "SPACE",
            "stage": {
                "$type": "StimulusPage",
                "imgpath": participant_image.imgpath,
                "continue_key": "SPACE",
            },
            "host_imgpath": host_image.imgpath,
        }

    def _generate_break_stage(
        self,
        experiment_path: Path,
        text_config: dict[str, Any],
    ) -> dict[str, Any]:
        text = (
            (experiment_path / "materials" / "break.txt")
            .read_text(encoding="utf8")
            .strip()
        )
        (image,) = stimuli.generate_text_pages(
            text,
            **text_config,
        )
        image.save(experiment_path, "break")
        return {
            "$type": "HostControlled",
            "continue_key": "ESCAPE",
            "setup_key": "SPACE",
            "stage": {
                "$type": "StimulusPage",
                "imgpath": image.imgpath,
                "continue_key": "SPACE",
            },
            "host_imgpath": "stimuli/wait.host.png",
        }

    def _generate_annotation_stages(
        self,
        experimental_items: dict[str, dict[str, Any]],
        practice_items: dict[str, dict[str, Any]],
        experiment_path: Path,
        text_config: dict[str, Any],
    ) -> dict[str, list[dict[str, Any]]]:
        stimulus_stages = {}
        for item_id, item in list(experimental_items.items()) + list(
            practice_items.items()
        ):
            anno_image = stimuli.generate_label_annotation_page(
                item["text"],
                self.labels,
                label_texts=self.label_texts,
                custom_area_spans=item["custom_area_spans"],
                **text_config,
            )
            for area_type in item["custom_area_spans"]:
                if any(area.continued for area in anno_image.areas[area_type]):
                    warnings.warn(
                        f"Area '{area_type}' in item {item_id} crosses line boundaries."
                    )
            anno_image.save(experiment_path, f"{item_id}.anno")
            text_start_location = (
                int(anno_image.areas["section"][0].left - self.font_size),
                int(
                    anno_image.areas["section"][0].top
                    + self.font_size * self.line_spacing / 2
                ),
            )

            stages = [
                {
                    "$name": f"{item_id}.drift",
                    "$type": "DriftCorrect",
                    "location": text_start_location,
                },
                {
                    "$type": "LabelAnnotation",
                    "$name": f"{item_id}.anno",
                    "$record_eyes": True,
                    "imgpath": anno_image.imgpath,
                    "label_boxes": {
                        area.content.removeprefix("label:"): area.xywh
                        for area in anno_image.areas["section"]
                        if area.content.startswith("label:")
                    },
                    "label_keys": {
                        key: label
                        for key, label in zip(self.label_option_keys, self.labels)
                    },
                    "confirm_key": self.label_confirm_key,
                },
            ]

            stimulus_stages[item_id] = stages

        return stimulus_stages

    def _generate_question_stages(
        self,
        experiment_path: Path,
        text_config: dict[str, Any],
    ) -> list[dict[str, Any]]:
        question_stages = []
        for i, question in enumerate(self.questions):
            if self.question_layout in {"horizontal", "diamond"}:
                question_image, option_boxes = stimuli.generate_mcq_page(
                    question["stem"],
                    question["options"],
                    option_layout=self.question_layout,
                    **text_config,
                )
                question_image.save(experiment_path, f"question.{i+1}")
                question_stages.append(
                    {
                        "$name": f"question.{i+1}",
                        "$type": "MultipleChoiceQuestion",
                        "$record_eyes": True,
                        "imgpath": question_image.imgpath,
                        "option_keys": self.question_option_keys,
                        "option_boxes": option_boxes,
                        "confirm_key": self.question_confirm_key,
                    }
                )

            elif self.question_layout == "cursor":
                question_image, cursor_locations = stimuli.generate_cursor_mcq_page(
                    question["stem"],
                    question["options"],
                    **text_config,
                )
                question_image.save(experiment_path, f"question.{i+1}")
                question_stages.append(
                    {
                        "$name": f"question.{i+1}",
                        "$type": "CursorMultipleChoiceQuestion",
                        "$record_eyes": True,
                        "imgpath": question_image.imgpath,
                        "cursor_locations": cursor_locations,
                        "cursor_size": self.font_size - 8,
                        "prev_option_key": self.question_option_keys[0],
                        "next_option_key": self.question_option_keys[1],
                        "confirm_key": self.question_confirm_key,
                    }
                )

        return question_stages

    def _build_item_assignments(
        self,
        experimental_items: dict[str, dict[str, Any]],
    ) -> dict[str, list[str]]:
        """Returns a dict mapping each participant ID to a list of item IDs (with conditions)."""
        # Build design for experimental items
        participant_ids = [f"P{i}" for i in range(1, self.num_participants + 1)]
        item_ids = sorted(experimental_items.keys())

        # Shuffle item IDs for each participant
        assignments = {}
        for participant_id in participant_ids:
            participant_assignments = item_ids.copy()
            random.seed(participant_id)
            random.shuffle(participant_assignments)
            assignments[participant_id] = participant_assignments
        return assignments
