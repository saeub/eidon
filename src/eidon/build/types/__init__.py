from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(kw_only=True)
class ExperimentType(ABC):
    """
    Base class for experiment types.

    :param background_color: Color for window and stimulus backgrounds.
        (red, green, blue) with values from 0 to 255.
    :param display_size: Size of the display in pixels (width, height).
    """

    # TODO: Use more user-friendly formats for color and size, and avoid list->tuple conversion for PIL
    display_size: tuple[int, int]
    background_color: tuple[int, int, int] = (204, 204, 204)

    @classmethod
    def get_subclasses(cls) -> dict[str, type[ExperimentType]]:
        """Recursively collect all subclasses (and subsubclasses etc.) of this class."""
        subclasses = {}
        for subclass in cls.__subclasses__():
            subclasses[subclass.__name__] = subclass
            subclasses.update(subclass.get_subclasses())
        return subclasses

    @abstractmethod
    def build(self, experiment_path: Path) -> dict[str, dict[str, Any]]:
        """Generate stimuli and return session definitions."""
        pass
