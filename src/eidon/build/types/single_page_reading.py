from collections import defaultdict
import csv
import random
import re
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from eidon.build import ExperimentType, stimuli
from eidon.build.designs import build_design
from eidon.fonts import FONTS


@dataclass(kw_only=True)
class SinglePageReading(ExperimentType):
    """
    Reading experiment with short, single-page text stimuli.

    Each experimental item consists of a text and optionally one or more multiple-choice questions.
    Each item may appear in multiple conditions, which are assigned to participants according to the
    specified design (e.g., Latin square). Filler items can also be added.

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
          ├─ 📄 practice.txt (optional)
          └─ 📄 fillers.txt (optional)
    ```

    `instructions.txt`, `wait.txt`, `break.txt`, and `end.txt` contain the text for the
    instructions, wait (after instructions and practice trials), break, and end pages. The
    instructions are split into multiple pages if necessary.

    #### Experimental items

    `01.txt`, `02.txt`, etc. each represent one experimental item. The file names (without `.txt`)
    are used as item IDs. Each file must follow the following format (values in [brackets] are
    placeholders):

    ```
    <<item>>
    [text for condition 1]
    <<question>>
    [question stem]
    <<options>>
    [option 1]
    **[option 2]
    [option 3]
    <<question>>
    [question stem]
    <<options>>
    [option 1]
    [option 2]
    ```

    If the experiment has **multiple conditions**, each item file contains the text and questions
    for all conditions, and the name of the condition must be specified like this:

    ```
    <<[condition 1]>>
    [text for condition 1]
    <<question>>
    [question stem]
    <<options>>
    [option 1]
    **[option 2]
    [option 3]
    <<question>>
    [question stem]
    <<options>>
    [option 1]
    [option 2]

    <<[condition 2]>>
    [text for condition 2]
    ...
    ```

    The number of questions can vary across items. Optionally, one answer option per question can be
    marked with `**` to indicate that it is the correct answer.

    #### Practice and filler items

    `practice.txt` and `fillers.txt` are optional and can contain any number of practice and filler
    items, which follow a similar format (but without conditions):

    ```
    <<filler>>
    [text for filler 1]
    <<question>>
    [question stem]
    <<options>>
    [option 1]
    [option 2]
    [option 3]
    <<question>>
    [question stem]
    <<options>>
    [option 1]
    [option 2]

    <<filler>>
    [text for filler 2]
    ...
    ```

    Replace `<<filler>>` with `<<practice>>` for practice items.

    #### Areas of interest

    Areas of interest can be defined in the text by surrounding them with
    [[area-name]]...[[/area-name]]. For example:

    ```
    <<item>>
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
    :param font_size: Font size for all text.
    :param line_spacing: Line spacing multiplier for all text.
    :param question_layout: Layout for multiple-choice questions.
        `horizontal` arranges options in a horizontal row, `diamond` arranges them in a diamond
        shape (requires exactly 4 options that are selected with the UP, LEFT, RIGHT, and DOWN
        keys), and `cursor` arranges them vertically with a cursor movable with the UP and DOWN
        keys (requires `confirm_key`).
    :param option_keys: List of keys to use for selecting multiple-choice options, in order.
        For example, `["Y", "N"]` to use the Y key for the first option and N key for the second
        option. Only required when question layout is `horizontal`.
    :param option_confirm_key: Key to use for confirming the selection of an option.
        If not specified, options are selected immediately when the corresponding option key is
        pressed.
    """

    num_participants: int
    conditions: list[str] | None = None
    design: str = "latin_square"
    breaks_after: int | None = None
    margin: int = 50
    font_monospaced: bool = True
    font_size: int = 25
    line_spacing: int = 2.0
    question_layout: str = "horizontal"
    option_keys: list[str] | None = None
    confirm_key: str | None = None

    def build(self, experiment_path: Path) -> dict[str, dict[str, Any]]:
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

        experimental_items, practice_items, filler_items = self._parse_items(
            experiment_path
        )
        stimulus_stages = self._generate_stimulus_stages(
            experimental_items,
            practice_items,
            filler_items,
            experiment_path,
            text_config,
        )

        assignments = self._build_item_assignments(experimental_items, filler_items)
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

    def _parse_items(
        self, experiment_path: Path
    ) -> tuple[
        dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]
    ]:
        experimental_items = {}
        practice_items = {}
        filler_items = {}
        for item_path in (experiment_path / "materials" / "items").glob("*.txt"):
            file_content = item_path.read_text(encoding="utf8")
            if item_path.name in {"practice.txt", "fillers.txt"}:
                item_type = "practice" if item_path.name == "practice.txt" else "filler"
                item_strings = [
                    f"<<{item_type}>>\n" + s
                    for s in file_content.split(f"<<{item_type}>>")
                    if s.strip()
                ]
                for i, item_string in enumerate(item_strings):
                    item = self._parse_item(item_string, item_path.name)
                    if set(item.keys()) != {item_type}:
                        raise ValueError(
                            f"Each {item_type} item in {item_path.name} "
                            f"must be preceded by a <<{item_type}>> tag."
                        )
                    if item_type == "practice":
                        practice_items[f"{item_type}.{i+1}"] = item
                    else:
                        filler_items[f"{item_type}.{i+1}"] = item
            else:
                item = self._parse_item(file_content, item_path.name)
                if self.conditions is None and set(item.keys()) != {"item"}:
                    raise ValueError(
                        f"When no conditions are defined, the experimental item in {item_path.name} "
                        "must be preceded by a <<item>> tag."
                    )
                elif self.conditions is not None and set(item.keys()) != set(
                    self.conditions
                ):
                    raise ValueError(
                        f"Item {item_path.name} has conditions {set(item.keys())}, "
                        f"expected {set(self.conditions)}."
                    )
                experimental_items[f"item.{item_path.stem}"] = item
        if len(filler_items) < len(experimental_items):
            percentage = (
                len(filler_items) / (len(experimental_items) + len(filler_items))
            ) * 100
            warnings.warn(
                f"Fillers make up only {percentage:.1f}% of the items. "
                f"Consider adding more fillers to reach at least 50%."
            )
        if self.conditions is not None:
            for item_id, item in experimental_items.items():
                item_conditions = set(item.keys())
                if set(item_conditions) != set(self.conditions):
                    raise ValueError(
                        f"Item {item_id} has conditions {item_conditions}, expected {self.conditions}."
                    )
        return experimental_items, practice_items, filler_items

    def _parse_item(self, item_string: str, filename: str) -> dict[str, Any]:
        """
        Parse a stimulus string into a dict containing the text and questions for each condition.

        Item string format (values in brackets are placeholders):
        '''
        <<[condition 1]>>
        [text for condition 1]
        <<question>>
        [question stem]
        <<options>>
        [option 1]
        **[option 2]
        [option 3]
        <<question>>
        [question stem]
        <<options>>
        [option 1]
        [option 2]

        <<[condition 2]>>
        ...
        '''

        Each condition can contain multiple questions. Correct answer options can be marked with **.

        Returns a dict with this structure:
        {
            "[condition_1]": {
                "text": "[text for condition A]",
                "custom_area_spans": {...},
                "questions": {
                    "stem": "[question stem]"
                    "options": ["[option 1]", "[option 2]", "[option 3]"]
                    "correct_option_index": 1
                },
            },
            "[condition_2]": {
                ...
            }
        }
        """
        # Generic regex that captures any tag and the text on the following lines
        tag_pattern = re.compile(r"<<(.+)>>\n([\S\s]+?)(?=<<|\Z)", re.MULTILINE)
        matches = []
        match_start = 0
        while match_start < len(item_string):
            match = tag_pattern.match(item_string, match_start)
            if not match:
                raise ValueError(
                    f"Expected a <<tag>> followed by text in {filename} at "
                    f"'{item_string[match_start:match_start+20]}...'"
                )
            matches.append(match)
            match_start = match.end()
        if not matches:
            raise ValueError(f"No tags found in {filename}.")

        item = {}
        current_condition = None
        current_subitem = None  # Holds text/questions for the current condition
        for match in matches:
            tag = match.group(1).strip()
            if re.search(r"\s", tag):
                raise ValueError(
                    f"Invalid tag <<{tag}>> in {filename}: tags cannot contain whitespace."
                )
            text = match.group(2).strip()

            # Question stem
            if tag == "question":
                if current_subitem is None:
                    raise ValueError(
                        f"'<<question>>' tag found before any condition tag in {filename}."
                    )
                current_subitem["questions"].append(
                    {"stem": text, "options": None, "correct_option_index": None}
                )
            # Question options
            elif tag == "options":
                if current_subitem is None or not current_subitem["questions"]:
                    raise ValueError(
                        f"'<<options>>' tag found without a preceding '<<question>>' in {filename}."
                    )
                if current_subitem["questions"][-1]["options"] is not None:
                    raise ValueError(
                        f"Multiple '<<options>>' tags found for question {current_subitem['questions'][-1]['stem']} in {filename}."
                    )
                options = []
                correct_option_index = None
                for line in text.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("**"):
                        option_text = line[2:].strip()
                        if correct_option_index is not None:
                            raise ValueError(
                                f"Multiple options marked as correct in {filename}."
                            )
                        correct_option_index = len(options)
                    else:
                        option_text = line
                    options.append(option_text)
                current_subitem["questions"][-1]["options"] = options
                current_subitem["questions"][-1][
                    "correct_option_index"
                ] = correct_option_index
            else:
                # New condition
                if current_condition is not None:
                    item[current_condition] = current_subitem
                current_condition = tag
                text, custom_area_spans = self._parse_area_spans(text)
                current_subitem = {
                    "text": text,
                    "custom_area_spans": custom_area_spans,
                    "questions": [],
                }
        # Final condition
        if current_condition is not None:
            item[current_condition] = current_subitem

        for subitem in item.values():
            for question in subitem["questions"]:
                if not question["options"]:
                    raise ValueError(
                        f"Question '{question['stem']}' in {filename} has no options."
                    )

        return item

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

    def _generate_stimulus_stages(
        self,
        experimental_items: dict[str, dict[str, Any]],
        practice_items: dict[str, dict[str, Any]],
        filler_items: dict[str, dict[str, Any]],
        experiment_path: Path,
        text_config: dict[str, Any],
    ) -> dict[str, list[dict[str, Any]]]:
        stimulus_stages = {}
        for item_id, item in (
            list(experimental_items.items())
            + list(practice_items.items())
            + list(filler_items.items())
        ):
            for condition, subitem in item.items():
                if (
                    item_id.startswith(("practice.", "filler."))
                    or self.conditions is None
                ):
                    name = item_id
                else:
                    name = f"{item_id}.{condition}"
                text_images = stimuli.generate_text_pages(
                    subitem["text"],
                    custom_area_spans=subitem["custom_area_spans"],
                    **text_config,
                )
                assert (
                    len(text_images) == 1
                ), f"Text for item {name} does not fit on a single page."
                text_image = text_images[0]
                for area_type in subitem["custom_area_spans"]:
                    if any(area.continued for area in text_image.areas[area_type]):
                        warnings.warn(
                            f"Area '{area_type}' in item {name} crosses line boundaries."
                        )
                text_image.save(experiment_path, f"{name}.text")
                text_start_location = (
                    int(text_image.areas["page"][0].left - self.font_size),
                    int(
                        text_image.areas["page"][0].top
                        + self.font_size * self.line_spacing / 2
                    ),
                )

                stages = [
                    {
                        "$name": f"{name}.drift",
                        "$type": "DriftCorrect",
                        "location": text_start_location,
                    },
                    {
                        "$type": "StimulusPage",
                        "$name": f"{name}.text",
                        "$record_eyes": True,
                        "imgpath": text_image.imgpath,
                        "continue_key": "SPACE",
                    },
                ]

                for i, question in enumerate(subitem["questions"]):
                    if self.question_layout in {"horizontal", "diamond"}:
                        question_image, option_boxes = stimuli.generate_mcq_page(
                            question["stem"],
                            question["options"],
                            option_layout=self.question_layout,
                            **text_config,
                        )
                        question_image.save(experiment_path, f"{name}.question.{i+1}")
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
                                question["options"],
                                **text_config,
                            )
                        )
                        question_image.save(experiment_path, f"{name}.question.{i+1}")
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
        filler_items: dict[str, dict[str, Any]],
    ) -> dict[str, list[str]]:
        """Returns a dict mapping each participant ID to a list of item IDs (with conditions)."""
        # Build design for experimental items
        participant_ids = [f"P{i}" for i in range(1, self.num_participants + 1)]
        item_ids = sorted(experimental_items.keys())
        conditions = self.conditions if self.conditions is not None else ["item"]
        design = build_design(self.design, participant_ids, item_ids, conditions)

        # Add fillers and shuffle
        assignments = {}
        for participant_id in participant_ids:
            if self.conditions is None:
                experimental_assignments = [
                    item_id for item_id, _ in design[participant_id]
                ]
            else:
                experimental_assignments = [
                    f"{item_id}.{condition}"
                    for item_id, condition in design[participant_id]
                ]
            filler_assignments = [item_id for item_id in filler_items.keys()]
            participant_assignments = experimental_assignments + filler_assignments
            random.seed(participant_id)
            random.shuffle(participant_assignments)
            assignments[participant_id] = participant_assignments
        return assignments
