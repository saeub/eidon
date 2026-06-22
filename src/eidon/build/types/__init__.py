from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

TrackingMode = Literal['remote', 'head-stabilized']

@dataclass(kw_only=True)
class ExperimentType(ABC):
    """
    Base class for experiment types.

    :param background_color: Color for window and stimulus backgrounds.
        (red, green, blue) with values from 0 to 255.
    :param stimulus_area_px: Size of the stimulus area in pixels (width, height). The resulting rectangle will be
    centered in the screen and all stimuli will be presented within this rectangle. Please ensure that the stimulus
    area is within the trackable range of your eye-tracker. Note that it is not equivalent to the resolution of
    the monitor, but it cannot be greater than the resolution.
    :param margin_px: The margin in px. This margin will be deducted from the width and height of the stimulus area.
    :param tracking_mode: Tracking mode of the eye-tracker. For example, remote tracking or head-stabilized.
    """

    # TODO: Use more user-friendly formats for color and size, and avoid list->tuple conversion for PIL
    stimulus_area_px: tuple[int, int]
    margin_px: int
    background_color: tuple[int, int, int] = (204, 204, 204)
    tracking_mode: TrackingMode

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
