class Settings:
    def __init__(self, max_speed: float = 100.0):
        self.__max_speed = max_speed if max_speed > 0 else 100.0


    # Getters
    @property
    def max_speed(self) -> float:
        return self.__max_speed