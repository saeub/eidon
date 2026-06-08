## Experiment stage: `MultipleChoiceQuestion`

Shows an image stimulus and allows selecting a response option by pressing a key.

### Configuration

- `imgpath` (str)  
  Path to the image file to display, relative to the experiment's root directory.
- `option_keys` (list[str])  
  The keys to select each answer option.
- `option_values` (list[str] | None)  
  The values for each answer option that will be returned and logged. By default, the option indices are used as values.
- `correct_option_index` (int | None)  
  The index of the correct answer option. This does not affect the presentation, but is logged for convenience.
