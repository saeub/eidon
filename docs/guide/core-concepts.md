---
title: Core concepts
parent: User guide
layout: default
nav_order: 0
---
{% include toc.html %}

# Core concepts

This page will introduce the core concepts you'll encounter when using _eidon_.

## Experiment

Every **experiment** is a folder with a specific file structure. The folder includes all the materials required to build and run the experiment, including stimuli, configuration files, collected data, and custom code files. For example, it could look like this:

```
📂 my_experiment
├─ config.yaml
├─ experiment.json
├─ 📂 materials
│  └─ 📄 texts.txt
├─ 📂 stimuli
│  ├─ 📄 image1.png
│  ├─ 📄 image1.aois.csv
│  └─ 📄 sound1.wav
├─ 📂 sessions
│  ├─ 📄 subject1.json
│  ├─ 📄 subject2.json
│  └─ 📄 subject3.json
├─ 📂 recordings
└─ 📂 code
   └─ 📄 custom.py
```

Don't worry – you won't have to create all those files yourself. Most of the files will be created automatically by _eidon_. The fact that all these files are contained within a single folder will make it easy for you to share or publish your experiment. Simply zip your experiment and upload it, and anyone will be able to reproduce your experiment.

## Experiment type

_eidon_ supports various **types of experiments** out of the box. For example, a reading experiment with a Latin square design. The experiment type determines what kinds of materials you will need to build an experiment (e.g., texts and comprehension questions) and what the rough procedure will be when you run it (e.g., how the stimuli will be presented).

You can find an overview of all the experiment types that are currently supported [here](../reference/experiment-types). If none of the pre-implemented ones match your needs, you can always [create your own experiment type](custom-experiment-type).

## Experiment session

A **session** is a single run of your experiment. It defines precisely what trials are presented in what order, during which parts eye movements are recorded, and what interactions (key presses, etc.) are possible. All of this is defined in a JSON file in the experiment folder. In a typical single-session experiment, there will be one of these session files for each participant. If you are using one of the existing [experiment types](../reference/experiment-types), _eidon_ will generate them for you. But if you want to have full control over every detail in your experiment, you are free to create or generate these session files yourself.

## Experiment stage

Each session consists of a sequence of **stages**. A stage is typically just a single screen where a stimulus is displayed or some interaction happens (e.g., answering a question, performing calibration, etc.). If you are using one of the existing [experiment types](../reference/experiment-types), you will not have to configure these stages yourself.

```mermaid
block
    block:sessions
    columns 3
        block:session1:3
        columns 3
            session1label["session1.json"]:3
            session1stage1["Stage 1"]
            session1stage2["Stage 2"]
            session1stage3["Stage 3"]
        end
        block:session2:3
        columns 3
            session2label["session2.json"]:3
            session2stage1["Stage 1"]
            session2stage2["Stage 2"]
            session2stage3["Stage 3"]
        end
    end
    style session1label stroke-width:0, fill:#0000
    style session2label stroke-width:0, fill:#0000
```
