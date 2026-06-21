---
generated: true
---

## CLI command: `run`

Run a session from a built experiment. Collects eye-tracking data and logs.

### Usage

```
eidon run [-h] [--dummy] [--participant-control]
                       [--recording-name RECORDING_NAME] [--screen SCREEN]
                       [--start-from-stage START_FROM_STAGE]
                       path session

Run a session from a built experiment. Collects eye-tracking data and logs.

positional arguments:
  path                  Path to the built experiment directory (must contain
                        experiment.json and sessions/).
  session               Name of the session to run (without the .json file
                        extension).

options:
  -h, --help            show this help message and exit
  --dummy               Use mouse-based eye tracker for testing.
  --participant-control
                        Allow participant to control calibrations, drift
                        corrects, etc. (useful for testing).
  --recording-name RECORDING_NAME
                        Name for recording and log files.
  --screen SCREEN       Screen index to use for the experiment window.
  --start-from-stage START_FROM_STAGE
                        Start the session from the stage with the specified
                        name.
```
