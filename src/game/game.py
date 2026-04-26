import threading
import time
from collections.abc import Callable
from typing import TypedDict

from src.controller.signal_receiver_interface import SignalReceiverInterface
from .lane import Lane
from .player import Player
from .settings import Settings
from .track_module import TrackModule, TrackType
from src.logger.multi_logger import get_logger

logger = get_logger()


class LaneChangeState(TypedDict):
    lane_sequence: list[Lane]
    sequence_index: int
    track_module: TrackModule
    module_position: float
    end_time: float


class RespawnState(TypedDict):
    """Internal timer state for one inactive player awaiting respawn.

    Attributes:
        end_time (float): Absolute tick-time at which a respawn attempt may start.
    """
    end_time: float
    
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
        self.__game_tick_interval_s = 0.02
        
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

        self.__game_tick_interval_s = game_tick_interval_s

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

    # Helpers
    def __get_lane_track_length(self, lane: Lane) -> float:
        """Return total drivable length for one lane across all configured modules.

        Args:
            lane (Lane): Lane whose complete track length should be accumulated.

        Returns:
            float: Sum of all line lengths that belong to the given lane.
        """
        return sum([tm.get_line_length_for_lane(lane) for tm in self.__track_modules])

    def __get_track_module_for_lane_position(self, lane: Lane, position: float) -> tuple[TrackModule | None, float]:
        """Resolve a lane position to its module and local offset inside that module.

        The vehicle position is interpreted as a continuous coordinate on the selected lane.
        This method maps that coordinate to one concrete track module and returns the
        lane-local position used for proportional lane conversion.

        Args:
            lane (Lane): Lane used to interpret the global position value.
            position (float): Global lane position coordinate.

        Returns:
            tuple[TrackModule | None, float]:
                The matched track module and the module-local lane offset.
                Returns ``(None, 0.0)`` if the lane has no positive total length.
        """
        lane_length = self.__get_lane_track_length(lane)
        if lane_length <= 0:
            return None, 0.0

        # Normalize to one lap so lookups remain stable for wrapped positions.
        normalized_position = position % lane_length if position >= 0 else 0.0
        cumulative_length = 0.0

        for track_module in self.__track_modules:
            line_length = track_module.get_line_length_for_lane(lane)
            if line_length <= 0:
                continue

            next_cumulative_length = cumulative_length + line_length
            if normalized_position < next_cumulative_length:
                return track_module, normalized_position - cumulative_length

            cumulative_length = next_cumulative_length

        return None, normalized_position

    # Respawn
    # check tests for test details
    
    # Collision and Fall Detection
    def __violates_driving_profile(self, player: Player) -> bool:
        """Check whether vehicle kinematics violate the active line profile.

        Args:
            player (Player): Player whose current speed/acceleration are validated.

        Returns:
            bool: ``True`` when speed or acceleration is outside allowed bounds.
        """
        track_module, _ = self.__get_track_module_for_lane_position(
            player.vehicle.lane,
            player.vehicle.position,
        )
        if track_module is None:
            return True

        current_line = track_module.get_line_for_lane(player.vehicle.lane)
        if current_line is None:
            return True

        profile = current_line.driving_profile
        speed = player.vehicle.speed
        acceleration = player.vehicle.acceleration

        return (
            speed > profile.max_speed
            or speed < profile.min_speed
            or acceleration > profile.max_acceleration
            or acceleration < profile.min_acceleration
        )

    def __detect_and_apply_collisions(self):
        # TODO: implement
        # check every player against every other player on the same lane for distance violations
        # trigger player respawn if a collision with given rules (see readme) is detected
        pass

    # Further methods
    def display(self):
        # Display current game state to lcd, led, log, ...
        # TODO: implement display logic
        self.log_fully()
        pass

    def __game_loop(self):
        """Execute one simulation tick for all players.

        Per player, this tick processes controller input, movement physics, and the
        timed lane-change state machine.

        Args:
            None

        Returns:
            None: Mutates player vehicles and game-internal lane-change state.
        """        
        
        for player in self.__players:
            # check respawn state 
            if not player.vehicle.active and player.vehicle.respawn_ticks > 0:
                player.vehicle.reduce_respawn_ticks(1)
                continue

            # get newest value for acceleration from controller input
            player.vehicle.set_acceleration(player.controller.forward_press)
            
            # apply friction
            player.vehicle.apply_friction(self.__settings.friction_percent)
            
            # update speed based on acceleration and max speed
            player.vehicle.update_speed(
                self.__settings.max_speed,
                acceleration_multiplier=self.__settings.acceleration_multiplier,
            )

            # lane change trigger
            if (player.vehicle.line_change_ticks is 0 
                and player.vehicle.line_change_target is None
                and player.controller.special_1 >= self.__settings.special_1_threshold):

                target_lane: Lane | None = None
                # player is left (lane 0) -> target is right (lane -1) and vice versa
                if player.vehicle.lane is not None:
                    if self.__lanes[0] == player.vehicle.lane:
                        target_lane = self.__lanes[-1]
                    elif self.__lanes[-1] == player.vehicle.lane:
                        target_lane = self.__lanes[0]
                        
                if target_lane is not None:
                    player.vehicle.trigger_line_change(
                        target_lane=target_lane,
                        line_change_ticks=self.__settings.lane_change_ticks
                    )

            # fall down detection
            if self.__violates_driving_profile(player):
                player.vehicle.trigger_respawn(self.__settings.respawn_ticks)
                continue

            # update position and round
            # lane_track_length: total length of the current lane across all modules.
            # delta_position: distance to move in this tick, derived from current speed.
            lane_track_length = self.__get_lane_track_length(player.vehicle.lane)
            delta_position = player.vehicle.speed * self.__game_tick_interval_s
            player.vehicle.update_position(
                delta_position,
                lane_track_length,
            )
            
        # collision detection
        self.__detect_and_apply_collisions()
            
            
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
                    "special_1": player.controller.special_1,
                    # "backward_press": player.controller.backward_press,
                    # "left_press": player.controller.left_press,
                    # "right_press": player.controller.right_press,
                    # "special_2": player.controller.special_2
                },                    
            } for player in self.__players],
            "track_modules": [{
                "track_type": tm.track_type.value,
                "part_length": tm.length,
                "lines": [{
                    "line_length": line.length,
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
                "respawn_time": self.settings.respawn_time,
                "friction_percent": self.settings.friction_percent,
                "acceleration_multiplier": self.settings.acceleration_multiplier,
                "special_1_threshold": self.settings.special_1_threshold,
                "overtake_time": self.settings.lane_change_time,
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