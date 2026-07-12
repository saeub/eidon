---
title: Getting started
layout: default
nav_order: 1
---

# Getting started

This page will show you how to set up and run your first eye-tracking experiment with _eidon_.

## Installing the package

The easiest way to install _eidon_ is using `pip`:

```bash
pip install eidon
```

> **NOTE:** On Mac, you will first have to install the [portaudio library](https://portaudio.com/). For example, using Homebrew: `brew install portaudio`

## Building and running an example experiment

Download one of the [example experiments](https://github.com/saeub/eidon/tree/main/examples) and place the folder in your working directory. You can use this link to download a ZIP archive of the `SinglePageReading` example:

https://download-directory.github.io/?url=https://github.com/saeub/eidon/tree/main/examples/SinglePageReading

In your terminal, navigate into the experiment directory (where `config.yaml` is located). Then build the experiment using this command:

```bash
eidon build
```

Then run the session for participant `P1` in dummy mode:

```bash
eidon run P1 --dummy
```

> Dummy mode means that you won't need an eye tracker to test the experiment.

## Implementing your first experiment

To implement your own experiment, you first need to find the [experiment type](docs/experiment-types) that matches your use case. For this tutorial, we'll use the [`SinglePageReading`](docs/experiment-types/SinglePageReading) experiment type.

### 1. Create an experiment folder and a configuration file

First, create a folder and a `config.yaml` file for your experiment:

```
📂 my_experiment
└─ config.yaml
```

```yaml
# config.yaml
name: "my-experiment"
type: SinglePageReading

stimulus_area_size: [1100, 900]
num_participants: 8
option_keys: [Y, N]
```

The experiment's `name` will appear, among others, in recordings and metadata files.

`stimulus_area_size` defines the width and height (in pixels) of the area where your stimuli will be presented. It is important that this is within your eye tracker's **trackable area** on the screen you're going to use for the experiment. You can use `eidon setup` to test this -- see [below](#2-record-the-hardware-setup).

`option_keys` are the keys on the keyboard that participants are going to use to respond to multiple-choice questions (in this case, we are going to use yes/no questions).

This example is a very bare-bones configuration file. Check the [documentation page for `SinglePageReading`](docs/experiment-types/SinglePageReading) for more configuration options.

### 2. Create stimuli

The [documentation page for `SinglePageReading`](docs/experiment-types/SinglePageReading) tells you the structure and format you need to use for your stimuli:

```
📂 my_experiment
├─ config.yaml
└─ 📂 materials
   ├─ 📄 instructions.txt
   ├─ 📄 break.txt
   ├─ 📄 end.txt
   └─ 📂 items
      ├─ 📄 01.txt
      ├─ 📄 02.txt
      ├─ 📄 03.txt
      ├─ 📄 ...
      └─ 📄 fillers.txt (optional)
```

`instructions.txt`, `break.txt`, and `end.txt` simply contain the text you want to display before/after the experiment and during breaks. The item files `01.txt`, `02.txt`, etc. contain one item each (in different conditions) and need to be structured as follows:

```
<<active>>
My neighbor's friend stole a candy bar.
<<question>>
Did the neighbor steal the candy bar?
<<options>>
yes
**no

<<passive>>
A candy bar was stolen by my neighbor's friend.
<<question>>
Did the neighbor steal the candy bar?
<<options>>
yes
**no
```

Here, we have an item in two conditions (`active` and `passive`) with one comprehension question each. The asterisks `**` indicate the correct answer.

Check the [example experiment](https://github.com/saeub/eidon/tree/main/examples/SinglePageReading/materials/items) for more examples of item files.

### 3. Build the experiment

To build your experiment, navigate into the `my_experiment` folder and run:

```bash
eidon build
```

where `my_experiment` is the path to your experiment folder. This will generate the stimulus images, AOI files, and session files:

```
📂 my_experiment
├─ config.yaml
├─ experiment.json
├─ 📁 materials
├─ 📂 stimuli
│  ├─ 🖼️ instructions.0.png
│  ├─ 📄 instructions.0.char.csv
│  ├─ 📄 instructions.0.word.csv
│  ├─ 🖼️ item.01.active.png
│  ├─ 📄 item.01.active.char.csv
│  ├─ 📄 item.01.active.word.csv
│  ├─ 🖼️ item.01.passive.png
│  ├─ 📄 item.01.passive.char.csv
│  ├─ 📄 item.01.passive.word.csv
│  └─ 🖼️ ...
└─ 📂 sessions
   ├─ 📄 P1.json
   ├─ 📄 P2.json
   └─ 📄 ...
```

### 4. Run the experiment

To run a session of your experiment, run:

```bash
eidon run P1 --dummy
```

where `P1` is the name of a session file (without `.json`).

> **NOTE:** You can abort the experiment using <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>Escape</kbd>.

This will create a recording directory under `my_experiment/recordings` containing the log file (this is where the question responses are) and eye-tracking data (except when in dummy mode):

```
📂 my_experiment
├─ config.yaml
├─ experiment.json
├─ 📁 materials
├─ 📁 stimuli
├─ 📁 sessions
└─ 📂 recordings
   └─ 📂 my-experiment.P1.20260710-140345
      └─ 📄 my-experiment.P1.20260710-140345.log
```

## Using a real eye tracker

### 1. Install `pylink`

Currently, only EyeLink devices by SR Research are supported. To connect to an EyeLink eye tracker, you first need to install `pylink`:

```bash
pip install sr-research-pylink
```

> **NOTE:** At the time of writing, `pylink` only supports version Python 3.12. If the installation fails, make sure are using the correct Python version (`python --version`).

### 2. Record the hardware setup

When you run a session for the first time, you will be required to take a few measurements, including the size of the stimulus area and the eye-to-screen distance. This will make sure that your stimuli are presented within the trackable range of your eye tracker. Running this command from the root directory of your experiment will guide you through all of the settings:

```bash
eidon setup
```

Before each subsequent session, you will be asked to confirm if the previous setup is still accurate. If any of the measurements have changed, you will be prompted to re-enter them.

The setup configurations are stored in the `setups` directory of your experiment:

```
📂 my_experiment
├─ config.yaml
├─ experiment.json
├─ 📁 materials
├─ 📁 stimuli
├─ 📁 sessions
└─ 📂 setups
   └─ 📄 setup.20260710-165614.json
```

### 3. Run a session

While connected to the eye tracker, navigate to the root directory of your experiment and run:

```bash
eidon run P1
```

### 4. Convert the recordings

After completing a session, the EDF file will automatically be transferred to a directory under `my_experiment/recordings`. To convert the EDF file to a more interoperable format, use the ["EDF Converter" tool by SR Research](https://www.sr-research.com/support/thread-7674.html). After converting the `.edf` to a `.asc` file, run the following command from the root directory of your experiment:

```bash
eidon convert
```

This will convert all `.asc` files to `.csv` files, which can be opened by all major data analysis software packages. It will also generate a `.json` file containing metadata like calibration errors.

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
      └─ 📄 my-experiment.P1.20260710-172305.log
```

## Learn more

Congratulations, you've mastered the basics of _eidon_!

As a next step, you can:

- Learn how to [inspect and manually correct recordings](guide/cleaning) using `eidon clean`.
- Learn how to [create your own experiment type](guide/custom-experiment-type) using Python code. This gives you maximum control over the experimental procedure.
