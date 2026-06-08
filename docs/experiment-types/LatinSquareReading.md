## Experiment type: `LatinSquareReading`

Reading experiment with single-page minimal-pair stimuli and a Latin square design.

### Description

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

### Configuration

- `display_size` (tuple[int, int])
- `background_color` (tuple[int, int, int])  
  Default: `(204, 204, 204)`
- `num_participants` (int)  
  Number of participants in the experiment. Should be a multiple of the number of conditions.
- `option_keys` (list[str])  
  List of keys to use for selecting multiple-choice options, in order. For example, ["Y", "N"] to use the Y key for the first option and N key for the second option.
- `margin` (int)  
  Margin in pixels around the text on the stimulus pages.  
  Default: `50`
- `font_monospaced` (bool)  
  Whether to use a monospaced font for the stimuli. This is recommended when controlling for word length effects.  
  Default: `True`
- `font_size` (int)  
  Font size for all text.  
  Default: `25`
- `line_spacing` (int)  
  Line spacing multiplier for all text.  
  Default: `2.0`
- `breaks_after` (int | None)  
  Insert a break after every N items.  
  Default: `None`

### [Example](https://github.com/saeub/eidon/tree/main/examples/LatinSquareReading)
