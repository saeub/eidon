## CLI command: `setup`

Once an experiment has been built, this command has to be run to set up the hardware. Using `eidon setup` the experimenter 
can define the physical hardware settings such as the eye-to-screen distance or the physical screen size in millimeters.

Note that running this command is required in order to run sessions

### Usage

```
eidon setup [-h] path

Once an experiment has been built, this command has to be run to set up the hardware. Using `eidon setup` the experimenter 
can define the physical hardware settings such as the eye-to-screen distance or the physical screen size in millimeters.

Note that running this command is required in order to run sessions

positional arguments:
  path           Path to the experiment directory (must contain experiment.json and sessions/).

options:
  -h, --help     show this help message and exit
```