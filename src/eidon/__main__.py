import argparse
from pathlib import Path

from eidon.build import ExperimentBuilder
from eidon.convert import RecordingConverter
from eidon.run import ExperimentRunner


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
        "path",
        type=Path,
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
        "path",
        type=Path,
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

    convert_parser = subparsers.add_parser(
        "convert", help="Convert .asc recordings to .csv."
    )
    convert_parser.add_argument(
        "path",
        type=Path,
        help="Path to the experiment directory (must contain recordings/).",
    )
    convert_parser.add_argument(
        "--recording-names",
        type=str,
        nargs="+",
        default=None,
        help=(
            "Names of the recordings to convert (without the .asc file extension). "
            "If not provided, all recordings will be converted."
        ),
    )

    return parser


def main():
    parser = get_argument_parser()
    args = parser.parse_args()

    if args.command == "build":
        builder = ExperimentBuilder(experiment_path=args.path)
        builder.build(generate_area_images=args.area_images)

    elif args.command == "run":
        runner = ExperimentRunner(
            experiment_path=args.path,
            session_name=args.session,
            dummy=args.dummy,
            participant_control=args.participant_control,
            recording_name=args.recording_name,
            screen=args.screen,
        )
        runner.run(start_from_stage=args.start_from_stage)

    elif args.command == "convert":
        converter = RecordingConverter(experiment_path=args.path)
        converter.convert(args.recording_names)


if __name__ == "__main__":
    main()
