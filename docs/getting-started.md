## Getting started

This page will show you how to set up and run your first eye-tracking experiment with _eidon_.

### Installing the package

The easiest way to install _eidon_ is using `pip`:

```bash
pip install eidon
```

### Building and running an example experiment

Download one of the [example experiments](https://github.com/saeub/eidon/tree/main/examples) and place the folder in your working directory. You can use this link to download a ZIP archive of the `SinglePageReading` example:

https://download-directory.github.io/?url=https://github.com/saeub/eidon/tree/main/examples/SinglePageReading

Build the experiment using this command:

```bash
eidon build SinglePageReading
```

Then run the session for participant `P1` in dummy mode:

```bash
eidon run SinglePageReading P1 --dummy
```

> Dummy mode means that you won't need an eye tracker to test the experiment.

### Implementing your first experiment

To implement your own experiment, you first need to find the [experiment type](experiment-types/index.md) that matches your use case. For this tutorial, we'll use the [`SinglePageReading`](experiment-types/SinglePageReading.md) experiment type.

#### 1. Creating an experiment folder and a configuration file

First, create a folder and a `config.yaml` file for your experiment:

```
📂 my_experiment
└─ config.yaml
```

```yaml
# config.yaml
name: "my-experiment"
type: SinglePageReading

display_size_px: [1100, 900]
num_participants: 8
option_keys: [Y, N]
```

The experiment's `name` will appear, among others, in recordings and metadata files.

`display_size_px` defines the width and height (in pixels) of the area where your stimuli will be presented. It is important that this is within your eye tracker's **trackable area** on the screen you're going to use for the experiment.

`option_keys` are the keys on the keyboard that participants are going to use to respond to multiple-choice questions (in this case, we are going to use yes/no questions).

This example is a very bare-bones configuration file. Check the [documentation page for `SinglePageReading`](experiment-types/SinglePageReading.md) for more configuration options.

#### 2. Creating stimuli

The [documentation page for `SinglePageReading`](experiment-types/SinglePageReading.md) tells you the structure and format you need to use for your stimuli:

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

Here, we have an item in two conditions (`active` and `passive`) with one comprehension question each.

Check the [example experiment](https://github.com/saeub/eidon/tree/main/examples/SinglePageReading/items) for more examples of item files.

#### 3. Building the experiment

To build your experiment, run:

```bash
eidon build my_experiment
```

where `my_experiment` is the path to your experiment folder. This will generate the stimulus images, AOI files, and session files:

```
📂 my_experiment
├─ config.yaml
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

#### 4. Running the experiment

To run a session of your experiment, run:

```bash
eidon run my_experiment P1 --dummy
```

where `P1` is the name of a session file (without `.json`). This will create a recording directory under `my_experiment/recordings` containing the log file (this is where the question responses are) and eye-tracking data (except when in dummy mode).

### Learn more

Congratulations, you've mastered the basics of _eidon_!

As a next step, you can:

- Look at [experiment stages](experiment-stages/index.md) and how session files are structured.
- [Create your own experiment type](experiment-types/custom.md). This gives you maximum control over the experimental procedure.
- [Create your own experiment stage](experiment-stages/custom.md). This allows you to present types of stimuli or implement interfaces that are not supported out of the box.
