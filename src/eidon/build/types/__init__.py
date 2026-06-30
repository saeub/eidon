from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal


@dataclass(kw_only=True)
class ExperimentType(ABC):
    """
    Base class for experiment types.

    :param background_color: Color for window and stimulus backgrounds.
        (red, green, blue) with values from 0 to 255.
    :param stimulus_area_px: Size of the rectangular stimulus area in pixels (width, height).
        The rectangle will be centered in the screen and all stimuli will be presented inside it.
        The area needs to be within the trackable range of your eye tracker.
        The area cannot be larger than the resolution of your monitor.
    :param tracking_mode: Tracking mode of the eye-tracker (either `remote` or `head-stabilized`).
    """

    # TODO: Use more user-friendly formats for color and size, and avoid list->tuple conversion for PIL
    stimulus_area_px: tuple[int, int]
    background_color: tuple[int, int, int] = (204, 204, 204)
    tracking_mode: Literal["remote", "head-stabilized"]

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
