from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from eidon.build.materials import load_materials


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

    MATERIALS_SCHEMA: ClassVar[dict[str, dict[str, Any]]] | None = None

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
        self.materials = load_materials(
            self.experiment_path / "materials", self.MATERIALS_SCHEMA
        )

    @property
    def config_path(self) -> Path:
        """Path to the config.yaml file."""
        return self.experiment_path / "config.yaml"

    @classmethod
    def get_init_templates(cls) -> dict[str, str] | None:
        """Return a dictionary of template file paths and contents for eidon init."""
        return None

    @abstractmethod
    def build(self) -> dict[str, dict[str, Any]]:
        """Generate stimuli and return session definitions."""
        pass
