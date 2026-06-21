---
generated: true
---

## Experiment stage: `StimulusMultiPage`

Shows multiple image stimuli that can be navigated.

### Configuration

- `imgpaths` (list[str])  
  A list of paths to the image files to display, relative to the experiment's root directory.
- `next_page_key` (str)  
  The key to press to go to the next page.  
  Key names are [pyglet key symbol strings](https://pyglet.readthedocs.io/en/latest/programming_guide/keyboard.html#defined-key-symbols) (e.g. `A`, `LEFT`, `SPACE`).
- `prev_page_key` (str | None)  
  The key to press to go to the previous page. By default, going to the previous page is disabled.  
  Key names are [pyglet key symbol strings](https://pyglet.readthedocs.io/en/latest/programming_guide/keyboard.html#defined-key-symbols) (e.g. `A`, `LEFT`, `SPACE`).
- `min_duration` (float)  
  Minimum duration in seconds to display each page before allowing navigation. Default is 0.5 seconds to prevent accidentally skipping pages.  
  Default: `0.5`
