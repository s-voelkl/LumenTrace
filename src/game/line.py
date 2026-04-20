from .driving_profile import DrivingProfile

class Line:
    def __init__(self, driving_profile: DrivingProfile, length: float = 0, lane_id: int = 0):
        self.__length = length if length >= 0 else 0
        self.__lane_id = lane_id if lane_id >= 0 else 0
        self.__profile = driving_profile

    # Getters
    @property
    def length(self) -> float:
        return self.__length

    @property
    def lane_id(self) -> int:
        return self.__lane_id

    @property
    def profile(self) -> DrivingProfile:
        return self.__profile