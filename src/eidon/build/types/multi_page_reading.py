from collections import defaultdict
import csv
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import warnings

from eidon.build import ExperimentType, stimuli
from eidon.build.designs import build_design
from eidon.fonts import FONTS


@dataclass(kw_only=True)
class MultiPageReading(ExperimentType):
    """
    Reading experiment with longer, multi-page text stimuli.

    Each experimental item consists of a text and optionally one or more multiple-choice questions.
    Each item may appear in multiple conditions, which are assigned to participants according to the
    specified design (e.g., Latin square). Practice items can also be added.

    The main differences to `SinglePageReading` are:
    - The text for each item can span multiple pages. The text is automatically split into pages
      when necessary. Explicit page breaks can also be added using `<<pagebreak>>`.
    - The texts are vertically aligned to the top of the page (instead of centered).
    - Filler items are not supported.

    ### Items

    There are two types of items: experimental and practice. **Experimental items** constitute the
    main stimuli of the experiment. **Practice items** are presented before the experimental items
    to familiarize participants with the task.

    Items are defined in CSV files (see [below](#files)).

    ### Page breaks

    Page breaks are added automatically when the text exceeds the size of the stimulus area.
    Manual page breaks can be added by inserting `<<pagebreak>>` in the text (on a separate line).

    ### Areas of interest

    Areas of interest can be defined in the `text` column by surrounding them with
    `[[area-name]]...[[/area-name]]`. For example:

    ```
    [[subject]]The quick brown fox[[/subject]] jumps over [[object]]the lazy dog[[/object]].
    ```

    An item can contain any number of areas of interest. Discontinuous areas can be defined by
    using multiple tags with the same area name.

    :param num_participants: Number of participants in the experiment.
        Should be a multiple of the number of conditions.
    :param conditions: List of item condition names (if any).
    :param design: Name of the design to use for assigning items to participants.
    :param breaks_after: Insert a break after every N items.
    :param margin: Margin in pixels around the text on the stimulus pages.
    :param font_monospaced: Whether to use a monospaced font for the stimuli.
        This is recommended when controlling for word length effects.
    :param font_size: Font size in pixels for all text.
    :param line_spacing: Line spacing multiplier for all text.
    :param question_layout: Layout for multiple-choice questions.
        `horizontal` arranges options in a horizontal row, `diamond` arranges them in a diamond
        shape (requires exactly 4 options that are selected with the UP, LEFT, RIGHT, and DOWN
        keys), and `cursor` arranges them vertically with a visual selector that can be controlled
        with the UP and DOWN keys (requires `confirm_key`).
    :param option_keys: List of keys to use for selecting multiple-choice options, in order.
        For example, `[Y, N]` to use the Y key for the first option and the N key for the second
        option. Only required when question layout is `horizontal`.
    :param confirm_key: Key to use for confirming the selection of an option.
        If not specified, options are selected immediately when the corresponding option key is
        pressed.
    """

    num_participants: int
    conditions: list[str] | None = None
    design: str = "latin_square"
    breaks_after: int | None = None
    margin: int = 50
    font_monospaced: bool = False
    font_size: int = 25
    line_spacing: int = 2.0
    question_layout: str = "horizontal"
    option_keys: list[str] | None = None
    confirm_key: str | None = None

    _ITEM_COLUMNS = {
        "id": {
            "description": "Unique identifier for the item.",
            "required": True,
        },
        "text": {
            "description": "Stimulus text to be displayed.",
            "required": True,
        },
        "question.#.stem": {
            "description": (
                "Stem of the #-th multiple-choice question "
                "(starting at 0: `question.0.stem`, `question.1.stem`, ...)."
            ),
        },
        "question.#.option.#": {
            "description": (
                "#-th answer option for the #-th question "
                "(starting at 0: `question.0.option.0`, `question.0.option.1`, ...)."
            ),
        },
        "question.#.correct_option_index": {
            "description": (
                "Index of the correct answer option for the #-th question "
                "(starting at 0: `question.0.correct_option_index`, `question.1.correct_option_index`, ...)."
            ),
            "type": int,
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
            "description": (
                "Table of experimental items, one row per item per condition."
            ),
            "required": True,
            "columns": {
                **_ITEM_COLUMNS,
                "condition": {
                    "description": "Name of the experimental condition. Only required if config.yaml specifies multiple conditions.",
                },
            },
        },
        "items/practice.csv": {
            "description": (
                "Table of practice items, one row per item. "
                "Practice items do not support multiple conditions."
            ),
            "columns": _ITEM_COLUMNS,
        },
    }

    def build(self) -> dict[str, dict[str, Any]]:
        if self.question_layout == "horizontal":
            if self.option_keys is None:
                raise ValueError(
                    "option_keys must be provided for horizontal question layout."
                )
        elif self.question_layout == "diamond":
            if self.option_keys is None:
                self.option_keys = ["UP", "LEFT", "RIGHT", "DOWN"]
            if len(self.option_keys) != 4:
                raise ValueError(
                    "Exactly 4 option keys must be provided for diamond layout "
                    "(to select top/left/right/bottom option)."
                )
        elif self.question_layout == "cursor":
            if self.option_keys is None:
                self.option_keys = ["UP", "DOWN"]
            if len(self.option_keys) != 2:
                raise ValueError(
                    "Exactly 2 option keys must be provided for cursor layout "
                    "(to move cursor up and down)."
                )
            if self.confirm_key is None:
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
            "vertical_align": "top",
        }

        instructions_stage = self._generate_instructions_stage(
            text_config
        )
        end_stage = self._generate_end_stage(text_config)
        wait_stage = self._generate_wait_stage(text_config)
        if self.breaks_after is not None:
            break_stage = self._generate_break_stage(text_config)

        experimental_items, practice_items = self._process_items()
        stimulus_stages = self._generate_stimulus_stages(
            experimental_items,
            practice_items,
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
                    practice_stages.extend(stimulus_stages[name])
                practice_stages.append(wait_stage | {"$name": "wait.practice"})

            item_stages = []
            for i, name in enumerate(assignment):
                if (
                    self.breaks_after is not None
                    and i > 0
                    and i % self.breaks_after == 0
                ):
                    item_stages.append(break_stage | {"$name": f"break.{i}"})
                item_stages.extend(stimulus_stages[name])

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

    _ConditionedItem = dict[str, dict[str, Any]]  # {condition: {item}}

    def _process_items(
        self,
    ) -> tuple[
        dict[str, _ConditionedItem],
        dict[str, _ConditionedItem],
    ]:
        """Turn the raw item data into a structured format and validate it.

        Returns experimental, practice, and filler items as dicts
        mapping item IDs to dicts of conditions to items:
        {
            "item.1": {
                "condition1": {"pages": [...], "question": [...]},
                "condition2": {"pages": [...], "question": [...]},
                ...
            },
            ...
        }
        """
        # Collect and check experimental items
        experimental_items_path = "items/experimental.csv"
        experimental_items = {}
        for item in self.materials[experimental_items_path]:
            item_id = item["id"]
            item_id = f"item.{item_id}"
            item["id"] = item_id
            item_condition = item.get("condition")

            item_text = item["text"]
            if not item_text:
                raise ValueError(
                    f"Item {item_id} in {experimental_items_path} has empty text."
                )
            item["pages"] = []
            item_page_texts = [page.strip("\r\n") for page in item_text.split("\n<<pagebreak>>\n")]
            for text in item_page_texts:
                text, custom_area_spans = self._parse_area_spans(text)
                page = {"text": text, "custom_area_spans": custom_area_spans}
                item["pages"].append(page)

            # Items with conditions
            if self.conditions:
                item_condition = item.get("condition")
                if not item_condition:
                    raise ValueError(
                        f"Item {item_id} in {experimental_items_path} "
                        f"has missing or empty condition, should have one of {self.conditions}."
                    )
                if item_condition not in self.conditions:
                    raise ValueError(
                        f"Item {item_id} in {experimental_items_path} "
                        f"has condition {item_condition}, but expected one of {self.conditions}."
                    )
                # Nest conditions within item
                if item_id not in experimental_items:
                    experimental_items[item_id] = {}
                elif item_condition in experimental_items[item_id]:
                    raise ValueError(
                        f"Item {item_id} in {experimental_items_path} "
                        f"has duplicate condition {item_condition}."
                    )
                experimental_items[item_id][item_condition] = item

            # Items without conditions
            else:
                if item_id in experimental_items:
                    raise ValueError(
                        f"Duplicate item ID {item_id} in {experimental_items_path}."
                    )
                if item_condition:
                    raise ValueError(
                        f"Item {item_id} in {experimental_items_path} "
                        f"has condition {item_condition}, "
                        f"but no conditions were specified in {self.config_path}."
                    )
                # No conditions, use None as dummy condition key
                experimental_items[item_id] = {None: item}

        # Check that all items have all expected conditions
        if self.conditions is not None:
            for item_id, item in experimental_items.items():
                item_conditions = set(item.keys())
                if set(item_conditions) != set(self.conditions):
                    raise ValueError(
                        f"Item {item_id} has conditions {item_conditions}, expected {self.conditions}."
                    )

        if len(experimental_items) == 0:
            warnings.warn(f"No items found in {experimental_items_path}.")

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
                item["pages"] = []
                item_page_texts = [page.strip("\r\n") for page in item_text.split("\n<<pagebreak>>\n")]
                for text in item_page_texts:
                    text, custom_area_spans = self._parse_area_spans(text)
                    page = {"text": text, "custom_area_spans": custom_area_spans}
                    item["pages"].append(page)
                # No conditions for practice items, use None as dummy condition key
                practice_items[item_id] = {None: item}

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

    def _generate_end_stage(
        self, text_config: dict[str, Any]
    ) -> dict[str, Any]:
        text = self.materials["end.txt"]
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
        if "wait.txt" in self.materials:
            participant_text = self.materials["wait.txt"]
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
        text = self.materials["break.txt"]
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

    def _generate_stimulus_stages(
        self,
        experimental_items: dict[str, dict[str, Any]],
        practice_items: dict[str, dict[str, Any]],
        text_config: dict[str, Any],
    ) -> dict[str, list[dict[str, Any]]]:
        stimulus_stages = {}
        for item_id, item in list(experimental_items.items()) + list(
            practice_items.items()
        ):
            for condition, subitem in item.items():
                if item_id.startswith("practice.") or self.conditions is None:
                    name = item_id
                else:
                    name = f"{item_id}.{condition}"
                text_images = []
                for page in subitem["pages"]:
                    text_images.extend(
                        stimuli.generate_text_pages(
                            page["text"],
                            custom_area_spans=page["custom_area_spans"],
                            **text_config,
                        )
                    )
                for i, image in enumerate(text_images):
                    for area_type in page["custom_area_spans"]:
                        if area_type in image.areas and any(
                            area.continued for area in image.areas[area_type]
                        ):
                            warnings.warn(
                                f"Area '{area_type}' in item {name} (page {i}) crosses line boundaries."
                            )
                    image.save(self.experiment_path, f"{name}.text.{i}")
                text_start_location = (
                    int(self.margin - self.font_size),
                    int(self.margin + self.font_size * self.line_spacing / 2),
                )

                stages = [
                    {
                        "$name": f"{name}.drift",
                        "$type": "DriftCorrect",
                        "location": text_start_location,
                    },
                ] + [
                    {
                        "$type": "StimulusPage",
                        "$name": f"{name}.text.{i}",
                        "$record_eyes": True,
                        "imgpath": image.imgpath,
                        "continue_key": "SPACE",
                        "$after": {
                            "$type": "FixationTarget",
                            "location": text_start_location,
                        },
                    }
                    for i, image in enumerate(text_images)
                ]
                stages[-1].pop("$after")  # Remove fixation cross after last page

                for i, question in enumerate(subitem["question"]):
                    if self.question_layout in {"horizontal", "diamond"}:
                        question_image, option_boxes = stimuli.generate_mcq_page(
                            question["stem"],
                            question["option"],
                            option_layout=self.question_layout,
                            **text_config,
                        )
                        question_image.save(self.experiment_path, f"{name}.question.{i+1}")
                        stages.append(
                            {
                                "$name": f"{name}.question.{i+1}",
                                "$type": "MultipleChoiceQuestion",
                                "$record_eyes": True,
                                "imgpath": question_image.imgpath,
                                "option_keys": self.option_keys,
                                "correct_option_index": question[
                                    "correct_option_index"
                                ],
                                "option_boxes": option_boxes,
                                "confirm_key": self.confirm_key,
                            }
                        )

                    elif self.question_layout == "cursor":
                        question_image, cursor_locations = (
                            stimuli.generate_cursor_mcq_page(
                                question["stem"],
                                question["option"],
                                **text_config,
                            )
                        )
                        question_image.save(self.experiment_path, f"{name}.question.{i+1}")
                        stages.append(
                            {
                                "$name": f"{name}.question.{i+1}",
                                "$type": "CursorMultipleChoiceQuestion",
                                "$record_eyes": True,
                                "imgpath": question_image.imgpath,
                                "cursor_locations": cursor_locations,
                                "cursor_size": self.font_size - 8,
                                "prev_option_key": self.option_keys[0],
                                "next_option_key": self.option_keys[1],
                                "confirm_key": self.confirm_key,
                                "correct_option_index": question[
                                    "correct_option_index"
                                ],
                            }
                        )

                stimulus_stages[name] = stages

        return stimulus_stages

    def _build_item_assignments(
        self,
        experimental_items: dict[str, dict[str, Any]],
    ) -> dict[str, list[str]]:
        """Returns a dict mapping each participant ID to a list of item IDs (with conditions)."""
        # Build design for experimental items
        participant_ids = [f"P{i}" for i in range(1, self.num_participants + 1)]
        item_ids = sorted(experimental_items.keys())
        conditions = self.conditions if self.conditions is not None else ["item"]
        design = build_design(self.design, participant_ids, item_ids, conditions)

        # Shuffle
        assignments = {}
        for participant_id in participant_ids:
            if self.conditions is None:
                participant_assignments = [
                    item_id for item_id, _ in design[participant_id]
                ]
            else:
                participant_assignments = [
                    f"{item_id}.{condition}"
                    for item_id, condition in design[participant_id]
                ]
            random.seed(participant_id)
            random.shuffle(participant_assignments)
            assignments[participant_id] = participant_assignments
        return assignments
