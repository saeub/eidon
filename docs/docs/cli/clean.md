---
generated: true
title: eidon clean
parent: Command-line interface
layout: default
---

{% include toc.html %}

# CLI command: `eidon clean`

Clean gaze data by manually correcting drift or removing bad trials. Saves a JSON files with the applied corrections. These corrections can then be used to generate a cleaned gaze CSV file with the `--apply` flag.

## Usage

```
eidon clean [-h] [--experiment EXPERIMENT] [--areas AREAS]
                         [--apply]
                         [recording_names ...]

Clean gaze data by manually correcting drift or removing bad trials. Saves a
JSON files with the applied corrections. These corrections can then be used to
generate a cleaned gaze CSV file with the `--apply` flag.

positional arguments:
  recording_names       Names of the recordings or sessions to clean (without
                        a file extension).

options:
  -h, --help            show this help message and exit
  --experiment, -e EXPERIMENT
                        Path to the experiment directory (must contain
                        experiment.json and recordings/).
  --areas AREAS         Area types to display as a backdrop (e.g., 'word').
                        Requires building the experiment with --area-images.
  --apply               Apply the corrections to the gaze data and save a new
                        CSV file (no GUI).
```
