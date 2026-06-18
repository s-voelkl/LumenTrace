from enum import Enum
from .lane import Lane
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
        part_length: float = 0,
        lines: list[Line] | None = None,
        sound_stereo_ratio_left: float = 0.5,
    ):
        self.__track_type = track_type if track_type in self.__track_types else TrackType.NONE
        self.__length = part_length if part_length >= 0 else 0
        self.__lines = lines if lines else []
        # Clamp the stereo balance to the valid [0.0, 1.0] range. A value of
        # 1.0 routes the motor sound fully to the left speaker, 0.0 fully to
        # the right speaker, and 0.5 keeps it centered.
        self.__sound_stereo_ratio_left = min(1.0, max(0.0, sound_stereo_ratio_left))

    def get_line_length_for_lane(self, lane: Lane) -> float:
        '''Returns the line length for the given lane. If the lane is not found, returns 0.0.
        
        Args:
            lane (Lane): The lane for which to get the line length.
        Returns:
            float: The line length for the given lane, or 0.0 if the lane is not found.
        '''
        for line in self.__lines:
            if line.lane == lane:
                return line.length
        return 0.0

    def get_line_for_lane(self, lane: Lane) -> Line | None:
        for line in self.__lines:
            if line.lane == lane:
                return line
        return None

    def convert_position_between_lanes(
        self,
        source_lane: Lane,
        target_lane: Lane,
        source_position: float,
    ) -> float:
        source_line = self.get_line_for_lane(source_lane)
        target_line = self.get_line_for_lane(target_lane)

        if source_line is None or target_line is None:
            return source_position if source_position >= 0 else 0.0

        if source_line.length <= 0 or target_line.length <= 0:
            return source_position if source_position >= 0 else 0.0

        percent_through_line = max(0.0, min(source_position / source_line.length, 1.0))
        return target_line.length * percent_through_line

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

    @property
    def sound_stereo_ratio_left(self) -> float:
        """Stereo balance of the motor sound for this module.

        Returns:
            float: Left-channel ratio in the range [0.0, 1.0]. The right
                channel ratio is ``1.0 - sound_stereo_ratio_left``.
        """
        return self.__sound_stereo_ratio_left

    @property
    def sound_stereo_ratio_right(self) -> float:
        """Right-channel stereo ratio, complementary to the left ratio.

        Returns:
            float: ``1.0 - sound_stereo_ratio_left``.
        """
        return 1.0 - self.__sound_stereo_ratio_left