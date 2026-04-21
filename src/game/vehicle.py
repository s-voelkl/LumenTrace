# vehicle class 
# attr: position (float), lane (int), speed (float), acceleration (float), round (int), VehicleStyle

from src.game.lane import Lane

class Vehicle:
    
    __friction_percent = 0.98
    __acceleration_multiplier = 0.015
    
    def __init__(self, lane: Lane, position: float = 0, speed: float = 0, acceleration: float = 0, 
            round: int = 0, style: list[int] = []):
        self.__lane = lane 
        self.__position = position if position >= 0 else 0
        self.__speed = speed if speed >= 0 else 0
        self.__acceleration = acceleration if acceleration >= 0 else 0
        self.__round = round if round >= 0 else 0
        self.__style = style if style else [0, 0, 0]

    def accelerate(self, max_speed: float):
        '''Updates the speed of the vehicle based on its current acceleration and applies friction. 
        The speed is clamped to a maximum value in both positive and negative directions.

        Args:
            max_speed (float): The maximum speed the vehicle can reach in either direction.
        '''
        
        # apply friction to current speed
        if self.__speed != 0:
            self.__speed *= self.__friction_percent
            
        # apply acceleration to speed
        delta = self.__acceleration * self.__acceleration_multiplier
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
