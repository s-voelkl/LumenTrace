from src.controller.signal_receiver_interface import SignalReceiverInterface
from .lane import Lane
from .player import Player
from .settings import Settings
from .track_module import TrackModule
from src.logger.multi_logger import get_logger

logger = get_logger()
    
class Game:    
    def __init__(self,
        players: list[Player],
        settings: Settings,
        track_modules: list[TrackModule],
        signal_receiver: SignalReceiverInterface,
        lanes: list[Lane]):
        self.__players = players if players else []
        self.__settings = settings
        self.__track_modules = track_modules if track_modules else []
        self.__length = sum([tm.length for tm in track_modules]) if track_modules else 0
        self.__signal_receiver = signal_receiver
        self.__lanes = lanes if lanes else []

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
        # multithreaded game loop for the folling methods: 
        # - fetch data, this automatically updates the player controller with relevant data
        # - display, this displays the current game state to the lcd, led, log, ...
        # - main game loop, every 0.02 seconds.
        
        
        
        
    def fetch_data(self):
        self.__signal_receiver.receive_signal()

    def display(self):
        # display current game state to lcd, led, log, ...
        # TODO: implement display logic
        self.log_fully()
        pass
    
    def log_fully(self):       
        logger.log_json({
            "event": "game_state",
            "lanes": [{
                "lane_id": lane.lane_id
            } for lane in self.__lanes],
            "players": [{
                "name": player.name,
                "wins": player.wins,
                "losses": player.losses,
                "vehicle": {
                    "position": player.vehicle.position,
                    "lane": player.vehicle.lane.lane_id,
                    "speed": player.vehicle.speed,
                    "acceleration": player.vehicle.acceleration,
                    "round": player.vehicle.round,
                    "style": player.vehicle.style
                },
                "controller": {
                    "forward_press": player.controller.forward_press,
                    "backward_press": player.controller.backward_press,
                    "left_press": player.controller.left_press,
                    "right_press": player.controller.right_press,
                    "special_1": player.controller.special_1,
                    "special_2": player.controller.special_2
                },                    
            } for player in self.__players],
            "track_modules": [{
                "track_type": tm.track_type.value,
                "length": tm.length,
                "lines": [{
                    "length": line.length,
                    "lane_id": line.lane.lane_id,
                    "driving_profile": {
                        "max_speed": line.driving_profile.max_speed,
                        "min_speed": line.driving_profile.min_speed,
                        "max_acceleration": line.driving_profile.max_acceleration,
                        "min_acceleration": line.driving_profile.min_acceleration,
                        "lane_change_allowed": line.driving_profile.lane_change_allowed
                    }
                } for line in tm.lines]
            } for tm in self.__track_modules],
            "settings": {
                "max_speed": self.settings.max_speed,
            },
            "length": self.length,
            "signal_receiver": { 
                "data": dict(self.__signal_receiver.get_data())
            }
        })
                        
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
    
    @property
    def signal_receiver(self) -> SignalReceiverInterface:
        return self.__signal_receiver
    
    @property
    def lanes(self) -> list[Lane]:
        return self.__lanes