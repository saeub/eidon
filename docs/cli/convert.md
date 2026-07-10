---
generated: true
---

## CLI command: `convert`

Convert EyeLink recordings (.asc files) to a CSV file and extract metadata into a JSON file.

### Usage

```
eidon convert [-h] [--experiment EXPERIMENT]
                           [recording_names ...]

Convert EyeLink recordings (.asc files) to a CSV file and extract metadata
into a JSON file.

positional arguments:
  recording_names       Names of the recordings or sessions to convert
                        (without the .asc file extension). If not provided,
                        all recordings will be converted.

options:
  -h, --help            show this help message and exit
  --experiment, -e EXPERIMENT
                        Path to the experiment directory (must contain
                        experiment.json and recordings/).
```
