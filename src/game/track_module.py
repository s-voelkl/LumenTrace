from enum import Enum
from .line import Line


class TrackType(Enum):
    NONE = "none"
    STRAIGHT = "straight"
    CURVE_LEFT = "curve_left"
    CURVE_RIGHT = "curve_right"
    LOOPING = "looping"
    CURVE_LEFT_BENDED = "curve_left_bended"
    CURVE_RIGHT_BENDED = "curve_right_bended"
    INTERSECTION = "intersection"

class TrackModule:
    __track_types = list(TrackType)
    
    def __init__(
        self,
        track_type: TrackType = TrackType.NONE,
        length: float = 0,
        lines: list[Line] = [],
    ):
        self.__track_type = track_type if track_type in self.__track_types else TrackType.NONE
        self.__length = length if length >= 0 else 0
        self.__lines = lines if lines else []

    # Getters
    @property
    def length(self) -> float:
        return self.__length

    @property
    def lines(self) -> list[Line]:
        return self.__lines

    @property
    def track_type(self) -> TrackType:
        return self.__track_type