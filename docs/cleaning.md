## Cleaning eye-tracking recordings

_eidon_ provides a graphical user interface for inspecting and manually correcting eye-tracking data. For this guide, we will assume that you have recorded some eye-tracking as described in the [getting started guide](getting-started.md). Your experiment folder should look similar to this:

```
📂 my_experiment
├─ config.yaml
├─ experiment.json
├─ 📁 materials
├─ 📁 stimuli
├─ 📁 sessions
├─ 📁 setups
└─ 📂 recordings
   └─ 📂 my-experiment.P1.20260710-172305
      ├─ 📄 my-experiment.P1.20260710-172305.edf
      ├─ 📄 my-experiment.P1.20260710-172305.asc
      ├─ 📄 my-experiment.P1.20260710-172305.csv
      └─ 📄 my-experiment.P1.20260710-172305.log
```

### Using the cleaning interface

From the root directory of your experiment, run:

```bash
eidon clean P1 --vertical
```

The `--vertical` flag means that you'll only be able to do vertical drift corrections. This is highly recommended for reading experiments, as judging horizontal drift visually is not feasible.

This will open a window where you can flip through every screen of your experiment and inspect the data. Use these keys to navigate and edit:

| Key                            | Meaning                      |
| ------------------------------ | ---------------------------- |
| <kbd>→</kbd> (right arrow key) | Go to the next screen        |
| <kbd>←</kbd> (left arrow key)  | Go to the previous screen    |
| <kbd>←</kbd> (left arrow key)  | Go to the previous screen    |
| <kbd>X</kbd>                   | Remove data from this screen |
| <kbd>Ctrl</kbd>+<kbd>Z</kbd>   | Undo                         |
| <kbd>ESCAPE</kbd>              | Save and exit                |

You can click and drag the blue dots to move and warp the gaze data on this screen. This applies a [thin-plate spline transformation](https://scikit-image.org/docs/stable/auto_examples/transform/plot_tps_deformation.html) to the gaze coordinates. If the data on a screen is not rescuable, you can exclude it using the <kbd>X</kbd> key -- this will set the gaze coordinates for these samples to `null`.

While correcting drift, it is often useful to visualize areas of interest. After (re-)building your experiment with the [`--area-images` flag](cli/build.md), you can specify the area types to visualize in `eidon clean`. For example, to see word-level areas of interest:

```bash
eidon clean P1 --vertical --areas word
```

Note that any corrections you make in the interface are **not** immediately applied to the gaze CSV file. Instead, they are stored in a JSON file in the recording directory:

```
📂 my_experiment
├─ config.yaml
├─ experiment.json
├─ 📁 materials
├─ 📁 stimuli
├─ 📁 sessions
├─ 📁 setups
└─ 📂 recordings
   └─ 📂 my-experiment.P1.20260710-172305
      ├─ 📄 my-experiment.P1.20260710-172305.edf
      ├─ 📄 my-experiment.P1.20260710-172305.asc
      ├─ 📄 my-experiment.P1.20260710-172305.json
      ├─ 📄 my-experiment.P1.20260710-172305.csv
      ├─ 📄 my-experiment.P1.20260710-172305.corrections.json
      └─ 📄 my-experiment.P1.20260710-172305.log
```

### Applying the corrections

To apply the manual corrections, run:

```bash
eidon clean --apply
```

This will generate a new gaze CSV file for each recording that has a corrections file:

```
📂 my_experiment
├─ config.yaml
├─ experiment.json
├─ 📁 materials
├─ 📁 stimuli
├─ 📁 sessions
├─ 📁 setups
└─ 📂 recordings
   └─ 📂 my-experiment.P1.20260710-172305
      ├─ 📄 my-experiment.P1.20260710-172305.edf
      ├─ 📄 my-experiment.P1.20260710-172305.asc
      ├─ 📄 my-experiment.P1.20260710-172305.json
      ├─ 📄 my-experiment.P1.20260710-172305.csv
      ├─ 📄 my-experiment.P1.20260710-172305.corrections.json
      ├─ 📄 my-experiment.P1.20260710-172305.clean.csv
      └─ 📄 my-experiment.P1.20260710-172305.log
```

> **NOTE:** Make sure to keep the original version and the corrections file and include them when publishing your dataset. This increases transparency (reporting data quality) and reusability of the dataset for other purposes (e.g., automatic gaze correction). See [Jakobi et al. (2024)](https://doi.org/10.1145/3649902.3655658) for more information.

### Further cleaning steps

Depending on your use case, further processing is likely necessary, for example:

- Removing blinks
- Detecting fixations and other events
- Analyzing data quality
- ...

The Python package [pymovements](https://pymovements.readthedocs.io/en/stable/index.html) can be used for these steps.
