import argparse
from pathlib import Path

from eidon.build import ExperimentBuilder
from eidon.clean import RecordingCleaner
from eidon.convert import RecordingConverter
from eidon.run import ExperimentRunner
from eidon.setup import HardwareSetup


def get_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Command-line interface for eidon.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser(
        "build",
        help="Build an experiment.",
        description=(
            "Build an experiment from a configuration file and materials. "
            "Generates stimuli and session definitions that can be run with `eidon run`."
        ),
    )
    build_parser.add_argument(
        "--experiment",
        "-e",
        type=Path,
        default=Path.cwd(),
        help="Path to the experiment directory (must contain config.yaml).",
    )
    build_parser.add_argument(
        "--area-images",
        action="store_true",
        help="Generate additional images with outlined areas of interest.",
    )

    run_parser = subparsers.add_parser(
        "run",
        help="Run an experiment session.",
        description="Run a session from a built experiment. Collects eye-tracking data and logs.",
    )
    run_parser.add_argument(
        "--experiment",
        "-e",
        type=Path,
        default=Path.cwd(),
        help="Path to the built experiment directory (must contain experiment.json and sessions/).",
    )
    run_parser.add_argument(
        "session",
        type=str,
        help="Name of the session to run (without the .json file extension).",
    )
    run_parser.add_argument(
        "--dummy",
        action="store_true",
        help="Use mouse-based eye tracker for testing.",
    )
    run_parser.add_argument(
        "--participant-control",
        action="store_true",
        help="Allow participant to control calibrations, drift corrects, etc. (useful for testing).",
    )
    run_parser.add_argument(
        "--recording-name",
        type=str,
        default=None,
        help="Name for recording and log files.",
    )
    run_parser.add_argument(
        "--screen",
        type=int,
        default=0,
        help="Screen index to use for the experiment window.",
    )
    run_parser.add_argument(
        "--start-from-stage",
        type=str,
        default=None,
        help="Start the session from the stage with the specified name.",
    )

    setup_parser = subparsers.add_parser(
        "setup",
        help="Specify the hardware setup before running a session.",
        description=(
            "Specify the hardware setup, including eye tracker model and stimulus area measurements. "
            "This is required before running a session for the first time, and has to be confirmed before every subsequent session."
        ),
    )
    setup_parser.add_argument(
        "--experiment",
        "-e",
        type=Path,
        default=Path.cwd(),
        help="Path to the built experiment directory (must contain experiment.json and sessions/).",
    )
    setup_parser.add_argument(
        "--screen",
        type=int,
        default=0,
        help="Screen index to use for the setup window.",
    )

    convert_parser = subparsers.add_parser(
        "convert",
        help="Convert recordings to a standard format.",
        description="Convert EyeLink recordings (.asc files) to a CSV file and extract metadata into a JSON file.",
    )
    convert_parser.add_argument(
        "--experiment",
        "-e",
        type=Path,
        default=Path.cwd(),
        help="Path to the experiment directory (must contain experiment.json and recordings/).",
    )
    convert_parser.add_argument(
        "recording_names",
        type=str,
        nargs="*",
        help=(
            "Names of the recordings or sessions to convert (without the .asc file extension). "
            "If not provided, all recordings will be converted."
        ),
    )

    clean_parser = subparsers.add_parser(
        "clean",
        help="Clean gaze data.",
        description=(
            "Clean gaze data by manually correcting drift or removing bad trials. "
            "Saves a JSON files with the applied corrections. "
            "These corrections can then be used to generate a cleaned gaze CSV file with the `--apply` flag."
        ),
    )
    clean_parser.add_argument(
        "--experiment",
        "-e",
        type=Path,
        default=Path.cwd(),
        help="Path to the experiment directory (must contain experiment.json and recordings/).",
    )
    clean_parser.add_argument(
        "recording_names",
        type=str,
        nargs="*",
        help="Names of the recordings or sessions to clean (without a file extension).",
    )
    clean_parser.add_argument(
        "--areas",
        type=str,
        default=None,
        help=(
            "Area types to display as a backdrop (e.g., 'word'). "
            "Requires building the experiment with --area-images."
        ),
    )
    clean_parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the corrections to the gaze data and save a new CSV file (no GUI).",
    )

    return parser


def main():
    parser = get_argument_parser()
    args = parser.parse_args()

    if not args.experiment.exists():
        print(f"Experiment folder '{args.experiment}' does not exist.")
        exit(1)

    if args.command == "build":
        builder = ExperimentBuilder(experiment_path=args.experiment)
        builder.build(generate_area_images=args.area_images)

    elif args.command == "setup":
        setup = HardwareSetup(
            experiment_path=args.experiment,
            screen=args.screen,
        )
        setup.setup()

    elif args.command == "run":
        runner = ExperimentRunner(
            experiment_path=args.experiment,
            session_name=args.session,
            dummy=args.dummy,
            participant_control=args.participant_control,
            recording_name=args.recording_name,
            screen=args.screen,
        )
        runner.run(start_from_stage=args.start_from_stage)

    elif args.command == "convert":
        converter = RecordingConverter(experiment_path=args.experiment)
        converter.convert(args.recording_names)

    elif args.command == "clean":
        cleaner = RecordingCleaner(experiment_path=args.experiment)
        if args.apply:
            cleaner.apply(recording_names=args.recording_names)
        else:
            if not args.recording_names or len(args.recording_names) > 1:
                print("Please specify a single recording name to clean.")
                exit(1)
            cleaner.clean(
                recording_name=args.recording_names[0],
                area_type=args.areas,
            )


if __name__ == "__main__":
    main()
