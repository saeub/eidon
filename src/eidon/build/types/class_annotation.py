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

    ### Items

    There are two types of items: experimental and practice. **Experimental items** constitute the
    main stimuli of the experiment. **Practice items** are presented before the experimental items
    to familiarize participants with the task.

    Items are defined in CSV files (see [below](#files)).

    ### Areas of interest

    Areas of interest can be defined in the `text` column by surrounding them with
    `[[area-name]]...[[/area-name]]`. For example:

    ```
    [[subject]]The quick brown fox[[/subject]] jumps over [[object]]the lazy dog[[/object]].
    ```

    An item can contain any number of areas of interest. Discontinuous areas can be defined by
    using multiple tags with the same area name.

    ### Questions

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
    :param font_size: Font size in pixels for all text.
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

    _ITEM_COLUMNS = {
        "id": {
            "description": "Unique identifier for the item.",
            "required": True,
        },
        "text": {
            "description": "Stimulus text to be displayed.",
            "required": True,
        },
    }

    MATERIALS_SCHEMA = {
        "instructions.txt": {
            "description": "Text for the instructions shown at the beginning of the experiment.",
            "required": True,
        },
        "wait.txt": {
            "description": (
                "Text shown after the instructions and practice trials, while waiting "
                "for the experimenter to start the experimental trials."
            ),
        },
        "break.txt": {
            "description": "Text shown during breaks.",
        },
        "end.txt": {
            "description": "Text shown at the end of the experiment.",
            "required": True,
        },
        "items/experimental.csv": {
            "description": ("Table of experimental items, one row per item."),
            "required": True,
            "columns": _ITEM_COLUMNS,
        },
        "items/practice.csv": {
            "description": ("Table of practice items, one row per item. "),
            "columns": _ITEM_COLUMNS,
        },
    }

    def build(self) -> dict[str, dict[str, Any]]:
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
            "width": self.stimulus_area_size[0],
            "height": self.stimulus_area_size[1],
            "margin": self.margin,
            "font_path": font_path,
            "font_size": self.font_size,
            "line_spacing": self.line_spacing,
            "background_color": self.background_color,
            "vertical_align": "center",
        }

        instructions_stage = self._generate_instructions_stage(
            text_config
        )
        end_stage = self._generate_end_stage(text_config)
        wait_stage = self._generate_wait_stage(text_config)
        if self.breaks_after is not None:
            break_stage = self._generate_break_stage(text_config)

        experimental_items, practice_items = self._process_items()
        annotation_stages = self._generate_annotation_stages(
            experimental_items,
            practice_items,
            text_config,
        )

        question_stages = self._generate_question_stages(
            text_config,
        )

        assignments = self._build_item_assignments(experimental_items)
        # Save assignment table for convenience
        with open(self.experiment_path / "sessions" / "assignments.csv", "w") as f:
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

    def _process_items(
        self,
    ) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
        """Turn the raw item data into a structured format and validate it.

        Returns experimental and practice items as dicts mapping item IDs to items:
        {
            "item.1": {item_data},
            ...
        }
        """
        # Collect and check experimental items
        experimental_items_path = "items/experimental.csv"
        experimental_items = {}
        if experimental_items_path in self.materials:
            for item in self.materials[experimental_items_path]:
                item_id = item["id"]
                item_id = f"item.{item_id}"
                item["id"] = item_id
                if item_id in experimental_items:
                    raise ValueError(
                        f"Duplicate item ID {item_id} in {experimental_items_path}."
                    )
                item_text = item["text"]
                if not item_text:
                    raise ValueError(
                        f"Item {item_id} in {experimental_items_path} has empty text."
                    )
                item_text, custom_area_spans = self._parse_area_spans(item_text)
                item["text"] = item_text
                item["custom_area_spans"] = custom_area_spans
                experimental_items[item_id] = item

            if experimental_items is not None and len(experimental_items) == 0:
                warnings.warn(
                    f"No experimental items found in {experimental_items_path}."
                )

        # Collect and check practice items
        practice_items_path = "items/practice.csv"
        practice_items = {}
        if practice_items_path in self.materials:
            for item in self.materials[practice_items_path]:
                item_id = item["id"]
                item_id = f"practice.{item_id}"
                item["id"] = item_id
                if item_id in practice_items:
                    raise ValueError(
                        f"Duplicate item ID {item_id} in {practice_items_path}."
                    )
                item_text = item["text"]
                if not item_text:
                    raise ValueError(
                        f"Item {item_id} in {practice_items_path} has empty text."
                    )
                item_text, custom_area_spans = self._parse_area_spans(item_text)
                item["text"] = item_text
                item["custom_area_spans"] = custom_area_spans
                practice_items[item_id] = item

            if practice_items is not None and len(practice_items) == 0:
                warnings.warn(
                    f"No practice items found in {practice_items_path}."
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
        self, text_config: dict[str, Any]
    ) -> dict[str, Any]:
        text = (
            (self.experiment_path / "materials" / "instructions.txt")
            .read_text(encoding="utf8")
            .strip()
        )
        # TODO: Allow manual page breaks
        images = stimuli.generate_text_pages(text, **text_config)
        for i, image in enumerate(images):
            image.save(self.experiment_path, f"instructions.{i}")
        return {
            "$type": "StimulusMultiPage",
            "$name": "instructions",
            "$record_eyes": True,
            "imgpaths": [image.imgpath for image in images],
            "next_page_key": "SPACE",
        }

    def _generate_end_stage(self, text_config: dict[str, Any]) -> dict[str, Any]:
        text = (
            (self.experiment_path / "materials" / "end.txt")
            .read_text(encoding="utf8")
            .strip()
        )
        (image,) = stimuli.generate_text_pages(
            text,
            **text_config,
        )
        image.save(self.experiment_path, "end")
        return {
            "$type": "StimulusPage",
            "$name": "end",
            "imgpath": image.imgpath,
            "continue_key": "SPACE",
        }

    def _generate_wait_stage(
        self,
        text_config: dict[str, Any],
    ) -> dict[str, Any]:
        participant_text = ""
        if (self.experiment_path / "materials" / "wait.txt").exists():
            participant_text = (
                (self.experiment_path / "materials" / "wait.txt")
                .read_text(encoding="utf8")
                .strip()
            )
        (participant_image,) = stimuli.generate_text_pages(
            participant_text,
            **text_config,
        )
        participant_image.save(self.experiment_path, "wait.participant")
        (host_image,) = stimuli.generate_text_pages(
            "[SPACE] Setup\n[ESC] Continue",
            **text_config,
        )
        host_image.save(self.experiment_path, "wait.host")
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
        text_config: dict[str, Any],
    ) -> dict[str, Any]:
        text = (
            (self.experiment_path / "materials" / "break.txt")
            .read_text(encoding="utf8")
            .strip()
        )
        (image,) = stimuli.generate_text_pages(
            text,
            **text_config,
        )
        image.save(self.experiment_path, "break")
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
            anno_image.save(self.experiment_path, f"{item_id}.anno")
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
                question_image.save(self.experiment_path, f"question.{i+1}")
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
                question_image.save(self.experiment_path, f"question.{i+1}")
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
        """Returns a dict mapping each participant ID to a list of item IDs."""
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
