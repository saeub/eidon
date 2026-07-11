---
generated: true
title: eidon build
parent: Command-line interface
layout: default
---

{% include toc.html %}

# CLI command: `eidon build`

Build an experiment from a configuration file and materials. Generates stimuli and session definitions that can be run with `eidon run`.

## Usage

```
eidon build [-h] [--experiment EXPERIMENT] [--area-images]

Build an experiment from a configuration file and materials. Generates stimuli
and session definitions that can be run with `eidon run`.

options:
  -h, --help            show this help message and exit
  --experiment, -e EXPERIMENT
                        Path to the experiment directory (must contain
                        config.yaml).
  --area-images         Generate additional images with outlined areas of
                        interest.
```
