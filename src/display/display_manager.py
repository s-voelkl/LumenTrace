from src.game.game import Game
from src.game.track_module import TrackType
from src.game.vehicle import Vehicle
from src.game.driving_profile import DrivingProfile
from src.display.display import Display
from src.display.config import DisplayConfig
from src.display.color_constants import *

def interpolate_color(color1: tuple[int,int,int], color2: tuple[int,int,int], ratio: float) -> tuple[int,int,int]:
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
    
    def __init__(self, display: Display, config: DisplayConfig | None = None):
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
        self.display.clear()
        
        self._update_round_ticks(game)
        self._render_intersection_modules(game)
        self._render_intersection_animations(game)
        self._render_start_of_track(game)
        self._render_round_advance(game)
        self._render_inactive_vehicles(game)
        self._render_active_vehicles(game)

        self.display.render()

    def _update_round_ticks(self, game: Game):
        players = game.players
            
        for player in players:
            pid = id(player)
            vehicle = player.vehicle
            if vehicle:
                if pid not in self.__vehicle_rounds:
                    self.__vehicle_rounds[pid] = {"round": vehicle.round, "ticks_left": 0}
                
                state = self.__vehicle_rounds[pid]
                
                # Check if round advanced
                if vehicle.round > state["round"]:
                    state["ticks_left"] = self.config.round_advance_ticks
                    state["round"] = vehicle.round
                
                # Decrement ticks
                if state["ticks_left"] > 0:
                    state["ticks_left"] -= 1

    def _render_intersection_modules(self, game: Game):
        lanes = game.lanes
        track_modules = game.track_modules
        lane_lengths = {lane: 0.0 for lane in lanes}
        
        for module in track_modules:
            is_intersection = (module.track_type == TrackType.INTERSECTION)
            for lane in lanes:
                line_length = module.get_line_length_for_lane(lane)
                start_pos = lane_lengths[lane]
                end_pos = start_pos + line_length
                
                if is_intersection and line_length > 0:
                    # lane_total = game.get_track_length_for_lane(lane)
                    lane_total = game.__get_lane_track_length(lane)
                    if lane_total > 0:
                        start_ratio = start_pos / lane_total
                        end_ratio = end_pos / lane_total
                        self.display.fill_lane_section_by_ratio(lane, start_ratio, end_ratio, LIGHT_GRAY)
                        
                lane_lengths[lane] = end_pos

    def _render_intersection_animations(self, game: Game):
        players = game.players

        for player in players:
            vehicle = player.vehicle
            if vehicle and vehicle.lane:
                module, _ = game.get_track_module_for_lane_position(vehicle.lane, vehicle.position)
                if module and module.track_type == TrackType.INTERSECTION:
                    self.display.fill_lane(vehicle.lane, LIGHT_PINK)

    def _render_start_of_track(self, game: Game):
        lanes = game.lanes

        for lane in lanes:
            self.display.set_lane_pixel_by_ratio(lane, 0.0, GRAY)

    def _render_round_advance(self, game: Game):
        players = game.players

        for player in players:
            vehicle = player.vehicle
            
            if vehicle.lane is not None:
                pid = id(player)
                if vehicle and pid in self.__vehicle_rounds and self.__vehicle_rounds[pid]["ticks_left"] > 0:
                    ticks_left = self.__vehicle_rounds[pid]["ticks_left"]
                    change_interv = self.config.round_advance_tick_color_change
                    if (ticks_left // change_interv) % 2 == 0:
                        self.display.fill_lane(vehicle.lane, YELLOW)
                    else:
                        self.display.fill_lane(vehicle.lane, WHITE)

    def _render_inactive_vehicles(self, game: Game):
        players = game.players

        for player in players:
            vehicle = player.vehicle
            if vehicle and vehicle.lane:
                if not vehicle.active or vehicle.respawn_ticks > 0:
                    ticks = vehicle.respawn_ticks
                    change_interv = self.config.respawn_tick_color_change
                    color = WHITE if (ticks // change_interv) % 2 == 0 else GRAY
                    # lane_total = game.get_track_length_for_lane(vehicle.lane)
                    lane_total = game.__get_lane_track_length(vehicle.lane)
                    if lane_total > 0:
                        ratio = vehicle.position / lane_total
                        self.display.set_lane_pixel_by_ratio(vehicle.lane, ratio, color)

    def _render_active_vehicles(self, game: Game):
        players = game.players

        for player in players:
            vehicle = player.vehicle
            if vehicle and vehicle.lane and vehicle.active and vehicle.respawn_ticks <= 0:
                module, _ = game.get_track_module_for_lane_position(vehicle.lane, vehicle.position)
                if module:
                    line = module.get_line_for_lane(vehicle.lane)
                    if line:
                        dp = line.driving_profile
                        color = self._get_active_color(vehicle, dp)
                        # lane_total = game.get_track_length_for_lane(vehicle.lane)
                        lane_total = game.__get_lane_track_length(vehicle.lane)
                        if lane_total > 0:
                            ratio = vehicle.position / lane_total
                            self.display.set_lane_pixel_by_ratio(vehicle.lane, ratio, color)

    def _get_active_color(self, vehicle: Vehicle, dp: DrivingProfile) -> tuple[int,int,int]:
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
            ratio = (speed - half_max) / (dp.max_speed - half_max) if dp.max_speed != half_max else 1.0
            return interpolate_color(vehicle.primary_color, vehicle.decelerate_color, ratio)
        elif speed < -half_min:
            ratio = (abs(speed) - half_min) / (abs(dp.min_speed) - half_min) if abs(dp.min_speed) != half_min else 1.0
            return interpolate_color(vehicle.primary_color, vehicle.accelerate_color, ratio)
        else:
            return vehicle.primary_color
