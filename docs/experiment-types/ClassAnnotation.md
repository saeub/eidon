---
generated: true
---

## Experiment type: `ClassAnnotation`

Annotation experiment for text classification.

### Description

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

`instructions.txt`, `wait.txt`, `break.txt`, and `end.txt` contain the text for the
instructions, wait (after instructions and practice trials), break, and end pages. The
instructions are split into multiple pages if necessary.

#### Annotation items

`01.txt`, `02.txt`, etc. each represent one item to be annotated. The file names (without `.txt`)
are used as item IDs. Each file contains the text to be annotated.

#### Practice items

Practice items are optional and follow the same format as regular items. File names of practice
items must start with `practice.`.

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
      - "Not at all confident"
  - stem: "Which label would be your second choice?"
    options:
    - ...
```

### Configuration

- `display_size` (tuple[int, int])  
  Size of the display in pixels (width, height).
- `background_color` (tuple[int, int, int])  
  Color for window and stimulus backgrounds. (red, green, blue) with values from 0 to 255.  
  Default: `(204, 204, 204)`
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
  Font size for all text.  
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
  Key names are [pyglet key symbol strings](https://pyglet.readthedocs.io/en/latest/programming_guide/keyboard.html#defined-key-symbols) (e.g. `A`, `LEFT`, `SPACE`).
- `label_confirm_key` (str | None)  
  Key names are [pyglet key symbol strings](https://pyglet.readthedocs.io/en/latest/programming_guide/keyboard.html#defined-key-symbols) (e.g. `A`, `LEFT`, `SPACE`).  
  Default: `None`
- `questions` (list[dict[str, typing.Any]] | None)  
  List of multiple-choice questions to present after selecting a label. See [example above](#questions) for details.  
  Default: `None`
- `question_layout` (str)  
  Layout for multiple-choice questions. `horizontal` arranges options in a horizontal row, `diamond` arranges them in a diamond shape (requires exactly 4 options that are selected with the UP, LEFT, RIGHT, and DOWN keys), and `cursor` arranges them vertically with a cursor movable with the UP and DOWN keys (requires `question_confirm_key`).  
  Default: `cursor`
- `question_option_keys` (list[str] | None)  
  List of keys to use for selecting multiple-choice options, in order. For example, `[Y, N]` to use the Y key for the first option and the N key for the second option. Only required when question layout is `horizontal`.  
  Key names are [pyglet key symbol strings](https://pyglet.readthedocs.io/en/latest/programming_guide/keyboard.html#defined-key-symbols) (e.g. `A`, `LEFT`, `SPACE`).  
  Default: `None`
- `question_confirm_key` (str | None)  
  Key to use for confirming the selection of an option. If not specified, options are selected immediately when the corresponding option key is pressed.  
  Key names are [pyglet key symbol strings](https://pyglet.readthedocs.io/en/latest/programming_guide/keyboard.html#defined-key-symbols) (e.g. `A`, `LEFT`, `SPACE`).  
  Default: `SPACE`

### [Example](https://github.com/saeub/eidon/tree/main/examples/ClassAnnotation)
