---
generated: true
title: StimulusPage
parent: Experiment stages
layout: default
---

{% include toc.html %}

# Experiment stage: `StimulusPage`

Shows a single image stimulus.

## Configuration

- `imgpath` (str)  
  Path to the image file to display, relative to the experiment's root directory.
- `continue_key` (str)  
  The key to press to continue to the next stage.  
  Available key names are listed [here](../keyboard).
- `min_duration` (float)  
  Minimum duration in seconds to display the stimulus before allowing continuation. Default is 0.5 seconds to prevent accidentally skipping the stimulus.  
  Default: `0.5`
