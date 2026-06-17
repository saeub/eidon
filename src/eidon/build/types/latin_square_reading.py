import csv
import random
import re
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from eidon.build import ExperimentType, stimuli
from eidon.fonts import FONTS


@dataclass
class LatinSquareReading(ExperimentType):
    """
    Reading experiment with single-page minimal-pair stimuli and a Latin square design.

    Each experimental item consists of a text and optionally one or more multiple-choice questions.
    Each item appears in multiple conditions, which are assigned to participants in such a way that
    each participant sees each item in exactly one condition, and each condition is seen equally
    often across participants. Filler items can also be added.

    ### Required materials

    ```
    📂 my_experiment
    ├─ config.yaml
    └─ 📂 materials
       ├─ 📄 instructions.txt
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

    `instructions.txt`, `break.txt`, and `end.txt` contain the text for the instructions, break, and
    end pages. The instructions are split into multiple pages depending on length.

    `01.txt`, `02.txt`, etc. each represent one experimental item. The file names (without `.txt`)
    are used as item IDs. Each file must follow the following format (values in [brackets] are
    placeholders):

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

    The conditions must be the same across all items, but the number of questions can vary.
    Optionally, one answer option per question can be marked with `**` to indicate that it is the
    correct answer.

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

    :param num_participants: Number of participants in the experiment.
        Should be a multiple of the number of conditions.
    :param option_keys: List of keys to use for selecting multiple-choice options, in order.
        For example, ["Y", "N"] to use the Y key for the first option and N key for the second option.
    :param margin_px: Margin in pixels around the text on the stimulus pages.
    :param font_monospaced: Whether to use a monospaced font for the stimuli.
        This is recommended when controlling for word length effects.
    :param font_size: Font size for all text.
    :param line_spacing: Line spacing multiplier for all text.
    :param breaks_after: Insert a break after every N items.
    """

    num_participants: int
    option_keys: list[str]
    font_monospaced: bool = True
    font_size: int = 25
    line_spacing: int = 2.0
    breaks_after: int | None = None

    def build(self, experiment_path: Path) -> dict[str, dict[str, Any]]:
        if self.font_monospaced:
            font_path = FONTS["monospace"]
        else:
            font_path = FONTS["default"]

        text_config = {
            "width": self.display_size_px[0],
            "height": self.display_size_px[1],
            "margin_px": self.margin_px,
            "font_path": font_path,
            "font_size": self.font_size,
            "line_spacing": self.line_spacing,
            "background_color": self.background_color,
            "vertical_align": "center",
        }

        # Load texts
        instructions_text = (
            (experiment_path / "materials" / "instructions.txt")
            .read_text(encoding="utf8")
            .strip()
        )
        end_text = (
            (experiment_path / "materials" / "end.txt")
            .read_text(encoding="utf8")
            .strip()
        )
        if self.breaks_after is not None:
            break_text = (
                (experiment_path / "materials" / "break.txt")
                .read_text(encoding="utf8")
                .strip()
            )

        # Parse items
        experimental_items, practice_items, filler_items = self._parse_items(
            experiment_path
        )

        # Generate instruction pages
        instructions_images = stimuli.generate_text_pages(
            instructions_text,
            **text_config,
        )
        for i, image in enumerate(instructions_images):
            image.save(experiment_path / "stimuli", f"instructions.{i}")
        instructions_stage = {
            "$type": "StimulusMultiPage",
            "$name": "instructions",
            "$record_eyes": True,
            "imgpaths": [
                f"stimuli/instructions.{i}.png" for i in range(len(instructions_images))
            ],
            "next_page_key": "SPACE",
        }

        # Generate end page
        (end_image,) = stimuli.generate_text_pages(
            end_text,
            **text_config,
        )
        end_image.save(experiment_path / "stimuli", "end")
        end_stage = {
            "$type": "StimulusPage",
            "$name": "end",
            "imgpath": "stimuli/end.png",
            "continue_key": "SPACE",
        }

        # Generate host-controlled page
        (host_image,) = stimuli.generate_text_pages(
            "[SPACE] Setup\n[ESC] Continue",
            **text_config,
        )
        host_image.save(experiment_path / "stimuli", "host")
        host_stage = {
            "$name": "wait",
            "$type": "HostControlled",
            "continue_key": "ESCAPE",
            "setup_key": "SPACE",
            "stage": {"$type": "Blank", "continue_key": "SPACE"},
            "host_imgpath": "stimuli/host.png",
        }

        # Generate break page
        if self.breaks_after is not None:
            (break_image,) = stimuli.generate_text_pages(
                break_text,
                **text_config,
            )
            break_image.save(experiment_path / "stimuli", "break")
            break_stage = {
                "$type": "HostControlled",
                "continue_key": "ESCAPE",
                "setup_key": "SPACE",
                "stage": {
                    "$type": "StimulusPage",
                    "imgpath": "stimuli/break.png",
                    "continue_key": "SPACE",
                },
                "host_imgpath": "stimuli/host.png",
            }

        # Generate stimulus pages
        stimulus_stages = {}
        for item_id, item in (
            list(experimental_items.items())
            + list(practice_items.items())
            + list(filler_items.items())
        ):
            for condition, subitem in item.items():
                if item_id.startswith(("practice.", "filler.")):
                    name = item_id
                else:
                    name = f"{item_id}.{condition}"
                images = stimuli.generate_text_pages(
                    subitem["text"],
                    **text_config,
                )
                assert (
                    len(images) == 1
                ), f"Text for item {name} does not fit on a single page."
                images[0].save(experiment_path / "stimuli", f"{name}.text")
                text_start_location = (
                    int(images[0].areas["page"][0].left - text_config["font_size"]),
                    int(
                        images[0].areas["page"][0].top
                        + text_config["font_size"] * text_config["line_spacing"] / 2
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
                        "imgpath": f"stimuli/{name}.text.png",
                        "continue_key": "SPACE",
                    },
                ]

                # cursor_locations = []
                for i, question in enumerate(subitem["questions"]):
                    question_image = (  # , question_cursor_locations = (
                        stimuli.generate_mcq_page(
                            question["stem"],
                            question["options"],
                            **text_config,
                        )
                    )
                    # cursor_locations.append(question_cursor_locations)
                    question_image.save(
                        experiment_path / "stimuli", f"{name}.question.{i+1}"
                    )
                    stages.append(
                        {
                            "$name": f"{name}.question.{i+1}",
                            "$type": "MultipleChoiceQuestion",
                            "$record_eyes": True,
                            "imgpath": f"stimuli/{name}.question.{i+1}.png",
                            "option_keys": self.option_keys,
                            "correct_option_index": question["correct_option_index"],
                            # "cursor_size": self.font_size - 8,
                            # "prev_option_key": "UP",
                            # "next_option_key": "DOWN",
                            # "confirm_key": "SPACE",
                            # "cursor_locations": cursor_locations[i],
                        }
                    )

                stimulus_stages[name] = stages

        # Build latin square lists
        item_ids = sorted(experimental_items.keys())
        conditions = sorted(next(iter(experimental_items.values())).keys())
        item_lists = []

        for list_index in range(len(conditions)):
            item_list = []
            for item_index, item_id in enumerate(item_ids):
                # Rotate condition based on item and list index
                condition_index = (item_index + list_index) % len(conditions)
                condition = conditions[condition_index]
                item_list.append(f"{item_id}.{condition}")
            item_lists.append(item_list)

        # Assign lists to participants, add fillers, and shuffle
        if self.num_participants % len(conditions) != 0:
            warnings.warn(
                f"Number of participants ({self.num_participants}) is not a multiple "
                f"of the number of conditions ({len(conditions)}). "
                f"This will lead to an unbalanced design."
            )
        participant_ids = [f"P{i}" for i in range(1, self.num_participants + 1)]
        assignments = {}
        for participant_index, participant_id in enumerate(participant_ids):
            list_index = participant_index % len(item_lists)
            items = item_lists[list_index].copy()
            items.extend([f"{item_id}" for item_id in filler_items.keys()])
            random.seed(participant_id)
            random.shuffle(items)
            assignments[participant_id] = items

        # Create sessions
        sessions = {}
        for participant_id, assignment in assignments.items():
            practice_stages = []
            if len(practice_items) > 0:
                practice_stages.append(host_stage | {"$name": "wait.practice"})
                for name in practice_items:
                    practice_stages.extend(stimulus_stages[name])

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
                    *practice_stages,
                    host_stage,
                    *item_stages,
                    end_stage,
                ]
            }
            sessions[participant_id] = session

        # Save assignment table for convenience
        with open(experiment_path / "sessions" / "assignments.csv", "w") as f:
            csv_writer = csv.writer(f)
            for participant_id in assignments:
                csv_writer.writerow([participant_id] + assignments[participant_id])

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
                    if len(item) != 1 or next(iter(item.keys())) != item_type:
                        raise ValueError(
                            f"Each {item_type} item in {item_path.name} must be preceded by a <<{item_type}>> tag."
                        )
                    if item_type == "practice":
                        practice_items[f"{item_type}.{i+1}"] = item
                    else:
                        filler_items[f"{item_type}.{i+1}"] = item
            else:
                item = self._parse_item(file_content, item_path.name)
                experimental_items[f"item.{item_path.stem}"] = item
        if len(filler_items) < len(experimental_items):
            percentage = (
                len(filler_items) / (len(experimental_items) + len(filler_items))
            ) * 100
            warnings.warn(
                f"Fillers make up only {percentage:.1f}% of the items. "
                f"Consider adding more fillers to reach at least 50%."
            )
        conditions = set(next(iter(experimental_items.values())).keys())
        for item_id, item in experimental_items.items():
            item_conditions = set(item.keys())
            if set(item_conditions) != set(conditions):
                raise ValueError(
                    f"Item {item_id} has conditions {item_conditions}, expected {conditions}."
                )
        return experimental_items, practice_items, filler_items

    def _parse_item(self, item_string: str, filename: str) -> dict[str, Any]:
        """
        Parse a minimal-pair stimulus string into a dict containing the text and questions for each condition.

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
        current_subitem = {
            "questions": []
        }  # Holds text/questions for the current condition
        for match in matches:
            tag = match.group(1).strip()
            if re.search(r"\s", tag):
                raise ValueError(
                    f"Invalid tag <<{tag}>> in {filename}: tags cannot contain whitespace."
                )
            text = match.group(2).strip()

            # Question stem
            if tag == "question":
                if "text" not in current_subitem:
                    raise ValueError(
                        f"'<<question>>' tag found before any condition tag in {filename}."
                    )
                current_subitem["questions"].append(
                    {"stem": text, "options": None, "correct_option_index": None}
                )
            # Question options
            elif tag == "options":
                if not current_subitem["questions"]:
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
                current_subitem = {"text": text, "questions": []}
        # Final condition
        if current_condition is not None:
            item[current_condition] = current_subitem

        for condition, subitem in item.items():
            for question in subitem["questions"]:
                if not question["options"]:
                    raise ValueError(
                        f"Question '{question['stem']}' in {filename} has no options."
                    )

        return item
