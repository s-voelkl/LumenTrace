# class Driving Profile
# attr: max_speed (float), min_speed (float), max_acceleration (float), max_deceleration, lane_change_allowed (bool)

class DrivingProfile:
    def __init__(self, max_speed: float = 100.0, min_speed: float = -100.0, max_acceleration: float = 10.0, 
            min_acceleration: float = -10.0, lane_change_allowed: bool = True):
        self.__max_speed = max_speed if max_speed > 0 else 100.0
        self.__min_speed = min_speed 
        self.__max_acceleration = max_acceleration if max_acceleration >= 0 else 10.0
        self.__min_acceleration = min_acceleration
        self.__lane_change_allowed = lane_change_allowed

    # Getters
    @property
    def max_speed(self) -> float:
        return self.__max_speed

    @property
    def min_speed(self) -> float:
        return self.__min_speed

    @property
    def max_acceleration(self) -> float:
        return self.__max_acceleration

    @property
    def min_acceleration(self) -> float:
        return self.__min_acceleration

    @property
    def lane_change_allowed(self) -> bool:
        return self.__lane_change_allowed