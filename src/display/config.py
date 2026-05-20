class DisplayConfig:
    def __init__(
        self,
        respawn_tick_color_change: int = 10,
        round_advance_ticks: int = 20,
        round_advance_tick_color_change: int = 5,
    ):
        self.__respawn_tick_color_change = respawn_tick_color_change
        self.__round_advance_ticks = round_advance_ticks
        self.__round_advance_tick_color_change = round_advance_tick_color_change

    @property
    def respawn_tick_color_change(self) -> int:
        return self.__respawn_tick_color_change

    @property
    def round_advance_ticks(self) -> int:
        return self.__round_advance_ticks

    @property
    def round_advance_tick_color_change(self) -> int:
        return self.__round_advance_tick_color_change
