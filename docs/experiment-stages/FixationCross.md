---
generated: true
---

## Experiment stage: `FixationCross`

Shows a fixation cross/trigger.

### Configuration

- `location` (tuple[float, float])  
  The (x, y) location of the fixation cross in pixels. (0, 0) = top left.
- `fixation_trigger` (bool)  
  Whether to wait for the participant to fixate on the cross before continuing.  
  Default: `False`
- `tolerance` (float)  
  The radius in pixels around the fixation cross that counts as a fixation. Default is 20 pixels.  
  Default: `20`
- `timeout` (float)  
  Maximum time in seconds to wait for fixation before continuing anyway. Set to 0 to wait indefinitely (default).  
  Default: `0`
