---
generated: true
---

## Experiment type: `MultiPageReading`

Reading experiment with longer, multi-page text stimuli.

### Description

Each experimental item consists of a text and optionally one or more multiple-choice questions.
Each item may appear in multiple conditions, which are assigned to participants according to the
specified design (e.g., Latin square).

The main differences to `SinglePageReading` are:
- The text for each item can span multiple pages. The text is automatically split into pages
  when necessary. Explicit page breaks can also be added using `<<pagebreak>>`.
- The texts are vertically aligned to the top of the page (instead of centered).
- Filler items are not supported.

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
```

- `instructions.txt` contains the text for the instructions shown at the beginning of the experiment.
  The text is automatically split into multiple pages if necessary.
- `wait.txt` (optional) contains the text shown after the instructions and after the practice trials,
  where the participant waits for the experimenter to start the experiment. This is an opportunity
  for the participant to ask questions or for the experimenter to perform calibration if necessary.
- `break.txt` (optional) contains the text shown during breaks.
- `end.txt` contains the text shown at the end of the experiment.

#### Experimental items

`01.txt`, `02.txt`, etc. each represent one experimental item. The file names (without `.txt`)
are used as item IDs. Each file must follow the following format (values in [brackets] are
placeholders):

```
<<item>>
[text]
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

Page breaks can be added by inserting `<<pagebreak>>` in the text (on a separate line).

The number of questions can vary across items. Optionally, one answer option per question can be
marked with `**` to indicate that it is the correct answer.

`practice.txt` are optional and can contain any number of practice items, which follow a similar
format (but without conditions):

#### Practice items

```
<<practice>>
[text for practice item 1]
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

<<practice>>
[text for practice item 2]
...
```

#### Areas of interest

Areas of interest can be defined in the text by surrounding them with
[[area-name]]...[[/area-name]]. For example:

```
<<item>>
[[subject]]The quick brown fox[[/subject]] jumps over [[object]]the lazy dog[[/object]].
```

An item can contain any number of areas of interest. Discontinuous areas can be defined by
using multiple tags with the same area name.

### Configuration

- `stimulus_area_size` (tuple[int, int])  
  Size of the rectangular stimulus area in pixels (width, height). The rectangle will be centered in the screen and all stimuli will be presented inside it. The area needs to be within the trackable range of your eye tracker. The area cannot be larger than the resolution of your monitor.
- `background_color` (tuple[int, int, int])  
  Color for window and stimulus backgrounds. (red, green, blue) with values from 0 to 255.  
  Default: `(204, 204, 204)`
- `num_participants` (int)  
  Number of participants in the experiment. Should be a multiple of the number of conditions.
- `conditions` (list[str] | None)  
  List of item condition names (if any).  
  Default: `None`
- `design` (str)  
  Name of the design to use for assigning items to participants.  
  Available designs are documented [here](designs.md).  
  Default: `latin_square`
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
- `question_layout` (str)  
  Layout for multiple-choice questions. `horizontal` arranges options in a horizontal row, `diamond` arranges them in a diamond shape (requires exactly 4 options that are selected with the UP, LEFT, RIGHT, and DOWN keys), and `cursor` arranges them vertically with a visual selector that can be controlled with the UP and DOWN keys (requires `confirm_key`).  
  Default: `horizontal`
- `option_keys` (list[str] | None)  
  List of keys to use for selecting multiple-choice options, in order. For example, `[Y, N]` to use the Y key for the first option and the N key for the second option. Only required when question layout is `horizontal`.  
  Available key names are listed [here](../keyboard.md).  
  Default: `None`
- `confirm_key` (str | None)  
  Key to use for confirming the selection of an option. If not specified, options are selected immediately when the corresponding option key is pressed.  
  Available key names are listed [here](../keyboard.md).  
  Default: `None`

### [Example](https://github.com/saeub/eidon/tree/main/examples/MultiPageReading)
