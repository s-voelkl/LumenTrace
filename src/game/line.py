from .lane import Lane
from .driving_profile import DrivingProfile

class Line:    
    def __init__(self, driving_profile: DrivingProfile, lane: Lane, length: float = 0):
        self.__length = length if length >= 0 else 0
        self.__lane = lane
        self.__driving_profile = driving_profile

    # Getters
    @property
    def length(self) -> float:
        return self.__length

    @property
    def lane(self) -> Lane:
        return self.__lane

    @property
    def driving_profile(self) -> DrivingProfile:
        return self.__driving_profile