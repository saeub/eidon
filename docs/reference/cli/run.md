---
generated: true
title: eidon run
parent: Command-line interface
layout: default
---

{% include toc.html %}

# CLI command: `eidon run`

Run a session from a built experiment. Collects eye-tracking data and logs.

## Usage

```
eidon run [-h] [--experiment EXPERIMENT] [--dummy]
                       [--participant-control] [--screen SCREEN]
                       [--start-from-stage START_FROM_STAGE]
                       session

Run a session from a built experiment. Collects eye-tracking data and logs.

positional arguments:
  session               Name of the session to run (without the .json file
                        extension).

options:
  -h, --help            show this help message and exit
  --experiment, -e EXPERIMENT
                        Path to the built experiment directory (must contain
                        experiment.json and sessions/).
  --dummy               Use mouse-based eye tracker for testing.
  --participant-control
                        Allow participant to control calibrations, drift
                        corrects, etc. (useful for testing).
  --screen SCREEN       Screen index to use for the experiment window.
  --start-from-stage START_FROM_STAGE
                        Start the session from the stage with the specified
                        name.
```
