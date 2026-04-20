from .player import Player
from .settings import Settings
from .track_module import TrackModule
from logger.multi_logger import get_logger

logger = get_logger()

class Game:    
    def __init__(self,
        players: list[Player],
        settings: Settings,
        track_modules: list[TrackModule]):
        self.__players = players if players else []
        self.__settings = settings
        self.__track_modules = track_modules if track_modules else []
        self.__length = sum([tm.length for tm in track_modules]) if track_modules else 0
        
        logger.log_json({
            "event": "game_initialized",
            "players": [player.name for player in self.__players],
            "settings": self.__settings.__dict__,
            "track_length": self.__length
        })
        
    def start_game(self):
        logger.log_json({
            "event": "game_started",
        })
        # TODO: start the game loop (multithreaded?)
        
        
    def __fetch_data(self):
        # fetch current data from the player inputs (player controllers)
        for player in self.__players:
            pass
        # TODO: fetch player inputs
        
    def __display(self):
        # display current game state to lcd, led, log, ...
        # TODO: implement display logic
        self.__log()
        pass
    
    def __log(self):
        # log current game state per cycle
        # TODO: log every possible metric (e.g. player positions, controller inputs, ...)
        pass
    
    # Getters
    @property
    def players(self) -> list[Player]:
        return self.__players
    
    @property
    def settings(self) -> Settings:
        return self.__settings
    
    @property
    def track_modules(self) -> list[TrackModule]:
        return self.__track_modules
    
    @property
    def length(self) -> float:
        return self.__length