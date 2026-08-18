---
title: Home
layout: home
nav_order: 0
---

_eidon_ is a toolkit for implementing eye-tracking experiments and turning the collected data into publication-ready datasets.

You can use it to ...

- ... get started quickly with running your **first eye-tracking study**
- ... implement **common experimental paradigms** (like reading or visual world) without any programming
- ... conduct studies in a **reproducible** way with open and FAIR data principles in mind

_eidon_ is designed to be both **easy to use** and **easy to customize**, depending on your needs and level of expertise. It prioritizes **interoperability**, so you can combine it with the tools you already use and love.

<p align="center">
    <a href="getting-started" style="font-size: 1.5rem; font-weight: 500">🚀 Get started here</a>
</p>

> _eidon_ is still under development. Some features may be missing or buggy. You can help us out by [creating feature requests or bug reports](https://github.com/saeub/eidon/issues), or by [contributing code](https://github.com/saeub/eidon/pulls)!

## Who is _eidon_ for?

_eidon_ is for researchers who use in-lab eye-tracking methods, in particular:

- **Language researchers:** _eidon_ provides implementations for a range of [experiment types](reference/experiment-types) common in psycholinguistics. These implementations are easy to configure and modify with custom code to suit your needs.
- **NLP researchers:** Want to collect eye-tracking data for your dataset, or see what your annotators are paying attention to? _eidon_ is for you.
- **Students:** If you are just getting started with eye tracking, _eidon_ makes it easy for you to [implement your first experiment](getting-started) while following best practices. No coding required.

## Who is _eidon_ **not** for?

_eidon_ is **not** the best choice for you if you want to ...

- ... run **crowdsourcing studies**: _eidon_ is designed for use in a laboratory with high-precision eye trackers (not webcams).
- ... conduct user studies for your **software product or website**: all stimuli need to be rendered by _eidon_ itself, not via an external program.
- ... run an experiment with an eye tracker other than **SR Research EyeLink**: _eidon_ currently only supports EyeLink. If you have a different brand of eye tracker and would like to help us support it, please [get in touch](contact)!

## How _eidon_ works

```mermaid
flowchart TD
    A("Stimulus material + configuration file") -->|fa:fa-hammer eidon build| B(Compiled experiment)
    B -->|fa:fa-play eidon setup| C(Hardware setup configuration)
    C -->|fa:fa-play eidon run| D(Eye-tracking recordings)
    D -->|fa:fa-broom eidon convert| E(Raw eye-tracking data + metadata)
    E -->|fa:fa-broom eidon clean| F(Clean, publishable eye-tracking data)
```

_eidon_ consists of several components:

- **`eidon build`** builds your experiment. You provide the stimuli and configure fonts, colors, participant numbers, and other settings, and `eidon build` will turn it into a presentable experiment.
- **`eidon setup`** records metadata about your hardware setup. This keeps track of settings like the eye-to-screen distance and makes sure that your stimuli are within your eye tracker's trackable range.
- **`eidon run`** runs your experiment. You provide a session ID, and `eidon run` will present the stimuli, handle participant interaction, and record eye-tracking data.
- **`eidon convert`** converts your data into easy-to-use CSV files and extracts relevant metadata.
- **`eidon clean`** helps you inspect and clean your eye-tracking data.
