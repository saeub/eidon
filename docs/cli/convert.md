---
generated: true
---

## CLI command: `convert`

Convert eye-tracking recordings to a CSV file and extract metadata into a JSON file.

### Usage

```
eidon convert [-h]
                           [--recording-names RECORDING_NAMES [RECORDING_NAMES ...]]
                           path

Convert eye-tracking recordings to a CSV file and extract metadata into a JSON
file.

positional arguments:
  path                  Path to the experiment directory (must contain
                        recordings/).

options:
  -h, --help            show this help message and exit
  --recording-names RECORDING_NAMES [RECORDING_NAMES ...]
                        Names of the recordings to convert (without the .asc
                        file extension). If not provided, all recordings will
                        be converted.
```
