from src.game.lane import Lane

class Vehicle:
        
    def __init__(
        self,
        lane: Lane,
        position: float = 0,
        speed: float = 0,
        acceleration: float = 0,
        round: int = 0,
        style: list[int] = [],
        vehicle_length: float = 20,
    ):
        self.__lane = lane 
        self.__position = position if position >= 0 else 0
        self.__speed = speed if speed >= 0 else 0
        self.__acceleration = acceleration if acceleration >= 0 else 0
        self.__round = round if round >= 0 else 0
        self.__style = style if style else [0, 0, 0]
        self.__vehicle_length = vehicle_length if vehicle_length > 0 else 20

    def apply_friction(self, fraction_percent: float = 0.02):
        '''Applies friction to the vehicle's speed by reducing it by a fraction of its current value.
        
        Args:
            fraction_percent (float): The fraction of the current speed to reduce. Default is 0.02 (2%).
        '''
        if self.__speed != 0:
            self.__speed *= (1 - fraction_percent)
        
    def update_speed(self, max_speed: float, acceleration_multiplier: float = 0.015):
        '''Updates the vehicle's speed based on its current acceleration and a given acceleration multiplier, 
        while ensuring that the speed does not exceed a specified maximum speed. 
        If the speed changes direction in one step, it is clamped to 0.

        Args:
            max_speed (float): The maximum speed the vehicle can reach. 
                The speed will be clamped to this value in both positive and negative directions.
            acceleration_multiplier (float, optional): The multiplier for the acceleration. Defaults to 0.015.
        '''
        # apply acceleration to speed
        delta = self.__acceleration * acceleration_multiplier
        old_speed = self.__speed
        new_speed = old_speed + delta

        # if speed changes direction in one step, clamp to 0
        if (old_speed > 0 > new_speed) or (old_speed < 0 < new_speed):
            self.__speed = 0
        else:
            self.__speed = new_speed

        # clamp speed to positive and negative max speed
        max_abs_speed = abs(max_speed)
        if self.__speed > max_abs_speed:
            self.__speed = max_abs_speed
        elif self.__speed < -max_abs_speed:
            self.__speed = -max_abs_speed
            
    def update_position(self, delta_position: float, lane_length: float):
        '''Updates the vehicle position along the track and wraps it around at the track length.

        Args:
            delta_position (float): The distance to move in this tick.
            lane_length (float): The total lane length used for wraparound.
        '''
        new_position = self.__position + delta_position

        if lane_length <= 0:
            self.__position = new_position if new_position >= 0 else 0
            return

        while new_position >= lane_length:
            new_position -= lane_length
            self.__round += 1

        while new_position < 0 and self.__round > 0:
            new_position += lane_length
            self.__round -= 1

        self.__position = new_position if new_position >= 0 else 0


    # Setter
    def set_acceleration(self, acceleration: float):
        self.__acceleration = acceleration
        
    def set_lane(self, lane: Lane):
        self.__lane = lane

    def set_position(self, position: float):
        self.__position = position if position >= 0 else 0

    def set_speed(self, speed: float):
        self.__speed = speed

    def set_round(self, round_value: int):
        self.__round = round_value if round_value >= 0 else 0

    # Getters
    @property
    def position(self) -> float:
        return self.__position

    @property
    def lane(self) -> Lane:
        return self.__lane

    @property
    def speed(self) -> float:
        return self.__speed

    @property
    def acceleration(self) -> float:
        return self.__acceleration

    @property
    def round(self) -> int:
        return self.__round

    @property
    def style(self) -> list[int]:
        return self.__style

    @property
    def vehicle_length(self) -> float:
        return self.__vehicle_length
