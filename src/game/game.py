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
        self.__lane_change_states: dict[int, LaneChangeState] = {}
        self.__special_1_previous_active: dict[int, bool] = {}

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

    def __get_lane_sequence_for_module(self, track_module: TrackModule, source_lane: Lane) -> list[Lane]:
        """Build the ordered lane path for one lane-change action in a module.

        The function prefers a rightward path (ascending ``lane_id``). If no rightward
        movement is possible (for example at the rightmost lane), it falls back to a
        leftward path (descending ``lane_id``).

        Args:
            track_module (TrackModule): Module in which the lane change takes place.
            source_lane (Lane): Lane where the vehicle starts.

        Returns:
            list[Lane]: Ordered sequence from ``source_lane`` to the far end in the
            selected direction. Returns an empty list if no movement is possible.
        """
        module_lanes = sorted(
            {line.lane for line in track_module.lines},
            key=lambda lane: lane.lane_id,
        )
        source_index = next((index for index, lane in enumerate(module_lanes) if lane == source_lane), -1)

        if source_index < 0:
            return []

        # Prefer rightward travel first to keep existing trigger behavior stable.
        rightward_sequence = module_lanes[source_index:]
        if len(rightward_sequence) >= 2:
            return rightward_sequence

        # If rightward travel is unavailable, allow the same trigger to go left.
        leftward_sequence = list(reversed(module_lanes[:source_index + 1]))
        return leftward_sequence if len(leftward_sequence) >= 2 else []

    def __get_lane_prefix_before_module(self, lane: Lane, target_module: TrackModule) -> float:
        """Return accumulated lane length before a specific module.

        This prefix is required to convert a module-local lane position back into the
        global lane coordinate used by ``Vehicle.position``.

        Args:
            lane (Lane): Lane used for accumulation.
            target_module (TrackModule): Module at which accumulation stops.

        Returns:
            float: Summed lane length before ``target_module``.
        """
        prefix_length = 0.0
        for track_module in self.__track_modules:
            if track_module is target_module:
                break
            prefix_length += track_module.get_line_length_for_lane(lane)
        return prefix_length

    def __start_lane_change(
        self,
        player: Player,
        track_module: TrackModule,
        module_position: float,
        current_time: float,
    ) -> bool:
        """Initialize a multi-step lane-change state for one player.

        A lane change consists of one or more adjacent hops (e.g. ``1 -> 2 -> 3 -> 4``
        or ``4 -> 3 -> 2 -> 1``).
        Each hop takes ``Settings.lane_change_time`` and is finalized in ``__game_loop``.

        Args:
            player (Player): Player whose vehicle should start changing lanes.
            track_module (TrackModule): Current module where the transition is executed.
            module_position (float): Vehicle position inside the current module.
            current_time (float): Current tick time in seconds.

        Returns:
            bool: ``True`` when a valid sequence was created, otherwise ``False``.
        """
        # Enforce lane-change permission on the source line before building any transition state.
        source_line = track_module.get_line_for_lane(player.vehicle.lane)
        if source_line is None or not source_line.driving_profile.lane_change_allowed:
            return False

        lane_sequence = self.__get_lane_sequence_for_module(track_module, player.vehicle.lane)
        if len(lane_sequence) < 2:
            return False

        controller_id = player.controller.controller_id
        # Persist hop progress per controller so the transition can span multiple ticks.
        self.__lane_change_states[controller_id] = {
            "lane_sequence": lane_sequence,
            "sequence_index": 0,
            "track_module": track_module,
            "module_position": module_position,
            "end_time": current_time + self.__settings.lane_change_time,
        }

        return True

    def __finalize_lane_change(
        self,
        player: Player,
        lane_change_state: LaneChangeState,
        current_time: float,
    ) -> None:
        """Finalize one lane-change hop and schedule the next hop when needed.

        The method converts the local module position proportionally from the current
        lane to the next lane, updates the vehicle, and either continues or ends the
        transition based on remaining sequence steps.

        Args:
            player (Player): Player whose pending lane-change state is processed.
            lane_change_state (LaneChangeState): Mutable state of the current transition.
            current_time (float): Current tick time in seconds.

        Returns:
            None: The method updates vehicle and internal state in place.
        """
        track_module = lane_change_state["track_module"]
        lane_sequence = lane_change_state["lane_sequence"]
        sequence_index = int(lane_change_state["sequence_index"])
        module_position = lane_change_state["module_position"]

        assert isinstance(track_module, TrackModule)
        assert isinstance(lane_sequence, list)
        assert 0 <= sequence_index < len(lane_sequence) - 1

        source_lane = lane_sequence[sequence_index]
        target_lane = lane_sequence[sequence_index + 1]

        # Keep relative progress inside the module while switching lane geometry.
        converted_position = track_module.convert_position_between_lanes(
            source_lane=source_lane,
            target_lane=target_lane,
            source_position=float(module_position),
        )
        target_prefix = self.__get_lane_prefix_before_module(target_lane, track_module)

        player.vehicle.set_lane(target_lane)
        player.vehicle.set_position(target_prefix + converted_position)

        next_sequence_index = sequence_index + 1
        lane_change_state["sequence_index"] = next_sequence_index
        lane_change_state["module_position"] = converted_position

        if next_sequence_index < len(lane_sequence) - 1:
            # Continue with the next adjacent hop after another fixed delay.
            lane_change_state["end_time"] = current_time + self.__settings.lane_change_time
            self.__lane_change_states[player.controller.controller_id] = lane_change_state
        else:
            del self.__lane_change_states[player.controller.controller_id]

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
        # Evaluate time once so all decisions in this tick share the same time base.
        current_time = time.perf_counter()
        
        for player in self.__players:
            controller_id = player.controller.controller_id
            # Trigger lane change on a rising edge to avoid re-triggering while held.
            is_special_1_active = player.controller.special_1 > self.__settings.special_1_threshold
            was_special_1_active = self.__special_1_previous_active.get(controller_id, False)
            special_1_triggered = is_special_1_active and not was_special_1_active
            self.__special_1_previous_active[controller_id] = is_special_1_active

            # get newest value for acceleration from controller input
            player.vehicle.set_acceleration(player.controller.forward_press)
            
            # apply friction
            player.vehicle.apply_friction(self.__settings.friction_percent)
            
            # update speed based on acceleration and max speed
            player.vehicle.update_speed(
                self.__settings.max_speed,
                acceleration_multiplier=self.__settings.acceleration_multiplier,
            )

            # During a lane change, movement is paused until the timed hop completes.
            lane_change_state = self.__lane_change_states.get(controller_id)
            if lane_change_state is not None:
                end_time = float(lane_change_state["end_time"])
                if current_time >= end_time:
                    self.__finalize_lane_change(player, lane_change_state, current_time)
                else:
                    # While a hop timer is running, skip regular movement updates.
                    continue

            if special_1_triggered:
                current_track_module, module_position = self.__get_track_module_for_lane_position(
                    player.vehicle.lane,
                    player.vehicle.position,
                )

                if current_track_module is not None:
                    current_line = current_track_module.get_line_for_lane(player.vehicle.lane)
                    # driving profile must allow lane changes
                    can_change_lane = (
                        current_line is not None and current_line.driving_profile.lane_change_allowed
                    )

                    # Start asynchronous lane-change progression and skip normal movement this tick.
                    if can_change_lane and self.__start_lane_change(
                        player,
                        current_track_module,
                        module_position,
                        current_time,
                    ):
                        continue

            # update position and round
            lane_track_length = self.__get_lane_track_length(player.vehicle.lane)
            # Normal movement is only applied when no lane transition consumed this tick.
            player.vehicle.update_position(
                player.vehicle.speed * self.__game_tick_interval_s,
                lane_track_length,
            )
            
    
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