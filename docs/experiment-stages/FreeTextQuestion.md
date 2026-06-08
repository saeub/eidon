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
- `multiline` (bool)  
  Default: `False`
