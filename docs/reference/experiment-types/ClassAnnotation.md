---
generated: true
title: ClassAnnotation
parent: Experiment types
layout: default
---

{% include toc.html %}

# Experiment type: `ClassAnnotation`

Annotation experiment for text classification.

## Description

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

## Configuration

The following configuration parameters can be set in the `config.yaml` file:

- `stimulus_area_size` (tuple[int, int])  
  Size of the rectangular stimulus area in pixels (width, height). The rectangle will be centered in the screen and all stimuli will be presented inside it. The area needs to be within the trackable range of your eye tracker. The area cannot be larger than the resolution of your monitor.
- `background_color` (tuple[int, int, int])  
  Color for window and stimulus backgrounds. (red, green, blue) with values from 0 to 255.  
  Default: `(204, 204, 204)`
- `MATERIALS_SCHEMA` (ClassVar[dict[str, dict[str, Any]]] | None)  
  Default: `None`
- `num_participants` (int)  
  Number of participants in the experiment. Should be a multiple of the number of conditions.
- `breaks_after` (int | None)  
  Insert a break after every N items.  
  Default: `None`
- `margin` (int)  
  Margin in pixels around the text on the stimulus pages.  
  Default: `50`
- `font_monospaced` (bool)  
  Whether to use a monospaced font for the stimuli. This is recommended when controlling for word length effects.  
  Default: `False`
- `font_size` (int)  
  Font size in pixels for all text.  
  Default: `25`
- `line_spacing` (int)  
  Line spacing multiplier for all text.  
  Default: `2.0`
- `labels` (list[str])  
  Names of the labels to choose from.
- `label_texts` (list[str] | None)  
  Texts to display for each label. If not provided, the label names are used.  
  Default: `None`
- `label_option_keys` (list[str] | None)  
  List of keys to use for selecting a label, in order. For example, `[Y, N]` to use the Y key for the first label and the N key for the second label.  
  Available key names are listed [here](../keyboard).
- `label_confirm_key` (str | None)  
  Available key names are listed [here](../keyboard).  
  Default: `None`
- `questions` (list[dict[str, typing.Any]] | None)  
  List of multiple-choice questions to present after selecting a label. See [example above](#questions) for details.  
  Default: `None`
- `question_layout` (str)  
  Layout for multiple-choice questions. `horizontal` arranges options in a horizontal row, `diamond` arranges them in a diamond shape (requires exactly 4 options that are selected with the UP, LEFT, RIGHT, and DOWN keys), and `cursor` arranges them vertically with a visual selector that can be controlled with the UP and DOWN keys (requires `question_confirm_key`).  
  Default: `cursor`
- `question_option_keys` (list[str] | None)  
  List of keys to use for selecting multiple-choice options, in order. For example, `[Y, N]` to use the Y key for the first option and the N key for the second option. Only required when question layout is `horizontal`.  
  Available key names are listed [here](../keyboard).  
  Default: `None`
- `question_confirm_key` (str | None)  
  Key to use for confirming the selection of an option. If not specified, options are selected immediately when the corresponding option key is pressed.  
  Available key names are listed [here](../keyboard).  
  Default: `SPACE`

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
  Table of experimental items, one row per item.  
  <details><summary>Columns</summary><ul>

  <li>
    <code>id</code> (str) <strong>(required)</strong><br/>
    Unique identifier for the item.
  </li>

  <li>
    <code>text</code> (str) <strong>(required)</strong><br/>
    Stimulus text to be displayed.
  </li>

  </ul>
  </details>
- <a id="materials-items-practice-csv" />`items/practice.csv`  
  Table of practice items, one row per item.   
  <details><summary>Columns</summary><ul>

  <li>
    <code>id</code> (str) <strong>(required)</strong><br/>
    Unique identifier for the item.
  </li>

  <li>
    <code>text</code> (str) <strong>(required)</strong><br/>
    Stimulus text to be displayed.
  </li>

  </ul>
  </details>

## [Example](https://github.com/saeub/eidon/tree/main/examples/ClassAnnotation)
