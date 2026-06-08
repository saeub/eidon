from dataclasses import dataclass
from typing import Any, Literal


EventType = Literal["key", "hostkey", "fixation", "button"]


@dataclass(frozen=True)
class Event:
    type: EventType
    time: float | None
    data: dict[str, Any]

    def matches(self, other: "Event") -> bool:
        if self.type != other.type:
            return False
        for key, value in self.data.items():
            if key not in other.data or other.data[key] != value:
                return False
        return True
