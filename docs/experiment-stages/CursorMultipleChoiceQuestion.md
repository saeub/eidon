---
generated: true
---

## Experiment stage: `CursorMultipleChoiceQuestion`

Shows an image stimulus and allows selecting a response option by moving a cursor.

### Configuration

- `imgpath` (str)  
  Path to the image file to display, relative to the experiment's root directory.
- `cursor_locations` (list[tuple[float, float]])  
  A list of (x, y) locations in pixels for the cursor positions of each answer option.
- `cursor_size` (float)  
  The diameter of the cursor in pixels.
- `next_option_key` (str)  
  The key that moves the cursor to the next option.  
  Key names are [pyglet key symbol strings](https://pyglet.readthedocs.io/en/latest/programming_guide/keyboard.html#defined-key-symbols) (e.g. `A`, `LEFT`, `SPACE`).
- `prev_option_key` (str)  
  The key that moves the cursor to the previous option.  
  Key names are [pyglet key symbol strings](https://pyglet.readthedocs.io/en/latest/programming_guide/keyboard.html#defined-key-symbols) (e.g. `A`, `LEFT`, `SPACE`).
- `confirm_key` (str)  
  The key that confirms the current selection.  
  Key names are [pyglet key symbol strings](https://pyglet.readthedocs.io/en/latest/programming_guide/keyboard.html#defined-key-symbols) (e.g. `A`, `LEFT`, `SPACE`).
- `option_values` (list[str] | None)  
  The values for each answer option that will be returned and logged. By default, the option indices are used as values.
