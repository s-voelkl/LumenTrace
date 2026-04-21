import threading
import time
from collections.abc import Callable

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
        self.__stop_event = threading.Event()
        self.__threads: list[threading.Thread] = []

        logger.log_json({
            "event": "game_initialized",
            "players": [player.name for player in self.__players],
            "settings": self.__settings.__dict__,
            "track_length": self.__length
        })
        
    def start_game(
        self,
        fetch_interval_s: float = 0.01,
        display_interval_s: float = 0.02,
        game_tick_interval_s: float = 0.02,
    ):
        logger.log_json({
            "event": "game_started",
        })

        # Each worker owns one responsibility so timing stays predictable and easy to review.
        self.__stop_event.clear()
        self.__threads = [
            threading.Thread(
                target=self.__run_periodic_loop,
                name="GameFetchThread",
                args=(self.fetch_data, fetch_interval_s),
                daemon=False,
            ),
            threading.Thread(
                target=self.__run_periodic_loop,
                name="GameDisplayThread",
                args=(self.display, display_interval_s),
                daemon=False,
            ),
            threading.Thread(
                target=self.__run_periodic_loop,
                name="GameTickThread",
                args=(self.__game_loop, game_tick_interval_s),
                daemon=False,
            ),
        ]

        for thread in self.__threads:
            thread.start()

        try:
            for thread in self.__threads:
                thread.join()
        except KeyboardInterrupt:
            self.stop_game()
            for thread in self.__threads:
                thread.join()

    def stop_game(self):
        self.__stop_event.set()

    def __run_periodic_loop(self, action: Callable[[], None], interval_s: float) -> None:
        # Use a monotonic clock so the loop keeps its cadence even if wall time changes.
        next_run = time.perf_counter()
        while not self.__stop_event.is_set():
            next_run += interval_s
            action()

            remaining_s = next_run - time.perf_counter()
            if remaining_s > 0:
                self.__stop_event.wait(remaining_s)
            else:
                # If the action took longer than the requested cadence, continue immediately.
                next_run = time.perf_counter()

    def fetch_data(self):
        self.__signal_receiver.receive_signal()

    def display(self):
        # Display current game state to lcd, led, log, ...
        # TODO: implement display logic
        self.log_fully()
        pass

    def __game_loop(self):
        # Keep the game tick on a fixed cadence so future physics and scoring logic can be added here.
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