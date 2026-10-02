from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, ClassVar

from eidon.build.materials import load_materials_file


@dataclass(kw_only=True)
class ExperimentType(ABC):
    """
    Base class for experiment types.

    :param experiment_path: Path to the experiment directory.
    :param background_color: Color for window and stimulus backgrounds.
        (red, green, blue) with values from 0 to 255.
    :param stimulus_area_size: Size of the rectangular stimulus area in pixels (width, height).
        The rectangle will be centered in the screen and all stimuli will be presented inside it.
        The area needs to be within the trackable range of your eye tracker.
        The area cannot be larger than the resolution of your monitor.
    """

    experiment_path: Path
    # TODO: Use more user-friendly formats for color and size, and avoid list->tuple conversion for PIL
    stimulus_area_size: tuple[int, int]
    background_color: tuple[int, int, int] = (204, 204, 204)

    _required_materials: ClassVar[list[str]] = []
    _optional_materials: ClassVar[list[str] | None] = None

    @classmethod
    def get_subclasses(cls) -> dict[str, type[ExperimentType]]:
        """Recursively collect all subclasses (and subsubclasses etc.) of this class."""
        subclasses = {}
        for subclass in cls.__subclasses__():
            subclasses[subclass.__name__] = subclass
            subclasses.update(subclass.get_subclasses())
        return subclasses

    def __post_init__(self):
        # Load material files
        self.materials = {}
        for material_path in self.experiment_path.glob("materials/**/*"):
            if material_path.is_file():
                path = material_path.relative_to(
                    self.experiment_path / "materials"
                ).as_posix()
                self.materials[path] = load_materials_file(material_path)
        missing_materials = [
            path for path in self._required_materials if path not in self.materials
        ]
        if missing_materials:
            raise ValueError(
                f"Missing required materials: {', '.join(missing_materials)}"
            )
        if self._optional_materials is not None:
            expected_materials = set(self._required_materials) | set(
                self._optional_materials
            )
            unexpected_materials = [
                path
                for path in self.materials
                if not any(
                    fnmatch(path, pattern) for pattern in expected_materials
                )
            ]
            if unexpected_materials:
                raise ValueError(
                    f"Unexpected materials: {', '.join(unexpected_materials)}"
                )

    @property
    def config_path(self) -> Path:
        """Path to the config.yaml file."""
        return self.experiment_path / "config.yaml"

    @abstractmethod
    def build(self) -> dict[str, dict[str, Any]]:
        """Generate stimuli and return session definitions."""
        pass
