---
generated: true
---

## CLI command: `setup`

Specify the hardware setup, including eye tracker model and stimulus area measurements. This is required before running a session for the first time, and has to be confirmed before every subsequent session.

### Usage

```
eidon setup [-h] [--screen SCREEN] [experiment_path]

Specify the hardware setup, including eye tracker model and stimulus area
measurements. This is required before running a session for the first time,
and has to be confirmed before every subsequent session.

positional arguments:
  experiment_path  Path to the built experiment directory (must contain
                   experiment.json and sessions/).

options:
  -h, --help       show this help message and exit
  --screen SCREEN  Screen index to use for the setup window.
```
