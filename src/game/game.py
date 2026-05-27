import threading
import time
from collections.abc import Callable
from typing import Any, TypedDict

from src.controller.signal_receiver_interface import SignalReceiverInterface
from .lane import Lane
from .player import Player
from .settings import Settings
from .track_module import TrackModule, TrackType
from src.logger.multi_logger import get_logger

logger = get_logger()


class LaneChangeState(TypedDict):
    """Internal state for a multi-hop lane-change operation.

    Attributes:
        lane_sequence (list[Lane]): Ordered path including source and final target lane.
        sequence_index (int): Index of the currently active source lane in the sequence.
    """
    lane_sequence: list[Lane]
    sequence_index: int
    
class Game:    
    """Core simulation loop for player movement, lane changes, collisions, and respawns.

    The game is tick-based. Each tick updates active players in a deterministic order,
    then resolves collisions. Inactive players remain in respawn state and are retried
    according to the rules from the project README.
    """

    def __init__(self,
        players: list[Player],
        settings: Settings,
        track_modules: list[TrackModule],
        signal_receiver: SignalReceiverInterface,
        lanes: list[Lane],
        display_manager # explicitly not imported to avoid circular dependency
        ):
        
        self.__players = players if players else []
        self.__settings = settings
        self.__track_modules = track_modules if track_modules else []
        self.__length = sum([tm.length for tm in track_modules]) if track_modules else 0
        self.__signal_receiver = signal_receiver
        self.__lanes = lanes if lanes else []
        self.__display_manager = display_manager
        self.__lane_change_states: dict[Player, LaneChangeState] = {}
        self.__event_history: list[dict[str, Any]] = []
        self.__event_history_limit = 200
        self.__tick_count = 0
        
        self.__stop_event = threading.Event()
        self.__threads: list[threading.Thread] = []
        self.__game_tick_interval_s = 0.02
        
        self.__record_event({
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
        self.__record_event({
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
            # sound logic
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

    def __record_event(self, payload: dict[str, Any]) -> None:
        """Store and emit one structured game event."""
        event = {"tick": self.__tick_count, **payload}
        self.__event_history.append(event)
        if len(self.__event_history) > self.__event_history_limit:
            self.__event_history = self.__event_history[-self.__event_history_limit:]
        logger.log_json(event)

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

        if show_display:
            self.display()

    def display(self):
        self.log_fully()
        if self.__display_manager is not None:
            self.__display_manager.update(self)

    # Helpers
    def __get_lane_track_length(self, lane: Lane) -> float:
        """Return total drivable length for one lane across all configured modules.

        Args:
            lane (Lane): Lane whose complete track length should be accumulated.

        Returns:
            float: Sum of all line lengths that belong to the given lane.
        """
        return sum([tm.get_line_length_for_lane(lane) for tm in self.__track_modules])

    def __get_track_module_index_and_local_position(self, lane: Lane, position: float) -> tuple[int | None, float]:
        """Resolve one lane position to a concrete module index and lane-local position.

        Args:
            lane (Lane): Lane in which the position is interpreted.
            position (float): Global lane position value.

        Returns:
            tuple[int | None, float]:
                The matched module index and local position in that module.
                Returns ``(None, 0.0)`` if no lane segment can be resolved.
        """
        lane_length = self.__get_lane_track_length(lane)
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

    def __build_global_lane_position(self, lane: Lane, module_index: int, module_local_position: float) -> float:
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

    def get_track_module_for_lane_position(self, lane: Lane, position: float) -> tuple[TrackModule | None, float]:
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
        module_index, local_position = self.__get_track_module_index_and_local_position(lane, position)
        if module_index is None:
            return None, local_position
        return self.__track_modules[module_index], local_position

    def __fall_player(self, player: Player, reason: str) -> None:
        """Move one player into respawn state and clear pending lane-change state."""
        self.__lane_change_states.pop(player, None)
        self.__record_event({
            "event": "player_fell",
            "player": player.name,
            "reason": reason,
            "lane": player.vehicle.lane.lane_id if player.vehicle.lane is not None else None,
            "position": player.vehicle.position,
            "speed": player.vehicle.speed,
            "acceleration": player.vehicle.acceleration,
            "respawn_ticks": self.__settings.respawn_ticks,
        })
        player.vehicle.trigger_respawn(self.__settings.respawn_ticks)

    def __would_move_into_lane_gap(self, player: Player, delta_position: float) -> bool:
        """Check whether the requested movement crosses a module boundary without lane continuation.

        A lane gap exists if the next module in movement direction has no line for the
        player's current lane.

        Args:
            player (Player): Player to check.
            delta_position (float): Planned movement distance for this tick.

        Returns:
            bool: ``True`` if the movement would enter a lane gap.
        """
        return self.__lane_gap_reason(player, delta_position) is not None

    def __lane_gap_reason(self, player: Player, delta_position: float) -> str | None:
        """Return a short reason when movement enters a lane gap."""
        if delta_position == 0:
            return None

        lane = player.vehicle.lane
        if lane is None:
            return "lane is ended: vehicle has no lane"
        if not self.__track_modules:
            return "lane is ended: no track modules configured"

        module_index, module_position = self.__get_track_module_index_and_local_position(lane, player.vehicle.position)
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
                if self.__track_modules[module_index].get_line_length_for_lane(lane) <= 0:
                    return f"lane is ended: missing next lane segment in module {module_index}"
                module_position = 0.0
                continue

            distance_to_start = max(module_position, 0.0)
            if -remaining <= distance_to_start:
                return None

            remaining += distance_to_start
            module_index = (module_index - 1) % track_module_count
            previous_line_length = self.__track_modules[module_index].get_line_length_for_lane(lane)
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

    def __get_lane_sequence_between(self, source_lane: Lane, target_lane: Lane) -> list[Lane]:
        """Return ordered adjacent lane path from source to target.

        Args:
            source_lane (Lane): Lane where the vehicle currently is.
            target_lane (Lane): Requested final lane.

        Returns:
            list[Lane]: Inclusive ordered sequence of adjacent lanes.
        """
        source_index = self.__lanes.index(source_lane)
        target_index = self.__lanes.index(target_lane)
        if source_index <= target_index:
            return self.__lanes[source_index:target_index + 1]
        return list(reversed(self.__lanes[target_index:source_index + 1]))

    def __is_lane_change_allowed(self, player: Player) -> bool:
        """Check whether lane change is currently allowed on the active line."""
        lane = player.vehicle.lane
        if lane is None:
            return False

        module, _ = self.get_track_module_for_lane_position(lane, player.vehicle.position)
        if module is None:
            return False

        line = module.get_line_for_lane(lane)
        return bool(line and line.driving_profile.lane_change_allowed)

    def __start_lane_change_if_requested(self, player: Player) -> None:
        """Initialize a multi-hop lane change based on controller input.

        The current control model supports one button for switching between leftmost
        and rightmost lane. Middle-lane origins are ignored unless they are part of
        an already active lane-change sequence.
        """
        if player in self.__lane_change_states:
            return

        vehicle = player.vehicle
        if vehicle.lane is None:
            return
        if vehicle.line_change_ticks != 0 or vehicle.line_change_target is not None:
            return
        if player.controller.special_1 < self.__settings.special_1_threshold:
            return
        if not self.__is_lane_change_allowed(player):
            return

        target_lane: Lane | None = None
        if vehicle.lane == self.__lanes[0]:
            target_lane = self.__lanes[-1]
        elif vehicle.lane == self.__lanes[-1]:
            target_lane = self.__lanes[0]
        else:
            # In 3+ lane configurations (for example intersections), allow middle
            # lanes to initiate a lane change as well. We choose the nearest edge,
            # and in a tie we move right to keep behavior deterministic.
            source_index = self.__lanes.index(vehicle.lane)
            left_distance = source_index
            right_distance = (len(self.__lanes) - 1) - source_index
            target_lane = self.__lanes[-1] if right_distance <= left_distance else self.__lanes[0]

        if target_lane is None or target_lane == vehicle.lane:
            return

        lane_sequence = self.__get_lane_sequence_between(vehicle.lane, target_lane)
        if len(lane_sequence) <= 1:
            return

        self.__lane_change_states[player] = {
            "lane_sequence": lane_sequence,
            "sequence_index": 0,
        }
        self.__record_event({
            "event": "lane_change_started",
            "player": player.name,
            "source_lane": vehicle.lane.lane_id,
            "target_lane": target_lane.lane_id,
            "lane_sequence": [lane.lane_id for lane in lane_sequence],
            "lane_change_ticks": self.__settings.lane_change_ticks,
        })
        vehicle.trigger_line_change(
            target_lane=lane_sequence[1],
            line_change_ticks=self.__settings.lane_change_ticks,
        )

    def __advance_lane_change(self, player: Player) -> None:
        """Advance one lane-change state machine by one tick.

        Once one hop timer expires, the vehicle is moved to the next adjacent lane and
        position is converted proportionally inside the current track module.
        """
        state = self.__lane_change_states.get(player)
        if state is None:
            return

        vehicle = player.vehicle
        if vehicle.line_change_ticks > 0:
            vehicle.reduce_line_change_ticks(1)
        if vehicle.line_change_ticks > 0:
            return

        source_lane = state["lane_sequence"][state["sequence_index"]]
        target_lane = state["lane_sequence"][state["sequence_index"] + 1]

        module_index, source_module_position = self.__get_track_module_index_and_local_position(
            source_lane,
            vehicle.position,
        )
        if module_index is None:
            self.__fall_player(player, "lane change failed: source lane position not resolvable")
            return

        track_module = self.__track_modules[module_index]
        if track_module.get_line_for_lane(target_lane) is None:
            self.__fall_player(
                player,
                f"lane change failed: target lane L{target_lane.lane_id} missing in module {module_index}",
            )
            return

        target_module_position = track_module.convert_position_between_lanes(
            source_lane,
            target_lane,
            source_module_position,
        )
        target_global_position = self.__build_global_lane_position(
            target_lane,
            module_index,
            target_module_position,
        )

        vehicle.set_lane(target_lane)
        vehicle.set_position(target_global_position)
        self.__record_event({
            "event": "lane_change_hop_completed",
            "player": player.name,
            "from_lane": source_lane.lane_id,
            "to_lane": target_lane.lane_id,
            "module_index": module_index,
            "position": vehicle.position,
        })

        state["sequence_index"] += 1
        if state["sequence_index"] >= len(state["lane_sequence"]) - 1:
            self.__lane_change_states.pop(player, None)
            self.__record_event({
                "event": "lane_change_finished",
                "player": player.name,
                "final_lane": target_lane.lane_id,
                "position": vehicle.position,
            })
            return

        next_target = state["lane_sequence"][state["sequence_index"] + 1]
        vehicle.trigger_line_change(
            target_lane=next_target,
            line_change_ticks=self.__settings.lane_change_ticks,
        )

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

    def __try_respawn_player(self, player: Player) -> bool:
        """Try to respawn one player at position 0 on the first module.

        Returns:
            bool: ``True`` when respawn succeeded.
        """
        if not self.__track_modules:
            return False

        first_module_index = 0
        first_module = self.__track_modules[first_module_index]
        for lane in self.__lanes:
            if first_module.get_line_for_lane(lane) is None:
                continue
            if not self.__is_lane_available_for_respawn(lane, first_module_index):
                continue

            player.vehicle.set_lane(lane)
            player.vehicle.set_position(0)
            player.vehicle.set_speed(0)
            player.vehicle.set_acceleration(0)
            player.vehicle.set_respawn_ticks(0)
            player.vehicle.set_active(True)
            self.__record_event({
                "event": "player_respawned",
                "player": player.name,
                "lane": lane.lane_id,
                "position": player.vehicle.position,
            })
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
            self.__record_event({
                "event": "respawn_retry_blocked",
                "player": player.name,
            })

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
        if player.vehicle.lane is None:
            return True

        track_module, _ = self.get_track_module_for_lane_position(
            player.vehicle.lane,
            player.vehicle.position,
        )
        if track_module is None:
            return True

        current_line = track_module.get_line_for_lane(player.vehicle.lane)
        if current_line is None:
            return True

        return self.__get_profile_violation_reason(player, current_line.driving_profile) is not None

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

            lane_length = self.__get_lane_track_length(lane)
            if lane_length <= 0:
                continue

            lane_players.sort(key=lambda player: player.vehicle.position)
            for index, rear_player in enumerate(lane_players):
                front_player = lane_players[(index + 1) % len(lane_players)]
                forward_gap = (front_player.vehicle.position - rear_player.vehicle.position) % lane_length
                if 0 < forward_gap <= crash_distance:
                    players_to_fall[front_player] = (
                        f"collision with {rear_player.name} at position {rear_player.vehicle.position:.2f}"
                    )

        for player, reason in players_to_fall.items():
            if player.vehicle.active:
                self.__fall_player(player, reason)

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
                self.__handle_inactive_player_tick(player)
                continue

            vehicle.set_acceleration(player.controller.forward_press)
            vehicle.apply_friction(self.__settings.friction_percent)
            vehicle.update_speed(
                self.__settings.max_speed,
                acceleration_multiplier=self.__settings.acceleration_multiplier,
            )

            self.__start_lane_change_if_requested(player)

            track_module, _ = self.get_track_module_for_lane_position(
                vehicle.lane,
                vehicle.position,
            ) if vehicle.lane is not None else (None, 0.0)
            if track_module is None or vehicle.lane is None:
                self.__fall_player(player, "lane is ended: active lane/module not resolvable")
                continue

            current_line = track_module.get_line_for_lane(vehicle.lane)
            if current_line is None:
                self.__fall_player(player, "lane is ended: missing line for active lane")
                continue

            profile_reason = self.__get_profile_violation_reason(player, current_line.driving_profile)
            if profile_reason is not None:
                self.__fall_player(player, profile_reason)
                continue

            delta_position = vehicle.speed * self.__game_tick_interval_s
            lane_gap_reason = self.__lane_gap_reason(player, delta_position)
            if lane_gap_reason is not None:
                self.__fall_player(player, lane_gap_reason)
                continue

            if vehicle.lane is None:
                self.__fall_player(player, "lane is ended: vehicle lane is None after movement")
                continue

            lane_track_length = self.__get_lane_track_length(vehicle.lane)
            vehicle.update_position(delta_position, lane_track_length)

            self.__advance_lane_change(player)
            if not vehicle.active:
                continue

            track_module_after, _ = self.get_track_module_for_lane_position(
                vehicle.lane,
                vehicle.position,
            ) if vehicle.lane is not None else (None, 0.0)
            if track_module_after is None or vehicle.lane is None:
                self.__fall_player(player, "lane is ended: active lane/module not resolvable after movement")
                continue

            current_line_after = track_module_after.get_line_for_lane(vehicle.lane)
            if current_line_after is None:
                self.__fall_player(player, "lane is ended: missing line for active lane after movement")
                continue

            profile_reason_after = self.__get_profile_violation_reason(player, current_line_after.driving_profile)
            if profile_reason_after is not None:
                self.__fall_player(player, profile_reason_after)

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
                    "lane": player.vehicle.lane.lane_id if player.vehicle.lane is not None else None,
                    "speed": player.vehicle.speed,
                    "acceleration": player.vehicle.acceleration,
                    "round": player.vehicle.round,
                    "primary_color": player.vehicle.primary_color,
                    "decelerate_color": player.vehicle.decelerate_color,
                    "accelerate_color": player.vehicle.accelerate_color
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
                "respawn_ticks": self.settings.respawn_ticks,
                "friction_percent": self.settings.friction_percent,
                "acceleration_multiplier": self.settings.acceleration_multiplier,
                "special_1_threshold": self.settings.special_1_threshold,
                "lane_change_ticks": self.settings.lane_change_ticks,
                "vehicle_crash_distance": self.settings.vehicle_crash_distance,
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

    @property
    def recent_events(self) -> list[dict[str, Any]]:
        """Return in-memory structured event history for local simulations."""
        return list(self.__event_history)