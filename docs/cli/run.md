## CLI command: `run`

Run a session from a built experiment. Collects eye-tracking data and logs.

### Usage

```
[1;34musage: [0m[1;35mgenerate.py run[0m [[32m-h[0m] [[36m--dummy[0m] [[36m--participant-control[0m] [[36m--recording-name [33mRECORDING_NAME[0m] [[36m--screen [33mSCREEN[0m] [[36m--start-from-stage [33mSTART_FROM_STAGE[0m] [32mpath[0m [32msession[0m

Run a session from a built experiment. Collects eye-tracking data and logs.

[1;34mpositional arguments:[0m
  [1;32mpath[0m                  Path to the built experiment directory (must contain experiment.json and sessions/).
  [1;32msession[0m               Name of the session to run (without the .json file extension).

[1;34moptions:[0m
  [1;32m-h[0m, [1;36m--help[0m            show this help message and exit
  [1;36m--dummy[0m               Use mouse-based eye tracker for testing.
  [1;36m--participant-control[0m
                        Allow participant to control calibrations, drift corrects, etc. (useful for testing).
  [1;36m--recording-name[0m [1;33mRECORDING_NAME[0m
                        Name for recording and log files.
  [1;36m--screen[0m [1;33mSCREEN[0m       Screen index to use for the experiment window.
  [1;36m--start-from-stage[0m [1;33mSTART_FROM_STAGE[0m
                        Start the session from the stage with the specified name.
```
