class Settings:
    def __init__(
        self,
        max_speed: float = 100.0,
        respawn_time: float = 3000.0,
        friction_percent: float = 0.02,
        acceleration_multiplier: float = 0.015,
        special_1_threshold: float = 0.5, # TODO:measure fitting threshold for activation of line change
        lane_change_time: float = 500.0,
    ):
        self.__max_speed = max_speed if max_speed > 0 else 100.0
        self.__respawn_time = respawn_time if respawn_time > 0 else 3000.0
        self.__friction_percent = friction_percent if friction_percent > 0 else 0.02
        self.__acceleration_multiplier = acceleration_multiplier if acceleration_multiplier > 0 else 0.015
        self.__special_1_threshold = special_1_threshold if special_1_threshold >= 0 else 0.5
        self.__lane_change_time = lane_change_time if lane_change_time > 0 else 500.0


    # Getters
    @property
    def max_speed(self) -> float:
        return self.__max_speed

    @property
    def respawn_time(self) -> float:
        return self.__respawn_time

    @property
    def friction_percent(self) -> float:
        return self.__friction_percent

    @property
    def acceleration_multiplier(self) -> float:
        return self.__acceleration_multiplier

    @property
    def special_1_threshold(self) -> float:
        return self.__special_1_threshold

    @property
    def lane_change_time(self) -> float:
        return self.__lane_change_time