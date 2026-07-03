from src.game.game import Game
from src.game.track_module import TrackType
from src.game.vehicle import Vehicle
from src.game.driving_profile import DrivingProfile
from src.display.led_display import LedDisplay
from src.display.config import DisplayConfig
from src.display.color_constants import *


def interpolate_color(
    color1: tuple[int, int, int], color2: tuple[int, int, int], ratio: float
) -> tuple[int, int, int]:
    """
    Interpolate between two RGB colors based on a ratio.

    This function calculates a new color that is a mix of color1 and color2
    according to the given ratio. A ratio of 0.0 results in color1, a ratio of
    1.0 results in color2, and values in between result in a blended color.

    Args:
        color1 (tuple[int, int, int]): The starting RGB color.
        color2 (tuple[int, int, int]): The ending RGB color.
        ratio (float): The interpolation ratio between 0.0 and 1.0.

    Returns:
        tuple[int, int, int]: The interpolated RGB color.
    """
    ratio = max(0.0, min(1.0, ratio))
    r = int(color1[0] + (color2[0] - color1[0]) * ratio)
    g = int(color1[1] + (color2[1] - color1[1]) * ratio)
    b = int(color1[2] + (color2[2] - color1[2]) * ratio)
    return (r, g, b)


class DisplayManager:
    """
    Logic component to translate game state into visual components using the hierarchy.

    This class manages the rendering logic for the LED display, taking the current
    game state and deciding which visual elements to display based on a defined
    hierarchy (e.g., track start, intersections, vehicles).

    Attributes:
        display (Display): The display instance used to render the game state.
        config (DisplayConfig | None): Configuration settings for the display manager.
    """

    # Color constants assigned to class attributes for easy access and future customization.
    COLOR_RENDER_INTERSECTION = LIGHT_PINK
    COLOR_RENDER_TRACK_BASE = DARK_PURPLE
    COLOR_RENDER_TRACK_MODULE_START = DARK_PURPLE
    COLOR_RENDER_START_OF_TRACK = GRAY
    COLOR_RENDER_ROUND_ADVANCE_PRIMARY = YELLOW
    COLOR_RENDER_ROUND_ADVANCE_SECONDARY = WHITE
    COLOR_RENDER_INACTIVE_MODIFIER = GRAY
    COLOR_RENDER_FRONT_LIGHT = LIGHT_GRAY
    COLOR_RENDER_REAR_LIGHT = RED

    def __init__(self, display: LedDisplay, config: DisplayConfig | None = None):
        """
        Initialize the DisplayManager.

        Args:
            display (Display): The display instance for rendering.
            config (DisplayConfig | None): Configuration settings.
        """
        self.display = display
        self.config = config if config else DisplayConfig()
        # Track round ticks for vehicles
        # Dict[id(player), {"round": int, "ticks_left": int}]
        self.__vehicle_rounds = {}

    def update(self, game: Game):
        """
        Update the display based on the current game state.

        This method clears the display and then renders the various visual
        components in a specific hierarchical order, finally pushing the
        updates to the physical LEDs.

        Args:
            game (Game): The current game state object.

        Returns:
            None
        """
        # NOTE: The display update logic follows a strict rendering hierarchy.
        # Lower-priority layers are applied first so that higher-priority
        # rendering actions can override them by writing into the same virtual
        # buffer positions. The order implemented here (applied in update()):
        #  - intersection module (base color for intersection segments)
        #  - intersection animation (when a vehicle is currently on an intersection)
        #  - start of track marker (first pixel of each lane)
        #  - round advance animation (blinks lane on round increment)
        #  - inactive vehicles (respawn blinking marker)
        #  - active vehicles (final override for vehicle position / speed color)
        #  - vehicle front lights (white/gray highlight when accelerating)
        #  - vehicle rear lights (red highlight when braking)

        self.display.clear()

        self._update_round_ticks(game)
        # Render the low-priority base track module visuals first so higher
        # priority layers (intersections, vehicles, etc.) can override them.
        self._render_track_modules(game)
        self._render_intersection_modules(game)
        self._render_intersection_animations(game)
        self._render_start_of_track(game)
        self._render_round_advance(game)
        self._render_inactive_vehicles(game)
        self._render_active_vehicles(game)
        
        if game.settings.directional_vehicle_lights:
            self._render_vehicle_front_lights(game)
            self._render_vehicle_rear_lights(game)

        self.display.render()

    def _get_vehicle_pixel_count(self, game: Game) -> int:
        """Derive the vehicle sprite width from the crash-distance setting."""
        pixel_count = int(round(game.settings.vehicle_crash_distance))
        if pixel_count < 1:
            pixel_count = 1
        if pixel_count % 2 == 0:
            pixel_count += 1
        return pixel_count

    def _render_vehicle_pixel_window(
        self,
        game: Game,
        lane,
        position: float,
        color: tuple[int, int, int],
        pixel_count: int,
    ):
        lane_total = game.get_lane_track_length(lane)
        if lane_total <= 0:
            return

        relative_position = position / lane_total
        self.display.set_lane_pixel_window_by_relative_position(
            lane,
            relative_position,
            color,
            pixel_count=pixel_count,
        )

    def _update_round_ticks(self, game: Game):
        """
        Track and decrement per-player round-advance tick timers.

        This method inspects all players and records when a player's
        `vehicle.round` increases. When a round advance is detected a
        per-player counter is seeded from the configuration and decremented
        on each update call. The counters are used by the round advance
        renderer.

        Args:
            game (Game): Current game instance providing player list.
        """
        players = game.players

        for player in players:
            player_id = id(player)
            vehicle = player.vehicle
            if vehicle:
                if player_id not in self.__vehicle_rounds:
                    self.__vehicle_rounds[player_id] = {
                        "round": vehicle.round,
                        "ticks_left": 0,
                    }

                state = self.__vehicle_rounds[player_id]

                # Check if round advanced
                if vehicle.round > state["round"]:
                    state["ticks_left"] = self.config.round_advance_ticks
                    state["round"] = vehicle.round

                # Decrement ticks
                if state["ticks_left"] > 0:
                    state["ticks_left"] -= 1

    def _render_intersection_modules(self, game: Game):
        """
        Paint base color for track modules that are intersections.

        This paints a LIGHT_GRAY base colour for the region of each lane
        that belongs to a module with type `TrackType.INTERSECTION`. The
        physical-to-virtual mapping is calculated using lane-relative
        ratios derived from module line lengths.

        Args:
            game (Game): Current game instance exposing lanes and modules.
        """
        lanes = game.lanes
        track_modules = game.track_modules
        lane_lengths = {lane: 0.0 for lane in lanes}

        for module in track_modules:
            for lane in lanes:
                line = module.get_line_for_lane(lane)
                lane_change_allowed = bool(
                    line and line.driving_profile.lane_change_allowed
                )
                line_length = module.get_line_length_for_lane(lane)
                start_pos = lane_lengths[lane]
                end_pos = start_pos + line_length

                if lane_change_allowed and line_length > 0:
                    # lane_total = game.get_track_length_for_lane(lane)
                    lane_total = game.get_lane_track_length(lane)
                    if lane_total > 0:
                        start_relative_position = start_pos / lane_total
                        end_relative_position = end_pos / lane_total
                        self.display.fill_lane_section_by_relative_position(
                            lane,
                            start_relative_position,
                            end_relative_position,
                            self.COLOR_RENDER_INTERSECTION,
                            color_ratio=0.1,
                        )

                lane_lengths[lane] = end_pos

    def _render_track_modules(self, game: Game):
        """
        Paint a subtle base color across the whole track and emphasize the
        first pixel of each track module.

        - By default the entire lane is painted DARK_GRAY at a low ratio
          (`color_ratio=0.05`).
        - Additionally each module's first pixel is painted with DARK_GRAY at
          a higher ratio (`color_ratio=0.1`) to make module boundaries visible.
        """
        lanes = game.lanes
        track_modules = game.track_modules

        # Fill entire lanes with a faint dark gray base.
        for lane in lanes:
            self.display.fill_lane(lane, self.COLOR_RENDER_TRACK_BASE, color_ratio=0.1)

        # Highlight the first pixel of each module to improve visibility.
        lane_start_positions = {lane: 0.0 for lane in lanes}
        for module in track_modules:
            for lane in lanes:
                line_length = module.get_line_length_for_lane(lane)
                if line_length <= 0:
                    # Advance start position regardless so later modules are placed correctly.
                    lane_start_positions[lane] += line_length
                    continue

                lane_total = game.get_lane_track_length(lane)
                if lane_total <= 0:
                    lane_start_positions[lane] += line_length
                    continue

                start_pos = lane_start_positions[lane]
                # Paint the module's leading pixel slightly brighter than the base.
                self.display.set_lane_pixel_by_relative_position(
                    lane,
                    start_pos / lane_total,
                    self.COLOR_RENDER_TRACK_MODULE_START,
                    color_ratio=0.3,
                )

                lane_start_positions[lane] += line_length

    def _render_intersection_animations(self, game: Game):
        """
        Overlay animation for vehicles currently on an intersection.

        If a vehicle is resolved to a module with type `INTERSECTION`, the
        entire lane segment for that module is painted `LIGHT_PINK`. This runs
        before active vehicle rendering so single-pixel vehicle markers can
        still override the animation when applicable.

        Args:
            game (Game): Current game instance exposing players.
        """
        players = game.players

        # Use a set to track which modules we have already rendered animations for
        # in this tick to avoid redundant fills if multiple players are in the same module.
        rendered_modules: set[int] = set()

        for player in players:
            vehicle = player.vehicle
            if vehicle and vehicle.lane:
                module, _ = game.get_track_module_for_lane_position(
                    vehicle.lane, vehicle.position
                )
                if not module or id(module) in rendered_modules:
                    continue

                line = module.get_line_for_lane(vehicle.lane)
                lane_change_allowed = bool(
                    line and line.driving_profile.lane_change_allowed
                )

                if lane_change_allowed:
                    lane = vehicle.lane
                    lane_total = game.get_lane_track_length(lane)
                    if lane_total <= 0:
                        continue

                    # Find the global start position of this module for the current lane.
                    module_start_position = 0.0
                    for track_module in game.track_modules:
                        line_length = track_module.get_line_length_for_lane(lane)

                        if track_module is module:
                            if line_length > 0:
                                self.display.fill_lane_section_by_relative_position(
                                    lane,
                                    module_start_position / lane_total,
                                    (module_start_position + line_length) / lane_total,
                                    self.COLOR_RENDER_INTERSECTION,
                                    color_ratio=0.2,
                                )
                                rendered_modules.add(id(module))
                            break

                        module_start_position += line_length

    def _render_start_of_track(self, game: Game):
        """
        Mark the start position of every lane.

        The first pixel of every lane is marked `GRAY` to indicate the
        start / end line of the track. This is intentionally a low-level
        visual and therefore applied early so higher-priority effects may
        override it.

        Args:
            game (Game): Current game instance exposing lane list.
        """
        if not game.track_modules:
            return

        lanes = game.lanes
        first_module = game.track_modules[0]

        for lane in lanes:
            if first_module.get_line_for_lane(lane) is not None:
                self.display.set_lane_pixel_by_relative_position(
                    lane, 0.0, self.COLOR_RENDER_START_OF_TRACK
                )

    def _render_round_advance(self, game: Game):
        players = game.players

        for player in players:
            vehicle = player.vehicle

            if vehicle.lane is not None:
                player_id = id(player)
                if (
                    vehicle
                    and player_id in self.__vehicle_rounds
                    and self.__vehicle_rounds[player_id]["ticks_left"] > 0
                ):
                    ticks_left = self.__vehicle_rounds[player_id]["ticks_left"]
                    change_interval = self.config.round_advance_tick_color_change
                    if (ticks_left // change_interval) % 2 == 0:
                        color = self.COLOR_RENDER_ROUND_ADVANCE_PRIMARY
                    else:
                        color = self.COLOR_RENDER_ROUND_ADVANCE_SECONDARY

                    # Only pulse the start pixel so the lap-change indicator stays subtle.
                    self.display.set_lane_pixel_by_relative_position(
                        vehicle.lane, 0.0, color
                    )

    def _render_inactive_vehicles(self, game: Game):
        players = game.players
        vehicle_pixel_count = self._get_vehicle_pixel_count(game)

        for player in players:
            vehicle = player.vehicle
            if (
                vehicle
                and vehicle.lane
                and (not vehicle.active or vehicle.respawn_ticks > 0)
            ):
                # Inactive vehicles keep a stable muted color: 40% primary + 60% gray.
                color = interpolate_color(
                    vehicle.primary_color,
                    self.COLOR_RENDER_INACTIVE_MODIFIER,
                    0.6,
                )
                self._render_vehicle_pixel_window(
                    game,
                    vehicle.lane,
                    vehicle.position,
                    color,
                    vehicle_pixel_count,
                )

    def _render_active_vehicles(self, game: Game):
        players = game.players
        vehicle_pixel_count = self._get_vehicle_pixel_count(game)

        for player in players:
            vehicle = player.vehicle
            if (
                vehicle
                and vehicle.lane
                and vehicle.active
                and vehicle.respawn_ticks <= 0
            ):
                module, _ = game.get_track_module_for_lane_position(
                    vehicle.lane, vehicle.position
                )
                if module:
                    line = module.get_line_for_lane(vehicle.lane)
                    if line:
                        dp = line.driving_profile
                        color = self._get_active_color(vehicle, dp)
                        self._render_vehicle_pixel_window(
                            game,
                            vehicle.lane,
                            vehicle.position,
                            color,
                            vehicle_pixel_count,
                        )

    def _render_vehicle_front_lights(self, game: Game):
        """
        Overlay front lighting for vehicles that are currently accelerating.

        If `vehicle.acceleration > 0`, the leading pixel of the vehicle sprite
        is overwritten with `COLOR_RENDER_FRONT_LIGHT`.
        """
        players = game.players
        vehicle_pixel_count = self._get_vehicle_pixel_count(game)
        offset = vehicle_pixel_count // 2

        for player in players:
            vehicle = player.vehicle
            if (
                vehicle
                and vehicle.lane
                and vehicle.active
                and vehicle.respawn_ticks <= 0
                and vehicle.acceleration > 0
            ):
                lane_total = game.get_lane_track_length(vehicle.lane)
                if lane_total <= 0:
                    continue

                arr = self.display.virtual_arrays.get(vehicle.lane.lane_id)
                if arr is not None and len(arr) > 0:
                    center_idx = int((vehicle.position / lane_total) * (len(arr) - 1))
                    front_idx = (center_idx + offset) % len(arr)
                    arr[front_idx] = self.COLOR_RENDER_FRONT_LIGHT

    def _render_vehicle_rear_lights(self, game: Game):
        """
        Overlay rear brake lighting for vehicles that are currently decelerating.

        If `vehicle.acceleration < 0`, the trailing pixel of the vehicle sprite
        is overwritten with `COLOR_RENDER_REAR_LIGHT`.
        """
        players = game.players
        vehicle_pixel_count = self._get_vehicle_pixel_count(game)
        offset = vehicle_pixel_count // 2

        for player in players:
            vehicle = player.vehicle
            if (
                vehicle
                and vehicle.lane
                and vehicle.active
                and vehicle.respawn_ticks <= 0
                and vehicle.acceleration <= 0
            ):
                lane_total = game.get_lane_track_length(vehicle.lane)
                if lane_total <= 0:
                    continue

                arr = self.display.virtual_arrays.get(vehicle.lane.lane_id)
                if arr is not None and len(arr) > 0:
                    center_idx = int((vehicle.position / lane_total) * (len(arr) - 1))
                    rear_idx = (center_idx - offset) % len(arr)
                    arr[rear_idx] = self.COLOR_RENDER_REAR_LIGHT

    def _get_active_color(
        self, vehicle: Vehicle, dp: DrivingProfile
    ) -> tuple[int, int, int]:
        """
        Calculate the appropriate color for an active vehicle based on its speed relative to the driving profile limits.

        Args:
            vehicle (Vehicle): The active vehicle instance.
            dp (DrivingProfile): The driving profile of the current line segment.

        Returns:
            tuple[int, int, int]: The RGB color to display for the active vehicle.
        """
        speed = vehicle.speed
        half_max = dp.max_speed / 2.0
        half_min = abs(dp.min_speed) / 2.0

        if speed > half_max:
            ratio = (
                (speed - half_max) / (dp.max_speed - half_max)
                if dp.max_speed != half_max
                else 1.0
            )
            return interpolate_color(
                vehicle.primary_color, vehicle.decelerate_color, ratio
            )
        elif speed < -half_min:
            ratio = (
                (abs(speed) - half_min) / (abs(dp.min_speed) - half_min)
                if abs(dp.min_speed) != half_min
                else 1.0
            )
            return interpolate_color(
                vehicle.primary_color, vehicle.accelerate_color, ratio
            )
        else:
            return vehicle.primary_color
