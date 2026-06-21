---
generated: true
---

## Experiment stage: `FreeTextQuestion`

Shows an image stimulus and allows entering a free text response.

### Configuration

- `imgpath` (str)  
  Path to the image file to display, relative to the experiment's root directory.
- `input_box` (tuple[float, float, float, float])  
  A rectangle (x, y, width, height) in pixels defining the location of the text input box.
- `font_size` (int)
- `confirm_key` (str)  
  The key to press to confirm the entered text.  
  Key names are [pyglet key symbol strings](https://pyglet.readthedocs.io/en/latest/programming_guide/keyboard.html#defined-key-symbols) (e.g. `A`, `LEFT`, `SPACE`).
- `multiline` (bool)  
  Default: `False`
