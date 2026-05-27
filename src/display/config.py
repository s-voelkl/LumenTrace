class DisplayConfig:
    """
    Configuration settings for the DisplayManager.
    
    This class holds the configuration values used to control the visual
    effects and timings such as respawn blinking and round advancement.
    
    Attributes:
        respawn_tick_color_change (int): Number of ticks per color toggle for inactive vehicles.
        round_advance_ticks (int): Total ticks to show the round advance animation.
        round_advance_tick_color_change (int): Number of ticks per color toggle in round advance.
    """
    def __init__(
        self,
        respawn_tick_color_change: int = 10,
        round_advance_ticks: int = 20,
        round_advance_tick_color_change: int = 5,
    ):
        """
        Initialize the DisplayConfig with optional overrides.
        
        Args:
            respawn_tick_color_change (int, optional): Ticks per blink toggle. Defaults to 10.
            round_advance_ticks (int, optional): Total ticks for round advance. Defaults to 20.
            round_advance_tick_color_change (int, optional): Ticks per round blink toggle. Defaults to 5.
        """
        self.__respawn_tick_color_change = respawn_tick_color_change
        self.__round_advance_ticks = round_advance_ticks
        self.__round_advance_tick_color_change = round_advance_tick_color_change

    @property
    def respawn_tick_color_change(self) -> int:
        """
        Get the ticks per color toggle for inactive vehicles.
        
        Returns:
            int: The number of ticks.
        """
        return self.__respawn_tick_color_change

    @property
    def round_advance_ticks(self) -> int:
        """
        Get the total ticks to show the round advance animation.
        
        Returns:
            int: The total ticks duration.
        """
        return self.__round_advance_ticks

    @property
    def round_advance_tick_color_change(self) -> int:
        """
        Get the ticks per color toggle in round advance animation.
        
        Returns:
            int: The number of ticks.
        """
        return self.__round_advance_tick_color_change
