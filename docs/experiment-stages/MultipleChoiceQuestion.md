---
generated: true
---

## Experiment stage: `MultipleChoiceQuestion`

Shows an image stimulus and allows selecting a response option by pressing a key.

### Configuration

- `imgpath` (str)  
  Path to the image file to display, relative to the experiment's root directory.
- `option_keys` (list[str])  
  The keys to select each answer option.  
  Key names are [pyglet key symbol strings](https://pyglet.readthedocs.io/en/latest/programming_guide/keyboard.html#defined-key-symbols) (e.g. `A`, `LEFT`, `SPACE`).
- `option_values` (list[str] | None)  
  The values for each answer option that will be returned and logged. By default, the option indices are used as values.
- `correct_option_index` (int | None)  
  The index of the correct answer option. This does not affect the presentation, but is logged for convenience.
- `option_boxes` (list[tuple[float, float, float, float]] | None)  
  A list of rectangles (x, y, width, height) in pixels defining the location of each answer options on the stimulus image. When `confirm_key` is provided, this is used to show a box around the currently selected option.
- `confirm_key` (str | None)  
  The key to press to confirm the selected answer option. If not provided, the answer is confirmed immediately when an option key is pressed. Requires `option_boxes` to be defined.  
  Key names are [pyglet key symbol strings](https://pyglet.readthedocs.io/en/latest/programming_guide/keyboard.html#defined-key-symbols) (e.g. `A`, `LEFT`, `SPACE`).
