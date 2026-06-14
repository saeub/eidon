import argparse
import dataclasses
import inspect
import re
import typing
from pathlib import Path

import docstring_parser

from eidon.__main__ import get_argument_parser
from eidon.build import ExperimentType
from eidon.build.designs import DESIGNS
from eidon.run import ExperimentStage


def generate_experimenttype_index(
    experiment_types: dict[str, type[ExperimentType]],
) -> str:
    markdown = "## Experiment types\n\n"
    markdown += "| Experiment type | Description |\n"
    markdown += "| --- | --- |\n"
    for name, cls in sorted(experiment_types.items()):
        short_description = docstring_parser.parse(
            cls.__doc__ or "", docstring_parser.DocstringStyle.REST
        ).short_description
        markdown += f"| [`{name}`]({name}.md) | {short_description} |\n"
    markdown += "\n> Can't find the experiment type you need? [**Implement your own!**](custom.md)\n"
    return markdown


def generate_experimenttype_page(
    name: str, cls: type[ExperimentType], examples_path: Path, examples_url: str
) -> str:
    parsed_docstring = docstring_parser.parse(
        cls.__doc__ or "", docstring_parser.DocstringStyle.REST
    )
    short_description = parsed_docstring.short_description or ""
    long_description = parsed_docstring.long_description or ""
    field_descriptions = {
        field.arg_name: field.description.replace("\n", " ")
        for field in parsed_docstring.params
    }
    fields = cls.__dataclass_fields__

    markdown = f"## Experiment type: `{name}`\n\n"
    markdown += f"{short_description}\n\n"
    if long_description:
        markdown += "### Description\n\n"
        markdown += f"{long_description}\n\n"
    markdown += "### Configuration\n\n"
    for field_name, field in fields.items():
        field_type = field.type
        if isinstance(field_type, type):
            field_type = field_type.__name__
        field_default = field.default
        field_description = field_descriptions.get(field_name)
        markdown += f"- `{field_name}` ({field_type})"
        if field_description:
            markdown += f"  \n  {field_description}"
        if field_name.endswith(("_key", "_keys")):
            markdown += (
                "  \n  Key names are [pyglet key symbol strings]"
                "(https://pyglet.readthedocs.io/en/latest/programming_guide/keyboard.html#defined-key-symbols) "
                "(e.g. `A`, `LEFT`, `SPACE`)."
            )
        elif field_name == "design":
            markdown += "  \n  Available designs are documented [here](designs.md)"
        if field_default is not dataclasses.MISSING:
            markdown += f"  \n  Default: `{field_default}`"
        markdown += "\n"
    if (examples_path / name).exists():
        markdown += f"\n### [Example]({examples_url.format(name)})\n"
    return markdown


def generate_experimentstage_index(
    experiment_stages: dict[str, type[ExperimentStage]],
) -> str:
    markdown = "## Experiment stages\n\n"
    markdown += "| Experiment stage | Description |\n"
    markdown += "| --- | --- |\n"
    for name, cls in sorted(experiment_stages.items()):
        short_description = docstring_parser.parse(
            cls.__doc__ or "", docstring_parser.DocstringStyle.REST
        ).short_description
        markdown += f"| [`{name}`]({name}.md) | {short_description} |\n"
    markdown += "\n> Can't find the experiment stage you need? [**Implement your own!**](custom.md)\n"
    return markdown


def generate_experimentstage_page(name: str, cls: type[ExperimentStage]) -> str:
    parsed_docstring = docstring_parser.parse(
        cls.__doc__ or "", docstring_parser.DocstringStyle.REST
    )
    short_description = parsed_docstring.short_description or ""
    long_description = parsed_docstring.long_description or ""
    signature = inspect.signature(cls.init)
    type_hints = typing.get_type_hints(cls.init)
    parsed_init_docstring = docstring_parser.parse(
        cls.init.__doc__ or "", docstring_parser.DocstringStyle.REST
    )
    param_docstrings = {
        param.arg_name: param.description.replace("\n", " ")
        for param in parsed_init_docstring.params
    }

    markdown = f"## Experiment stage: `{name}`\n\n"
    markdown += f"{short_description}\n\n"
    if long_description:
        markdown += "### Description\n\n"
        markdown += f"{long_description}\n\n"
    markdown += "### Configuration\n\n"
    if len(signature.parameters) == 1:  # Only self
        markdown += "No configuration parameters.\n"
    for param in signature.parameters.values():
        param_name = param.name
        if param_name == "self":
            continue
        param_type = type_hints.get(param_name, "")
        if isinstance(param_type, type):
            param_type = param_type.__name__
        param_default = param.default if param.default is not param.empty else None
        param_description = param_docstrings.get(param_name)
        markdown += f"- `{param_name}` ({param_type})"
        if param_description:
            markdown += f"  \n  {param_description}"
        if param_name.endswith(("_key", "_keys")):
            markdown += (
                "  \n  Key names are [pyglet key symbol strings]"
                "(https://pyglet.readthedocs.io/en/latest/programming_guide/keyboard.html#defined-key-symbols) "
                "(e.g. `A`, `LEFT`, `SPACE`)."
            )
        if param_default is not None:
            markdown += f"  \n  Default: `{param_default}`"
        markdown += "\n"
    return markdown


def generate_designs_page(designs: dict[str, typing.Callable]) -> str:
    markdown = "## Experiment designs\n\n"
    markdown += "| Design | Description |\n"
    markdown += "| --- | --- |\n"
    for name, design in sorted(designs.items()):
        short_description = design.__doc__.replace("\n", " ") or ""
        markdown += f"| `{name}` | {short_description} |\n"
    return markdown


def generate_cli_index(argument_parser: argparse.ArgumentParser) -> str:
    command_helps = {
        action.dest: action.help
        for action in argument_parser._actions[-1]._choices_actions
    }

    markdown = "## Command-line interface\n\n"
    markdown += "| Command | Description |\n"
    markdown += "| --- | --- |\n"
    for command in command_helps:
        help = command_helps[command]
        markdown += f"| [`{command}`]({command}.md) | {help} |\n"
    return markdown


def generate_cli_page(command: str, subparser: argparse.ArgumentParser) -> str:
    description = subparser.description
    usage = subparser.format_help()
    usage = re.sub(rf"^usage: .+?{command}", f"eidon {command}", usage)

    markdown = f"## CLI command: `{command}`\n\n"
    if description:
        markdown += f"{description}\n\n"
    markdown += "### Usage\n\n"
    markdown += f"```\n{usage}```\n"
    return markdown


def main():
    docs_path = Path(__file__).parent
    examples_path = Path(__file__).parent.parent / "examples"
    examples_url = "https://github.com/saeub/eidon/tree/main/examples/{}"
    generated_prefix = "---\ngenerated: true\n---\n\n"

    # Delete old generated files
    for path in docs_path.glob("**/*.md"):
        if path.read_text().startswith(generated_prefix):
            path.unlink()

    # Experiment types
    experiment_types = ExperimentType.get_subclasses()
    markdown = generate_experimenttype_index(experiment_types)
    (docs_path / "experiment-types" / "index.md").write_text(
        generated_prefix + markdown
    )
    for name, cls in experiment_types.items():
        markdown = generate_experimenttype_page(name, cls, examples_path, examples_url)
        (docs_path / "experiment-types" / f"{name}.md").write_text(
            generated_prefix + markdown
        )

    # Experiment stages
    experiment_stages = ExperimentStage.get_subclasses()
    markdown = generate_experimentstage_index(experiment_stages)
    (docs_path / "experiment-stages" / "index.md").write_text(
        generated_prefix + markdown
    )
    for name, cls in experiment_stages.items():
        markdown = generate_experimentstage_page(name, cls)
        (docs_path / "experiment-stages" / f"{name}.md").write_text(
            generated_prefix + markdown
        )

    # Experiment designs
    markdown = generate_designs_page(DESIGNS)
    (docs_path / "experiment-types" / "designs.md").write_text(generated_prefix + markdown)

    # CLI
    argument_parser = get_argument_parser(color=False)
    markdown = generate_cli_index(argument_parser)
    (docs_path / "cli" / "index.md").write_text(generated_prefix + markdown)
    for command, subparser in argument_parser._actions[-1].choices.items():
        markdown = generate_cli_page(command, subparser)
        (docs_path / "cli" / f"{command}.md").write_text(generated_prefix + markdown)


if __name__ == "__main__":
    main()
