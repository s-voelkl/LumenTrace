from src.controller.signal_receiver import SignalReceiver
from src.controller.player_controller import PlayerController
from src.logger.multi_logger import get_logger
from src.display.display import Display
from src.display.display_manager import DisplayManager
from src.display.color_constants import *
from src.game.game import Game
from src.game.lane import Lane
from src.game.player import Player
from src.game.vehicle import Vehicle
from src.game.track_module import TrackModule, TrackType
from src.game.line import Line
from src.game.driving_profile import DrivingProfile
from src.game.settings import Settings

logger = get_logger()

def main():
    """
    Entrypoint for Raspberry Pi 4 execution.
    
    Sets up the player controllers, signal receiver, and components for
    the display, then builds the game instance and starts the game loop.
    
    Args:
        None
        
    Returns:
        None
    """
    logger.log("Raspberry Pi 4: Main script running.")

    
    game = build_game()
    
    logger.log("Setup of Game, SignalReceiver, and PlayerController complete. Starting game loop.")
    game.start_game(fetch_interval_s=0.02, display_interval_s=0.02, game_tick_interval_s=0.02)


def build_game() -> Game:
    """
    Builds and configures the Game object with lanes, players, and track modules.
    
    This method creates the lanes, sets up two local players, constructs the
    track modules with their respective lines and driving profiles, and initializes the 
    Game object along with its base settings. It also configures the display units
    and the display manager for the game simulation.
        
    Returns:
        Game: The configured Game instance ready to be started.
    """
    player_controller_1 = PlayerController()
    player_controller_2 = PlayerController()
    signal_receiver = SignalReceiver(controllers=[player_controller_1, player_controller_2])
    
    # Optional: Configure the Display and DisplayManager
    display = Display({}, []) # Provide physical and virtual strips here when available
    display_manager = DisplayManager(display)
    max_speed = 100.0
    settings = Settings(
        max_speed=max_speed,
        respawn_ticks=200,
        friction_percent=0.02,
        acceleration_multiplier=0.015,
        special_1_threshold=0.5,
        lane_change_ticks=25,
    )

    lane_1 = Lane()
    lane_2 = Lane()

    player_1 = Player(
        controller=player_controller_1,
        vehicle=Vehicle(lane=lane_1, primary_color=GREEN, accelerate_color=PURPLE, decelerate_color=BLUE)
    )
    player_2 = Player(
        controller=player_controller_2,
        vehicle=Vehicle(lane=lane_2, primary_color=PINK, accelerate_color=ORANGE, decelerate_color=RED)
    )

    track_modules: list[TrackModule] = [
        TrackModule(
            track_type=TrackType.STRAIGHT,
            part_length=50,
            lines=[
                Line(
                    driving_profile=DrivingProfile(max_speed=100, lane_change_allowed=True),
                    lane=lane_1,
                    line_length=50,
                ),
                Line(
                    driving_profile=DrivingProfile(max_speed=90, lane_change_allowed=True),
                    lane=lane_2,
                    line_length=50
                ),
            ],
        ),
        TrackModule(
            track_type=TrackType.CURVE_LEFT,
            part_length=30,
            lines=[
                Line(
                    driving_profile=DrivingProfile(max_speed=65, lane_change_allowed=False),
                    lane=lane_1,
                    line_length=28,
                ),
                Line(
                    driving_profile=DrivingProfile(max_speed=75, lane_change_allowed=False),
                    lane=lane_2,
                    line_length=32
                ),
            ],
        ),
        TrackModule(
            track_type=TrackType.CURVE_RIGHT,
            part_length=50,
            lines=[
                Line(
                    driving_profile=DrivingProfile(max_speed=85, lane_change_allowed=True),
                    lane=lane_1,
                    line_length=55,
                ),
                Line(
                    driving_profile=DrivingProfile(max_speed=75, lane_change_allowed=True),
                    lane=lane_2,
                    line_length=45
                ),
            ],
        )
    ]

    game = Game(
        players=[player_1, player_2],
        track_modules=track_modules,
        settings=settings,
        signal_receiver=signal_receiver,
        lanes=[lane_1, lane_2],
        display=display,
    )

    return game


if __name__ == "__main__":
    main()
    
