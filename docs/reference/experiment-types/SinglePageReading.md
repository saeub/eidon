---
generated: true
title: SinglePageReading
parent: Experiment types
layout: default
---

{% include toc.html %}

# Experiment type: `SinglePageReading`

Reading experiment with short, single-page text stimuli.

## Description

Each experimental item consists of a text and optionally one or more multiple-choice questions.
Each item may appear in multiple conditions, which are assigned to participants according to the
specified design (e.g., Latin square). Practice and filler items can also be added.

### Items

There are three types of items: experimental, practice, and filler. **Experimental items**
constitute the main stimuli of the experiment. **Practice items** are presented before the
experimental items to familiarize participants with the task. **Filler items** are randomly
interspersed with the experimental items to reduce predictability.

Items are defined in CSV files (see [below](#files)).

### Areas of interest

Areas of interest can be defined in the `text` column by surrounding them with
`[[area-name]]...[[/area-name]]`. For example:

```
[[subject]]The quick brown fox[[/subject]] jumps over [[object]]the lazy dog[[/object]].
```

An item can contain any number of areas of interest. Discontinuous areas can be defined by
using multiple tags with the same area name.

## Files 

- `my_experiment`
  - [`config.yaml`](#configuration)
  - `materials/`
    - [`instructions.txt`](#materials-instructions-txt)
    - [`wait.txt`](#materials-wait-txt)
    - [`break.txt`](#materials-break-txt)
    - [`end.txt`](#materials-end-txt)
    - `items/`
      - [`experimental.csv`](#materials-items-experimental-csv)
      - [`practice.csv`](#materials-items-practice-csv)
      - [`filler.csv`](#materials-items-filler-csv)

## Configuration

The following configuration parameters can be set in the `config.yaml` file:

- `experiment_path` (Path)  
  Path to the experiment directory.
- `stimulus_area_size` (tuple[int, int])  
  Size of the rectangular stimulus area in pixels (width, height). The rectangle will be centered in the screen and all stimuli will be presented inside it. The area needs to be within the trackable range of your eye tracker. The area cannot be larger than the resolution of your monitor.
- `background_color` (tuple[int, int, int])  
  Color for window and stimulus backgrounds. (red, green, blue) with values from 0 to 255.  
  Default: `(204, 204, 204)`
- `MATERIALS_SCHEMA` (ClassVar[dict[str, dict[str, Any]]] | None)  
  Default: `None`
- `num_participants` (int)  
  Number of participants in the experiment. Should be a multiple of the number of conditions.
- `conditions` (list[str] | None)  
  List of item condition names (if any).  
  Default: `None`
- `design` (str)  
  Name of the design to use for assigning items to participants.  
  Available designs are documented [here](../designs).  
  Default: `latin_square`
- `breaks_after` (int | None)  
  Insert a break after every N items.  
  Default: `None`
- `margin` (int)  
  Margin in pixels around the text on the stimulus pages.  
  Default: `50`
- `font_monospaced` (bool)  
  Whether to use a monospaced font for the stimuli. This is recommended when controlling for word length effects.  
  Default: `True`
- `font_size` (int)  
  Font size in pixels for all text.  
  Default: `25`
- `line_spacing` (int)  
  Line spacing multiplier for all text.  
  Default: `2.0`
- `question_layout` (str)  
  Layout for multiple-choice questions. `horizontal` arranges options in a horizontal row, `diamond` arranges them in a diamond shape (requires exactly 4 options that are selected with the UP, LEFT, RIGHT, and DOWN keys), and `cursor` arranges them vertically with a visual selector that can be controlled with the UP and DOWN keys (requires `confirm_key`).  
  Default: `horizontal`
- `option_keys` (list[str] | None)  
  List of keys to use for selecting multiple-choice options, in order. For example, `[Y, N]` to use the Y key for the first option and the N key for the second option. Only required when question layout is `horizontal`.  
  Available key names are listed [here](../keyboard).  
  Default: `None`
- `confirm_key` (str | None)  
  Key to use for confirming the selection of an option. If not specified, options are selected immediately when the corresponding option key is pressed.  
  Available key names are listed [here](../keyboard).  
  Default: `None`

## Materials

The following files can be included in the `materials/` directory:

- <a id="materials-instructions-txt" />`instructions.txt` **(required)**  
  Text for the instructions shown at the beginning of the experiment.
- <a id="materials-wait-txt" />`wait.txt`  
  Text shown after the instructions and practice trials, while waiting for the experimenter to start the experimental trials.
- <a id="materials-break-txt" />`break.txt`  
  Text shown during breaks.
- <a id="materials-end-txt" />`end.txt` **(required)**  
  Text shown at the end of the experiment.
- <a id="materials-items-experimental-csv" />`items/experimental.csv` **(required)**  
  Table of experimental items, one row per item per condition.  
  <details><summary>Columns</summary><ul>

  <li>
    <code>id</code><br/>
    Unique identifier for the item.
  </li>

  <li>
    <code>text</code><br/>
    Stimulus text to be displayed.
  </li>

  <li>
    <code>question.#.stem</code><br/>
    Stem of the #-th multiple-choice question (starting at 0: <code>question.0.stem</code>, <code>question.1.stem</code>, ...).
  </li>

  <li>
    <code>question.#.option.#</code><br/>
    #-th answer option for the #-th question (starting at 0: <code>question.0.option.0</code>, <code>question.0.option.1</code>, ...).
  </li>

  <li>
    <code>question.#.correct_option_index</code><br/>
    Index of the correct answer option for the #-th question (starting at 0: <code>question.0.correct_option_index</code>, <code>question.1.correct_option_index</code>, ...).
  </li>

  <li>
    <code>condition</code><br/>
    Name of the experimental condition. Only required if config.yaml specifies multiple conditions.
  </li>

  </ul>
  </details>
- <a id="materials-items-practice-csv" />`items/practice.csv`  
  Table of practice items, one row per item. Practice items do not support multiple conditions.  
  <details><summary>Columns</summary><ul>

  <li>
    <code>id</code><br/>
    Unique identifier for the item.
  </li>

  <li>
    <code>text</code><br/>
    Stimulus text to be displayed.
  </li>

  <li>
    <code>question.#.stem</code><br/>
    Stem of the #-th multiple-choice question (starting at 0: <code>question.0.stem</code>, <code>question.1.stem</code>, ...).
  </li>

  <li>
    <code>question.#.option.#</code><br/>
    #-th answer option for the #-th question (starting at 0: <code>question.0.option.0</code>, <code>question.0.option.1</code>, ...).
  </li>

  <li>
    <code>question.#.correct_option_index</code><br/>
    Index of the correct answer option for the #-th question (starting at 0: <code>question.0.correct_option_index</code>, <code>question.1.correct_option_index</code>, ...).
  </li>

  </ul>
  </details>
- <a id="materials-items-filler-csv" />`items/filler.csv`  
  Table of filler items, one row per item. Filler items do not support multiple conditions.  
  <details><summary>Columns</summary><ul>

  <li>
    <code>id</code><br/>
    Unique identifier for the item.
  </li>

  <li>
    <code>text</code><br/>
    Stimulus text to be displayed.
  </li>

  <li>
    <code>question.#.stem</code><br/>
    Stem of the #-th multiple-choice question (starting at 0: <code>question.0.stem</code>, <code>question.1.stem</code>, ...).
  </li>

  <li>
    <code>question.#.option.#</code><br/>
    #-th answer option for the #-th question (starting at 0: <code>question.0.option.0</code>, <code>question.0.option.1</code>, ...).
  </li>

  <li>
    <code>question.#.correct_option_index</code><br/>
    Index of the correct answer option for the #-th question (starting at 0: <code>question.0.correct_option_index</code>, <code>question.1.correct_option_index</code>, ...).
  </li>

  </ul>
  </details>

## [Example](https://github.com/saeub/eidon/tree/main/examples/SinglePageReading)
