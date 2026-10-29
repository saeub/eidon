---
title: Getting started
layout: default
nav_order: 1
---

{% include toc.html %}

# Getting started

This page will show you how to set up and run your first eye-tracking experiment with _eidon_.

## Installing the package

The easiest way to install _eidon_ is using `pip`:

```bash
pip install eidon
```

> **NOTE:** On Mac, you will first have to install the [portaudio library](https://portaudio.com/). For example, using Homebrew: `brew install portaudio`

## Building and running an example experiment

Download one of the [example experiments](https://github.com/saeub/eidon/tree/main/examples) and place the folder in your working directory. You can use [this link](https://download-directory.github.io/?url=https://github.com/saeub/eidon/tree/main/examples) to download a ZIP archive of all example experiments.

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

To implement your own experiment, you first need to find the [experiment type](reference/experiment-types) that matches your use case. For this tutorial, we'll use the [`SinglePageReading`](reference/experiment-types/SinglePageReading) experiment type.

### 1. Initialize the experiment folder

To get you started quickly, the `eidon init` command can create the required experiment folder structure for you:

```bash
eidon init SinglePageReading -e my-experiment
```

This initializes a new experiment in a folder named `my-experiment`. It includes a basic configuration file and some empty materials files:

```
📂 my-experiment
├─ 📄 config.yaml
└─ 📂 materials
   ├─ 📄 instructions.txt
   ├─ 📄 break.txt
   ├─ 📄 wait.txt
   ├─ 📄 end.txt
   └─ 📂 items
      ├─ 📄 experimental.csv
      ├─ 📄 filler.csv
      └─ 📄 practice.csv
```

### 2. Configure settings

The `config.yaml` file lets you configure how the experiment should look and behave. For example, you can change the size of the area on screen where your stimuli will appear (`stimulus_area_size`), define experimental conditions for your experiment design (`conditions`), or specify what keys participants should use to select options for multiple-choice questions (`option_keys`). Check the [documentation for your experiment type](reference/experiment-types) for more information.

For now, let's just set the number of participants to 8, define two experimental conditions (`active` and `passive`) and use the arrow keys <kbd>←</kbd> and <kbd>→</kbd> to select answer options and <kbd>SPACE</kbd> to confirm:

```yaml
# ...

num_participants: 8
num_conditions: [active, passive]

# ...

option_keys: [LEFT, RIGHT]
confirm_key: SPACE
```

### 3. Create stimuli

The `materials` folder contains all the study materials required for your experiment (including stimulus texts or images, instructions, etc.). For example, `materials/items/experimental.csv` holds the reading passages and questions of each experimental items. Some files (like `practice.csv` or `fillers.csv`) are optional and can be deleted. Refer to the [documentation for your experiment type](reference/experiment-types) for more information, and check out the [example experiments](https://github.com/saeub/eidon/tree/main/examples).

Let's add an experimental item with two conditions to `materials/items/experimental.csv:

```csv
id,condition,text,question.0.stem,question.0.option.0,question.0.option.1,question.0.correct_option_index
01,active,"My neighbor's friend stole a candy bar.","Did the neighbor steal the candy bar?",yes,no,1
01,passive,"A candy bar was stolen by my neighbor's friend.","Did the neighbor steal the candy bar?",yes,no,1
```

### 3. Build the experiment

To build your experiment, navigate into the `my-experiment` folder and run:

```bash
eidon build
```

This will generate the stimulus images, AOI files, and session files:

```
📂 my-experiment
├─ config.yaml
├─ experiment.json
├─ 📁 materials
├─ 📂 stimuli
│  ├─ 🖼️ instructions.0.png
│  ├─ 📄 instructions.0.char.csv
│  ├─ 📄 instructions.0.word.csv
│  ├─ 🖼️ item.01.active.text.png
│  ├─ 📄 item.01.active.text.char.csv
│  ├─ 📄 item.01.active.text.word.csv
│  ├─ 🖼️ item.01.active.question.png
│  ├─ 📄 item.01.active.question.char.csv
│  ├─ 📄 item.01.active.question.word.csv
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

This will create a recording directory under `my-experiment/recordings` containing the log file with the question responses (and also the eye-tracking data, if not run in dummy mode):

```
📂 my-experiment
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

### 2. Record the hardware setup

When you run a session for the first time, you will be required to take a few measurements, including the size of the stimulus area and the eye-to-screen distance. This will make sure that your stimuli are presented within the trackable range of your eye tracker. Running this command from the root directory of your experiment will guide you through all of the settings:

```bash
eidon setup
```

Before each subsequent session, you will be asked to confirm if the previous setup is still accurate. If any of the measurements have changed, you will be prompted to re-enter them.

The setup configurations are stored in the `setups` directory of your experiment:

```
📂 my-experiment
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

After completing a session, the EDF file will automatically be transferred to a directory under `my-experiment/recordings`. To convert the EDF file to a more interoperable format, use the ["EDF Converter" tool by SR Research](https://www.sr-research.com/support/thread-7674.html). After converting the `.edf` to a `.asc` file, run the following command from the root directory of your experiment:

```bash
eidon convert
```

This will convert all `.asc` files to `.csv` files, which can be opened by all major data analysis software packages. It will also generate a `.json` file containing metadata like calibration errors.

```
📂 my-experiment
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
