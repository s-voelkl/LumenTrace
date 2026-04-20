# vehicle class 
# attr: position (float), lane (int), speed (float), acceleration (float), round (int), VehicleStyle

class Vehicle:
    def __init__(self, position: float = 0, lane: int = 0, speed: float = 0, acceleration: float = 0, 
            round: int = 0, style: list[int] = []):
        self.__position = position if position >= 0 else 0
        self.__lane = lane if lane >= 0 else 0
        self.__speed = speed if speed >= 0 else 0
        self.__acceleration = acceleration if acceleration >= 0 else 0
        self.__round = round if round >= 0 else 0
        self.__style = style if style else [0, 0, 0]

    # Getters
    @property
    def position(self) -> float:
        return self.__position

    @property
    def lane(self) -> int:
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