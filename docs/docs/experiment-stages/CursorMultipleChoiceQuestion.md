---
generated: true
title: CursorMultipleChoiceQuestion
parent: Experiment stages
layout: default
---

{% include toc.html %}

# Experiment stage: `CursorMultipleChoiceQuestion`

Shows an image stimulus and allows selecting a response option by moving a cursor.

## Configuration

- `imgpath` (str)  
  Path to the image file to display, relative to the experiment's root directory.
- `cursor_locations` (list[tuple[float, float]])  
  A list of (x, y) locations in pixels for the cursor positions of each answer option.
- `cursor_size` (float)  
  The diameter of the cursor in pixels.
- `next_option_key` (str)  
  The key that moves the cursor to the next option.  
  Available key names are listed [here](/docs/keyboard).
- `prev_option_key` (str)  
  The key that moves the cursor to the previous option.  
  Available key names are listed [here](/docs/keyboard).
- `confirm_key` (str)  
  The key that confirms the current selection.  
  Available key names are listed [here](/docs/keyboard).
- `option_values` (list[str] | None)  
  The values for each answer option that will be returned and logged. By default, the option indices are used as values.
- `correct_option_index` (int | None)  
  The index of the correct answer option. This does not affect the presentation, but is logged for convenience.
