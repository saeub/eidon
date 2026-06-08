## Experiment stage: `HostControlled`

Disables interaction on the display PC and waits for commands from the host PC.

### Configuration

- `stage` (dict[str, typing.Any])  
  The stage to display while waiting for host input. This stage will not be interactive.
- `continue_key` (str)  
  The key that the host PC should send to continue.
- `setup_key` (str)  
  The key that the host PC should send to start the eyetracker setup.
- `host_imgpath` (str | None)  
  Path to an image file to show on the host PC during this stage. By default, the backdrop of the inner stage is shown.
