class Settings:
    def __init__(
        self,
        max_speed: float = 100.0,
        min_acceleration: float = -100.0,
        max_acceleration: float = 100.0,
        respawn_ticks: int = 200,
        friction_percent: float = 0.02,
        acceleration_multiplier: float = 0.03,
        lane_change_window: float = 20.0,
        vehicle_crash_distance: float = 5.0,
        rounds_to_win: int = 20,
        vehicle_light_front: bool = True,
        vehicle_light_rear: bool = True,
    ):
        self.__max_speed = max_speed if max_speed > 0 else 100.0
        self.__min_acceleration = min_acceleration if min_acceleration < 0 else -100.0
        self.__max_acceleration = max_acceleration if max_acceleration > 0 else 100.0
        self.__respawn_ticks = respawn_ticks if respawn_ticks > 0 else 200
        self.__friction_percent = friction_percent if friction_percent > 0 else 0.02
        self.__acceleration_multiplier = (
            acceleration_multiplier if acceleration_multiplier > 0 else 0.03
        )
        self.__lane_change_window = (
            lane_change_window if lane_change_window > 0 else 20.0
        )
        self.__vehicle_crash_distance = (
            vehicle_crash_distance if vehicle_crash_distance > 0 else 5.0
        )
        self.__rounds_to_win = rounds_to_win if rounds_to_win > 0 else 20
        self.__vehicle_light_front = vehicle_light_front
        self.__vehicle_light_rear = vehicle_light_rear

    # Getters
    @property
    def max_speed(self) -> float:
        return self.__max_speed

    @property
    def min_acceleration(self) -> float:
        return self.__min_acceleration

    @property
    def max_acceleration(self) -> float:
        return self.__max_acceleration

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
    def lane_change_window(self) -> float:
        return self.__lane_change_window

    @property
    def vehicle_crash_distance(self) -> float:
        return self.__vehicle_crash_distance

    @property
    def rounds_to_win(self) -> int:
        return self.__rounds_to_win
    
    @property
    def vehicle_light_front(self) -> bool:
        return self.__vehicle_light_front
    
    @property
    def vehicle_light_rear(self) -> bool:
        return self.__vehicle_light_rear
