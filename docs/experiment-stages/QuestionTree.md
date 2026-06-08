## Experiment stage: `QuestionTree`

Shows a series of question stages, where each stage is based on previous responses.

### Configuration

- `tree` (dict[str, typing.Any])  
  A nested object defining the question tree, for example: {     "$type": "MultipleChoiceQuestion",     "imgpath": ...,     "branches": {         "0": { "$type": "FreeTextQuestion", ..., "branches": { ... } },         "1": { "$type": "MultipleChoiceQuestion", ..., "branches": { ... } },         ...     } }
