# class TrackModule
# attr: length (float), List of Lines
class TrackModule:
    def __init__(self, length: float = 0, lines: list[int] = []):
        self.__length = length if length >= 0 else 0
        self.__lines = lines if lines else []

    # Getters
    @property
    def length(self) -> float:
        return self.__length

    @property
    def lines(self) -> list[int]:
        return self.__lines