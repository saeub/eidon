---
generated: true
---

## Experiment stage: `LabelAnnotation`

Shows an image stimulus and allows selecting a label.

### Configuration

- `imgpath` (str)  
  Path to the image file to display, relative to the experiment's root directory.
- `label_boxes` (dict[str, tuple[float, float, float, float]])  
  An object mapping label names to rectangles (x, y, width, height) in pixels where the labels are located.
- `label_keys` (dict[str, str])  
  An object mapping keys to label names.  
  Available key names are listed [here](../keyboard.md).
- `confirm_key` (str | None)  
  The key to press to confirm the selected label. If not provided, the label is confirmed immediately when a label key is pressed.  
  Available key names are listed [here](../keyboard.md).
