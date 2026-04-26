class Settings:
    def __init__(
        self,
        max_speed: float = 100.0,
        respawn_ticks: int = 200,
        friction_percent: float = 0.02,
        acceleration_multiplier: float = 0.015,
        special_1_threshold: float = 0.5, # TODO:measure fitting threshold for activation of line change
        lane_change_ticks: int = 25,
    ):
        self.__max_speed = max_speed if max_speed > 0 else 100.0
        self.__respawn_ticks = respawn_ticks if respawn_ticks > 0 else 200
        self.__friction_percent = friction_percent if friction_percent > 0 else 0.02
        self.__acceleration_multiplier = acceleration_multiplier if acceleration_multiplier > 0 else 0.015
        self.__special_1_threshold = special_1_threshold if special_1_threshold >= 0 else 0.5
        self.__lane_change_ticks = lane_change_ticks if lane_change_ticks > 0 else 25
        self.__vehicle_crash_distance: float = 20.0


    # Getters
    @property
    def max_speed(self) -> float:
        return self.__max_speed

    @property
    def respawn_ticks(self) -> int:
        return self.__respawn_ticks

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
    def lane_change_ticks(self) -> int:
        return self.__lane_change_ticks

    @property
    def vehicle_crash_distance(self) -> float:
        return self.__vehicle_crash_distance