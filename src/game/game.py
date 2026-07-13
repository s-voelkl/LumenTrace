import threading
import time
from collections.abc import Callable
from typing import Any, Dict

from src.controller.signal_receiver_interface import SignalReceiverInterface
from src.round_counter.round_counter import RoundCounter
from .lane import Lane
from .player import Player
from .settings import Settings
from .track_module import TrackModule, TrackType
from src.logger.multi_logger import get_logger

# Audio support is optional so the simulation and unit tests can run in
# headless environments without the audio backend installed.
try:
    from src.sound.sound_manager import GameSound
    from src.sound.motor_sound import MotorSound
except Exception:  # pragma: no cover - audio backend is environment dependent
    GameSound = None  # type: ignore[assignment]
    MotorSound = None  # type: ignore[assignment]

logger = get_logger()


class Game:
    """Core simulation loop for player movement, lane changes, collisions, and respawns.

    The game is tick-based. Each tick updates active players in a deterministic order,
    then resolves collisions. Inactive players remain in respawn state and are retried
    according to the rules from the project README.
    """

    def __init__(
        self,
        players: list[Player],
        settings: Settings,
        track_modules: list[TrackModule],
        signal_receiver: SignalReceiverInterface,
        lanes: list[Lane],
        display_manager,  # explicitly not imported to avoid circular dependency
        sound_manager=None,
        round_counters: Dict[Player, RoundCounter]={},  # explicitly not imported to avoid circular dependency
    ):

        self.__players = players if players else []
        self.__settings = settings
        self.__track_modules = track_modules if track_modules else []
        self.__length = sum([tm.length for tm in track_modules]) if track_modules else 0
        self.__signal_receiver = signal_receiver
        self.__lanes = lanes if lanes else []
        self.__display_manager = display_manager
        self.__sound_manager = sound_manager
        self.__event_history: list[dict[str, Any]] = []
        self.__event_history_limit = 200
        self.__tick_count = 0
        self.__round_counters = round_counters if round_counters else {}

        # Per-player audio state. Motor sounds are continuous engine loops,
        # while the edge-tracking dictionaries make one-shot effects (lane
        # change, warning) fire only on state transitions instead of every tick.
        self.__motor_sounds: dict[Player, Any] = {}
        self.__warning_active: dict[Player, bool] = {}

        self.__stop_event = threading.Event()
        self.__threads: list[threading.Thread] = []
        self.__game_tick_interval_s = 0.02

        self.__record_event(
            {
                "event": "game_initialized",
                "players": [player.name for player in self.__players],
                "settings": self.__settings.__dict__,
                "track_length": self.__length,
            }
        )

    # main game loop
    def __game_loop(self):
        """Execute one simulation tick for all players.

        Per player, this tick processes controller input, movement physics, and the
        timed lane-change state machine.

        Args:
            None

        Returns:
            None: Mutates player vehicles and game-internal lane-change state.
        """

        self.__tick_count += 1

        for player in self.__players:
            vehicle = player.vehicle

            if not vehicle.active:
                # Keep the engine audible but idle while waiting to respawn.
                self.__update_motor_sound(player)
                self.__handle_inactive_player_tick(player)
                continue

            # map the input to acceleration and apply it
            vehicle_acceleration = self.map_forward_press_to_acceleration(
                player.controller.forward_press
            )
            vehicle.set_acceleration(
                vehicle_acceleration,
                self.__settings.min_acceleration,
                self.__settings.max_acceleration,
            )
            vehicle.apply_friction(self.__settings.friction_percent)
            vehicle.update_speed(
                self.__settings.max_speed,
                acceleration_multiplier=self.__settings.acceleration_multiplier,
            )

            self.__handle_lane_change(player, player.controller.special_1 > 0.5)

            track_module, _ = (
                self.get_track_module_for_lane_position(
                    vehicle.lane,
                    vehicle.position,
                )
                if vehicle.lane is not None
                else (None, 0.0)
            )
            if track_module is None or vehicle.lane is None:
                self.__fall_player(
                    player, "lane is ended: active lane/module not resolvable"
                )
                continue

            current_line = track_module.get_line_for_lane(vehicle.lane)
            if current_line is None:
                self.__fall_player(
                    player, "lane is ended: missing line for active lane"
                )
                continue

            profile_reason = self.__get_profile_violation_reason(
                player, current_line.driving_profile
            )
            if profile_reason is not None:
                self.__fall_player(player, profile_reason)
                continue

            # Warn the player when speed or acceleration approaches the limits
            # allowed by the current driving profile.
            self.__update_warning_sound(player, current_line.driving_profile)

            delta_position = vehicle.speed * self.__game_tick_interval_s
            lane_gap_reason = self.__lane_gap_reason(player, delta_position)
            if lane_gap_reason is not None:
                self.__fall_player(player, lane_gap_reason)
                continue

            if vehicle.lane is None:
                self.__fall_player(
                    player, "lane is ended: vehicle lane is None after movement"
                )
                continue

            lane_track_length = self.get_lane_track_length(vehicle.lane)

            # handle possible round changes as an event trigger
            round_change = vehicle.update_position(delta_position, lane_track_length)
            if round_change != 0:
                if (
                    self.__sound_manager is not None
                    and GameSound is not None
                    and round_change > 0
                ):
                    self.__play_positional_sound(
                        player, GameSound.CAR_LAP_1, volume=90.0
                    )

                self.__record_event(
                    {
                        "event": "round_change",
                        "player": player.name,
                        "change": round_change,
                        "new_round_value": vehicle.round,
                        "speed": vehicle.speed,
                        "acceleration": vehicle.acceleration,
                    }
                )

            if not vehicle.active:
                continue

            track_module_after, _ = (
                self.get_track_module_for_lane_position(
                    vehicle.lane,
                    vehicle.position,
                )
                if vehicle.lane is not None
                else (None, 0.0)
            )
            if track_module_after is None or vehicle.lane is None:
                self.__fall_player(
                    player,
                    "lane is ended: active lane/module not resolvable after movement",
                )
                continue

            current_line_after = track_module_after.get_line_for_lane(vehicle.lane)
            if current_line_after is None:
                self.__fall_player(
                    player, "lane is ended: missing line for active lane after movement"
                )
                continue

            profile_reason_after = self.__get_profile_violation_reason(
                player, current_line_after.driving_profile
            )
            if profile_reason_after is not None:
                self.__fall_player(player, profile_reason_after)
                continue

            # Reflect the final speed, acceleration and track position of this
            # tick in the continuous engine sound.
            self.__update_motor_sound(player)

        self.__detect_and_apply_collisions()

    def log_fully(self):
        logger.log_json(
            {
                "event": "game_state",
                "lanes": [{"lane_id": lane.lane_id} for lane in self.__lanes],
                "players": [
                    {
                        "name": player.name,
                        "vehicle": {
                            "position": player.vehicle.position,
                            "lane": player.vehicle.lane.lane_id
                            if player.vehicle.lane is not None
                            else None,
                            "speed": player.vehicle.speed,
                            "acceleration": player.vehicle.acceleration,
                            "round": player.vehicle.round,
                            "primary_color": player.vehicle.primary_color,
                            "decelerate_color": player.vehicle.decelerate_color,
                            "accelerate_color": player.vehicle.accelerate_color,
                        },
                        "controller": {
                            "forward_press": player.controller.forward_press,
                            "special_1": player.controller.special_1,
                            # "backward_press": player.controller.backward_press,
                            # "left_press": player.controller.left_press,
                            # "right_press": player.controller.right_press,
                            # "special_2": player.controller.special_2
                        },
                    }
                    for player in self.__players
                ],
                "track_modules": [
                    {
                        "track_type": tm.track_type.value,
                        "part_length": tm.length,
                        "lines": [
                            {
                                "line_length": line.length,
                                "lane_id": line.lane.lane_id,
                                "driving_profile": {
                                    "max_speed": line.driving_profile.max_speed,
                                    "min_speed": line.driving_profile.min_speed,
                                    "max_acceleration": line.driving_profile.max_acceleration,
                                    "min_acceleration": line.driving_profile.min_acceleration,
                                    "lane_change_allowed": line.driving_profile.lane_change_allowed,
                                },
                            }
                            for line in tm.lines
                        ],
                    }
                    for tm in self.__track_modules
                ],
                "settings": {
                    "max_speed": self.settings.max_speed,
                    "min_acceleration": self.settings.min_acceleration,
                    "max_acceleration": self.settings.max_acceleration,
                    "respawn_ticks": self.settings.respawn_ticks,
                    "friction_percent": self.settings.friction_percent,
                    "acceleration_multiplier": self.settings.acceleration_multiplier,
                    "lane_change_window": self.settings.lane_change_window,
                    "vehicle_crash_distance": self.settings.vehicle_crash_distance,
                },
                "length": self.length,
                "signal_receiver": {"data": dict(self.__signal_receiver.get_data())},
            }
        )

    def start_game(
        self,
        fetch_interval_s: float = 0.01,
        display_interval_s: float = 0.02,
        game_tick_interval_s: float = 0.02,
    ):
        self.__record_event(
            {
                "event": "game_started",
                "fetch_interval_s": fetch_interval_s,
                "display_interval_s": display_interval_s,
                "game_tick_interval_s": game_tick_interval_s,
            }
        )

        self.__game_tick_interval_s = game_tick_interval_s
        
        if self.__sound_manager is not None and MotorSound is not None:
            for player in self.__players:
                self.__motor_sounds[player] = MotorSound(
                    self.__sound_manager, max_volume=10, idle_volume=2
                )

        # Start the continuous per-player engine loops before the worker
        # threads begin updating their pitch and volume each tick.
        self.__start_motor_sounds()

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
        finally:
            self.__stop_motor_sounds()

    def stop_game(self):
        self.__stop_event.set()

        if self.__sound_manager is not None:
            self.__sound_manager.stop_all()

        # if self.__display_manager is not None:
        #     self.__display_manager.clear_all()

    def __run_periodic_loop(
        self, action: Callable[[], None], interval_s: float
    ) -> None:
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

    def __record_event(self, payload: dict[str, Any]) -> None:
        """Store and emit one structured game event."""
        event = {"tick": self.__tick_count, **payload}
        self.__event_history.append(event)
        if len(self.__event_history) > self.__event_history_limit:
            self.__event_history = self.__event_history[-self.__event_history_limit :]
        logger.log_json(event)

    def __update_round_counter(self):
        if not self.__round_counters:
            return
        
        # Periodically iterate over all players and push updates to their assigned panel
        for player in self.__players:
            if player in self.__round_counters:
                round_counter = self.__round_counters[player]
                round_val = player.vehicle.round
                try:
                    round_counter.display_round(round_val)
                    # logger.log(f"Updated round counter for player {player.name} to {round_val}")
                except Exception as e:
                    logger.log(
                        f"Error updating round counter for player {player.name}: {e}"
                    )
            if player.vehicle.round >= self.__settings.rounds_to_win:
                logger.log(f"Player {player.name} has won the game!")
                self.stop_game()
                break
            
    def clear_round_counters(self):
        """Clear all round counters to reset the display."""
        for player, round_counter in self.__round_counters.items():
            try:
                round_counter.clear()
            except Exception as e:
                logger.log(
                    f"Error clearing round counter for player {player.name}: {e}"
                )

    def tick_once(
        self,
        *,
        fetch_data: bool = True,
        show_display: bool = False,
        game_tick_interval_s: float | None = None,
    ) -> None:
        """Run one deterministic game tick.

        This API is intended for simulation and unit tests where external control
        over tick cadence is preferred over threaded background loops.

        Args:
            fetch_data (bool, optional): Whether input receiver should be polled first.
            show_display (bool, optional): Whether to call ``display`` after tick update.
            game_tick_interval_s (float | None, optional): Tick duration used by
                movement integration. ``None`` keeps the current configured value.
        """
        if game_tick_interval_s is not None:
            self.__game_tick_interval_s = game_tick_interval_s

        if fetch_data:
            self.fetch_data()

        self.__game_loop()

        # check win condition
        if self.__settings is not None and self.__settings.rounds_to_win is not None:
            for player in self.__players:
                if player.vehicle.round >= self.__settings.rounds_to_win:
                    self.__record_event(
                        {
                            "event": "player_won",
                            "player": player.name,
                            "rounds": player.vehicle.round,
                        }
                    )

        if show_display:
            self.display()

    # display
    def display(self):
        """
        Updates the round counters and renders the main display.
        Running both on the same thread prevents concurrent access to the shared strips.
        """
        
        self.__update_round_counter()
        # Explicitly yield the GIL immediately after the blocking hardware write.
        # This allows the physics and audio threads to run smoothly mid-frame.
        time.sleep(0.001)
        
        if self.__display_manager is not None:
            self.__display_manager.update(self)

    # helpers
    def get_lane_track_length(self, lane: Lane) -> float:
        """Return total drivable length for one lane across all configured modules.

        Args:
            lane (Lane): Lane whose complete track length should be accumulated.

        Returns:
            float: Sum of all line lengths that belong to the given lane.
        """
        return sum([tm.get_line_length_for_lane(lane) for tm in self.__track_modules])

    def __get_track_module_index_and_local_position(
        self, lane: Lane, position: float
    ) -> tuple[int | None, float]:
        """Resolve one lane position to a concrete module index and lane-local position.

        Args:
            lane (Lane): Lane in which the position is interpreted.
            position (float): Global lane position value.

        Returns:
            tuple[int | None, float]:
                The matched module index and local position in that module.
                Returns ``(None, 0.0)`` if no lane segment can be resolved.
        """
        lane_length = self.get_lane_track_length(lane)
        if lane_length <= 0:
            return None, 0.0

        normalized_position = position % lane_length if position >= 0 else 0.0
        cumulative = 0.0
        for index, module in enumerate(self.__track_modules):
            line_length = module.get_line_length_for_lane(lane)
            if line_length <= 0:
                continue

            upper = cumulative + line_length
            if normalized_position < upper:
                return index, normalized_position - cumulative
            cumulative = upper

        return None, normalized_position

    def __build_global_lane_position(
        self, lane: Lane, module_index: int, module_local_position: float
    ) -> float:
        """Build global lane position from a module-local coordinate.

        Args:
            lane (Lane): Target lane.
            module_index (int): Module index for the local position.
            module_local_position (float): Offset within the lane line of that module.

        Returns:
            float: Global lane position coordinate.
        """
        global_position = 0.0
        for idx in range(module_index):
            global_position += self.__track_modules[idx].get_line_length_for_lane(lane)
        return max(0.0, global_position + max(0.0, module_local_position))

    def get_track_module_for_lane_position(
        self, lane: Lane, position: float
    ) -> tuple[TrackModule | None, float]:
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
        module_index, local_position = self.__get_track_module_index_and_local_position(
            lane, position
        )
        if module_index is None:
            return None, local_position
        return self.__track_modules[module_index], local_position

    def __fall_player(self, player: Player, reason: str) -> None:
        """Move one player into respawn state and clear pending lane-change state."""
        # logger.log("Collision detected for player " + player.name + ": " + reason)
        if player.vehicle.active:
            vehicle = player.vehicle
            if self.__sound_manager is not None and GameSound is not None:
                self.__play_positional_sound(player, GameSound.CAR_CRASH_2, volume=30.0)

            respawn_module_index = self.__resolve_respawn_module_index(
                vehicle.lane,
                vehicle.position,
            )
            vehicle.set_respawn_module_index(respawn_module_index)
            vehicle.trigger_respawn(self.__settings.respawn_ticks)

            self.__record_event(
                {
                    "event": "player_fell",
                    "player": player.name,
                    "reason": reason,
                    "lane": vehicle.lane.lane_id if vehicle.lane is not None else None,
                    "position": vehicle.position,
                    "speed": vehicle.speed,
                    "acceleration": vehicle.acceleration,
                    "respawn_ticks": self.__settings.respawn_ticks,
                    "respawn_module_index": respawn_module_index,
                }
            )

    def __lane_gap_reason(self, player: Player, delta_position: float) -> str | None:
        """Return a short reason when movement enters a lane gap."""
        if delta_position == 0:
            return None

        lane = player.vehicle.lane
        if lane is None:
            return "lane is ended: vehicle has no lane"
        if not self.__track_modules:
            return "lane is ended: no track modules configured"

        module_index, module_position = (
            self.__get_track_module_index_and_local_position(
                lane, player.vehicle.position
            )
        )
        if module_index is None:
            return "lane is ended: current lane position not resolvable"

        remaining = delta_position
        track_module_count = len(self.__track_modules)

        while remaining != 0:
            current_module = self.__track_modules[module_index]
            current_line_length = current_module.get_line_length_for_lane(lane)
            if current_line_length <= 0:
                return f"lane is ended in module {module_index}"

            if remaining > 0:
                distance_to_end = max(current_line_length - module_position, 0.0)
                if remaining <= distance_to_end:
                    return None

                remaining -= distance_to_end
                module_index = (module_index + 1) % track_module_count
                if (
                    self.__track_modules[module_index].get_line_length_for_lane(lane)
                    <= 0
                ):
                    return f"lane is ended: missing next lane segment in module {module_index}"
                module_position = 0.0
                continue

            distance_to_start = max(module_position, 0.0)
            if -remaining <= distance_to_start:
                return None

            remaining += distance_to_start
            module_index = (module_index - 1) % track_module_count
            previous_line_length = self.__track_modules[
                module_index
            ].get_line_length_for_lane(lane)
            if previous_line_length <= 0:
                return f"lane is ended: missing previous lane segment in module {module_index}"
            module_position = previous_line_length

        return None

    @staticmethod
    def __get_profile_violation_reason(player: Player, profile: Any) -> str | None:
        """Return short violation string for speed/acceleration bounds."""
        speed = player.vehicle.speed
        acceleration = player.vehicle.acceleration

        if speed > profile.max_speed:
            return f"speed ({speed:.2f}) > {profile.max_speed:.2f}"
        if speed < profile.min_speed:
            return f"speed ({speed:.2f}) < {profile.min_speed:.2f}"
        if acceleration > profile.max_acceleration:
            return f"acceleration ({acceleration:.2f}) > {profile.max_acceleration:.2f}"
        if acceleration < profile.min_acceleration:
            return f"acceleration ({acceleration:.2f}) < {profile.min_acceleration:.2f}"

        return None

    @staticmethod
    def map_forward_press_to_acceleration(forward_press: float) -> float:
        input_min = 42000  # 70% of 65536 is 45875, but rounding down to 42000 to give some buffer for switch activation
        input_max = 65536
        output_min = 0
        output_max = 100
        if forward_press < input_min:
            return 0.0
        if forward_press > input_max:
            return 100.0

        # calculation for the mapping: linear interpolation
        # $$f(x) = (x - \text{input\_min}) \cdot \frac{\text{output\_max} - \text{output\_min}}{\text{input\_max} - \text{input\_min}} + \text{output\_min}$$
        mapped_signal: float = (forward_press - input_min) * (
            output_max - output_min
        ) // (input_max - input_min) + output_min
        # logger.log("Input: " + str(forward_press) + " -> " + str(mapped_signal))
        return mapped_signal

    def __handle_lane_change(self, player: Player, special_1_pressed: bool) -> None:
        """Handle execution of lane changes (starting and finishing) for the given player."""
        vehicle = player.vehicle
        lane = vehicle.lane
        if lane is None or len(self.__lanes) < 3:
            return

        idx, local_pos = self.__get_track_module_index_and_local_position(lane, vehicle.position)
        if idx is None:
            return
        module_index: int = idx
        module = self.__track_modules[module_index]
        line = module.get_line_for_lane(lane)
        if not (line and line.driving_profile.lane_change_allowed):
            return

        left_lane, middle_lane, right_lane = self.__lanes[0], self.__lanes[1], self.__lanes[2]
        window = self.__settings.lane_change_window
        dist_to_end = line.length - local_pos
        dist_since_last = abs(local_pos - vehicle.lane_change_start_position)

        target_lane = None
        target_outer = None
        event_type = None

        if lane in (left_lane, right_lane):
            # Only start if button is pressed, we have enough space, and enough distance since last transition.
            if special_1_pressed and dist_to_end > window and dist_since_last >= window:
                target_lane = middle_lane
                event_type = "lane_change_started"
                target_outer = right_lane if lane == left_lane else left_lane
        elif lane == middle_lane:
            # Finish if we are near the end (auto) or button is pressed after minimal distance (manual).
            if dist_to_end <= window or (special_1_pressed and dist_since_last >= window):
                target_lane = vehicle.lane_change_target or right_lane
                event_type = "lane_change_finished"

        if target_lane:
            target_pos = module.convert_position_between_lanes(lane, target_lane, local_pos)
            global_pos = self.__build_global_lane_position(target_lane, module_index, target_pos)

            old_lane_id = lane.lane_id
            vehicle.set_lane(target_lane)
            vehicle.set_position(global_pos)

            if event_type == "lane_change_started":
                vehicle.set_lane_change(target_outer, target_pos)
            else:
                # Store the finish position to enforce minimal distance until the next start.
                vehicle.set_lane_change(None, target_pos)

            if self.__sound_manager is not None and GameSound is not None:
                self.__play_positional_sound(player, GameSound.COIN_2, volume=30.0)

            self.__record_event(
                {
                    "event": event_type,
                    "player": player.name,
                    "from_lane": old_lane_id,
                    "to_lane": target_lane.lane_id,
                }
            )

    # motor sound initialization
    def __start_motor_sounds(self) -> None:
        """Start the looping engine sound for every player."""
        for motor_sound in self.__motor_sounds.values():
            motor_sound.start()

    def __stop_motor_sounds(self) -> None:
        """Stop the looping engine sound for every player."""
        for motor_sound in self.__motor_sounds.values():
            motor_sound.stop()

    # Sound helpers
    def __get_stereo_ratio_left_for_player(self, player: Player) -> float:
        """Return the left-channel stereo ratio for a player's current module.

        Args:
            player (Player): Player whose track position selects the module.

        Returns:
            float: Left ratio in [0.0, 1.0]; defaults to ``0.5`` (centered)
                when the player has no resolvable lane or module.
        """
        lane = player.vehicle.lane
        if lane is None:
            return 0.5

        module, _ = self.get_track_module_for_lane_position(
            lane, player.vehicle.position
        )
        if module is None:
            return 0.5
        return module.sound_stereo_ratio_left

    @staticmethod
    def __stereo_ratio_to_channel_volumes(ratio_left: float) -> tuple[float, float]:
        """Convert a left stereo ratio to (left, right) channel volumes (0-100)."""
        ratio_left = min(1.0, max(0.0, ratio_left))
        return ratio_left * 100.0, (1.0 - ratio_left) * 100.0

    def __play_positional_sound(
        self, player: Player, sound: Any, volume: float
    ) -> None:
        """Play a one-shot sound panned to the player's current track module.

        Args:
            player (Player): Player used to derive the stereo position.
            sound (GameSound): Sound effect to play.
            volume (float): Overall volume of the effect (0-100).
        """
        if self.__sound_manager is None or GameSound is None:
            return

        ratio_left = self.__get_stereo_ratio_left_for_player(player)
        left_volume, right_volume = self.__stereo_ratio_to_channel_volumes(ratio_left)

        # logger.log("Playing positional sound: " + str(sound) + " for player " + player.name + " with left volume " + str(left_volume) + " and right volume " + str(right_volume))

        self.__sound_manager.play(
            sound=sound,
            # loop=False,
            # pitch=1.0,
            volume=volume,
            left_volume=left_volume,
            right_volume=right_volume,
        )

    @staticmethod
    def __is_near_profile_bounds(
        vehicle, profile: Any, threshold: float = 0.1, settings_max_speed: float = 100
    ) -> bool:
        """Return whether speed or acceleration is close to a profile limit.

        A value is considered "near a bound" when it falls within ``threshold``
        of the span on either side, i.e. inside ``[lower, lower + margin]`` or
        ``[upper - margin, upper]`` with ``margin = (upper - lower) * threshold``.
        This captures the upper warning band ``[max * 0.8, max]`` as well as the
        symmetric band next to the lower limit for both speed and acceleration.

        Args:
            vehicle: Vehicle whose speed and acceleration are inspected.
            profile (Any): Driving profile providing the min/max bounds.
            threshold (float): Fraction of the span treated as the warning band.
            settings_max_speed (float): The settings maximum speed limit.

        Returns:
            bool: ``True`` when speed or acceleration is within the warning band.
        """
        # If the profile max speed is >= settings max speed, the profile is not
        # constraining the vehicle beyond the settings limit, so no warning is needed.
        is_profile_constraining = profile.max_speed < settings_max_speed

        if not is_profile_constraining:
            return False

        def near(value: float, lower: float, upper: float) -> bool:
            span = upper - lower
            if span <= 0:
                return False
            margin = span * threshold
            return value <= lower + margin or value >= upper - margin

        return near(vehicle.speed, profile.min_speed, profile.max_speed) or near(
            vehicle.acceleration,
            profile.min_acceleration,
            profile.max_acceleration,
        )

    def __update_warning_sound(self, player: Player, profile: Any) -> None:
        """Play a warning sound once when a player enters the warning band.

        The warning is edge-triggered: it fires only on the transition into the
        warning band and resets once the player leaves it, preventing the sound
        from repeating on every tick.
        """
        if self.__sound_manager is None or GameSound is None:
            return

        is_near = self.__is_near_profile_bounds(
            player.vehicle, profile, settings_max_speed=self.settings.max_speed
        )
        was_near = self.__warning_active.get(player, False)

        if is_near and not was_near:
            self.__play_positional_sound(player, GameSound.WARNING_2, volume=22.0)

        self.__warning_active[player] = is_near

    def __update_motor_sound(self, player: Player) -> None:
        """Update one player's continuous engine sound from its vehicle state."""
        motor_sound = self.__motor_sounds.get(player)
        if motor_sound is None:
            return

        vehicle = player.vehicle
        max_speed = self.__settings.max_speed
        max_acceleration = self.__settings.max_acceleration
        speed_ratio = abs(vehicle.speed) / max_speed if max_speed else 0.0
        acceleration_ratio = (
            abs(vehicle.acceleration) / max_acceleration if max_acceleration else 0.0
        )
        ratio_left = self.__get_stereo_ratio_left_for_player(player)
        motor_sound.update(speed_ratio, acceleration_ratio, ratio_left)

    # collision and respawn
    def __resolve_respawn_module_index(
        self, lane: Lane | None, position: float
    ) -> int | None:
        """Resolve preferred respawn module and apply one-step loop avoidance.

        If the module where the vehicle fell is a LOOPING module, step back one
        module to avoid respawning in the same looping section.
        """
        if lane is None or not self.__track_modules:
            return None

        module_index, _ = self.__get_track_module_index_and_local_position(
            lane, position
        )
        if module_index is None:
            return None

        module = self.__track_modules[module_index]

        # Apply loop avoidance: if the current module is a looping module,
        # respawn one module earlier.
        if module.track_type == TrackType.LOOPING and len(self.__track_modules) > 1:
            module_index = (module_index - 1) % len(self.__track_modules)

        return module_index

    def __is_lane_available_for_respawn(self, lane: Lane, module_index: int) -> bool:
        """Return whether lane is free of active vehicles in a given module index."""
        for player in self.__players:
            vehicle = player.vehicle
            if not vehicle.active or vehicle.lane != lane:
                continue

            active_module_index, _ = self.__get_track_module_index_and_local_position(
                lane,
                vehicle.position,
            )
            if active_module_index == module_index:
                return False

        return True

    def __count_active_vehicles_in_module(self, module_index: int) -> int:
        """Count active vehicles that currently resolve to one module index."""
        count = 0
        for player in self.__players:
            vehicle = player.vehicle
            if not vehicle.active or vehicle.lane is None:
                continue

            active_module_index, _ = self.__get_track_module_index_and_local_position(
                vehicle.lane,
                vehicle.position,
            )
            if active_module_index == module_index:
                count += 1

        return count

    def __candidate_respawn_lanes(
        self, module_index: int, preferred_lane: Lane | None
    ) -> list[Lane]:
        """Return lane order for respawn: preferred lane first, then remaining lanes."""
        module = self.__track_modules[module_index]
        lanes_with_line = [
            lane for lane in self.__lanes if module.get_line_for_lane(lane) is not None
        ]
        if preferred_lane is None or preferred_lane not in lanes_with_line:
            return lanes_with_line

        return [preferred_lane] + [
            lane for lane in lanes_with_line if lane != preferred_lane
        ]

    def __spawn_player_on_module_lane(
        self, player: Player, module_index: int, lane: Lane
    ) -> bool:
        """Spawn one player at module start on the selected lane."""
        if not self.__is_lane_available_for_respawn(lane, module_index):
            return False

        vehicle = player.vehicle
        spawn_position = self.__build_global_lane_position(lane, module_index, 0.0)
        vehicle.set_lane(lane)
        vehicle.set_position(spawn_position)
        vehicle.set_speed(0)
        vehicle.set_acceleration(
            0, self.__settings.min_acceleration, self.__settings.max_acceleration
        )
        vehicle.set_respawn_ticks(0)
        vehicle.set_active(True)
        vehicle.clear_lane_change()
        vehicle.set_respawn_module_index(None)
        self.__record_event(
            {
                "event": "player_respawned",
                "player": player.name,
                "lane": lane.lane_id,
                "module_index": module_index,
                "position": vehicle.position,
            }
        )
        return True

    def __try_respawn_player(self, player: Player) -> bool:
        """Try to respawn one player using module-aware spawn rules.

        Returns:
            bool: ``True`` when respawn succeeded.
        """
        if not self.__track_modules:
            return False

        vehicle = player.vehicle
        preferred_module_index = vehicle.respawn_module_index
        if preferred_module_index is None:
            preferred_module_index = self.__resolve_respawn_module_index(
                vehicle.lane,
                vehicle.position,
            )
        if preferred_module_index is None:
            preferred_module_index = 0

        preferred_module_index %= len(self.__track_modules)

        for lane in self.__candidate_respawn_lanes(
            preferred_module_index, vehicle.lane
        ):
            if self.__spawn_player_on_module_lane(player, preferred_module_index, lane):
                return True

        fallback_candidates: list[tuple[int, int]] = []
        for module_index, module in enumerate(self.__track_modules):
            has_free_lane = False
            for lane in self.__candidate_respawn_lanes(module_index, vehicle.lane):
                if self.__is_lane_available_for_respawn(lane, module_index):
                    has_free_lane = True
                    break

            if has_free_lane:
                active_count = self.__count_active_vehicles_in_module(module_index)
                fallback_candidates.append((active_count, module_index))

        for _, module_index in sorted(
            fallback_candidates, key=lambda item: (item[0], item[1])
        ):
            for lane in self.__candidate_respawn_lanes(module_index, vehicle.lane):
                if self.__spawn_player_on_module_lane(player, module_index, lane):
                    return True

        return False

    def __handle_inactive_player_tick(self, player: Player) -> None:
        """Tick one inactive player and attempt respawn when ready."""
        vehicle = player.vehicle
        if vehicle.respawn_ticks > 0:
            vehicle.reduce_respawn_ticks(1)

        if vehicle.respawn_ticks == 0 and not self.__try_respawn_player(player):
            # Keep retrying every tick while no lane is safely available.
            vehicle.set_active(False)
            self.__record_event(
                {
                    "event": "respawn_retry_blocked",
                    "player": player.name,
                }
            )

    def __detect_and_apply_collisions(self):
        """Detect same-lane rear-end collisions and mark front vehicles as fallen.

        For each lane, players are ordered by position and only neighboring vehicles
        can collide in one direction. If the forward gap is below or equal to the
        configured crash distance, the vehicle in front falls.
        """
        players_to_fall: dict[Player, str] = {}
        crash_distance = self.__settings.vehicle_crash_distance

        for lane in self.__lanes:
            lane_players = [
                player
                for player in self.__players
                if player.vehicle.active and player.vehicle.lane == lane
            ]
            if len(lane_players) < 2:
                continue

            lane_length = self.get_lane_track_length(lane)
            if lane_length <= 0:
                continue

            lane_players.sort(key=lambda player: player.vehicle.position)
            for index, rear_player in enumerate(lane_players):
                front_player = lane_players[(index + 1) % len(lane_players)]
                forward_gap = (
                    front_player.vehicle.position - rear_player.vehicle.position
                ) % lane_length
                if 0 < forward_gap <= crash_distance:
                    players_to_fall[front_player] = (
                        f"collision with {rear_player.name} at position {rear_player.vehicle.position:.2f}"
                    )

        for player, reason in players_to_fall.items():
            self.__fall_player(player, reason)

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

    @property
    def recent_events(self) -> list[dict[str, Any]]:
        """Return in-memory structured event history for local simulations."""
        return list(self.__event_history)

    @property
    def round_counters(self) -> dict[Player, RoundCounter]:
        return self.__round_counters