---
generated: true
---

## CLI command: `clean`

Clean gaze data by manually correcting drift or removing bad trials. Saves a JSON files with the applied corrections. These corrections can then be used to generate a cleaned gaze CSV file with the `--apply` flag.

### Usage

```
eidon clean [-h] [--areas AREAS] [--vertical] [--apply]
                         path [recording_names ...]

Clean gaze data by manually correcting drift or removing bad trials. Saves a
JSON files with the applied corrections. These corrections can then be used to
generate a cleaned gaze CSV file with the `--apply` flag.

positional arguments:
  path             Path to the experiment directory (must contain
                   recordings/).
  recording_names  Names of the recordings or sessions to clean (without a
                   file extension).

options:
  -h, --help       show this help message and exit
  --areas AREAS    Area types to display as a backdrop (e.g., 'word').
                   Requires building the experiment with --area-images.
  --vertical       Restrict corrections to vertical axis only (recommended for
                   reading experiments).
  --apply          Apply the corrections to the gaze data and save a new CSV
                   file (no GUI).
```
