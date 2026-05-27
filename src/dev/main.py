from src.controller.signal_receiver_mock import SignalReceiverMock
from src.display.led_display import LedDisplay
from src.display.display_manager import DisplayManager
from src.game.lane import Lane
from src.logger.multi_logger import get_logger
from src.game.game import Game
from src.controller.player_controller import PlayerController
from src.game.player import Player
from src.game.vehicle import Vehicle
from src.game.track_module import TrackModule, TrackType
from src.game.line import Line
from src.game.driving_profile import DrivingProfile
from src.game.settings import Settings

logger = get_logger()


def simple_game_setup():
    """Create and run a local development game loop.

    This setup is intentionally deterministic and explicit so it can be used for
    manual validation of lane changes, profile-based falling, collisions, and
    respawn behavior introduced in recent game logic refactoring.
    """
    # Core simulation settings tuned for local development.
    max_speed = 100.0
    settings = Settings(
        max_speed=max_speed,
        respawn_ticks=200,
        friction_percent=0.02,
        acceleration_multiplier=0.015,
        special_1_threshold=0.5,
        lane_change_ticks=25,
    )

    # Lanes are ordered left-to-right.
    lane_1 = Lane()
    lane_2 = Lane()

    # Two local players on separate start lanes.
    player_1 = Player(
        controller=PlayerController(),
        vehicle=Vehicle(lane=lane_1)
    )
    player_2 = Player(
        controller=PlayerController(),
        vehicle=Vehicle(lane=lane_2)
    )

    # Mock receiver provides random controller values on dev machines.
    signal_receiver = SignalReceiverMock(controllers=[player_1.controller, player_2.controller])

    # Track modules with explicit lane-change permission and profile limits.
    # This enables manual testing of the updated game loop rules.
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
                    driving_profile=DrivingProfile(max_speed=65, max_acceleration=7, lane_change_allowed=False),
                    lane=lane_1,
                    line_length=28,
                ),
                Line(
                    driving_profile=DrivingProfile(max_speed=75, max_acceleration=8, lane_change_allowed=False),
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
                    driving_profile=DrivingProfile(max_speed=85, max_acceleration=9, lane_change_allowed=True),
                    lane=lane_1,
                    line_length=55,
                ),
                Line(
                    driving_profile=DrivingProfile(max_speed=75, max_acceleration=8, lane_change_allowed=True),
                    lane=lane_2,
                    line_length=45
                ),
            ],
        ),
        # TrackModule(
        #     track_type=TrackType.LOOPING,
        #     part_length=80,
        #     lines=[
        #         Line(
        #             driving_profile=DrivingProfile(min_speed=70, lane_change_allowed=False),
        #             lane=lane_1,
        #             line_length=80,
        #         ),
        #         Line(
        #             driving_profile=DrivingProfile(min_speed=70, lane_change_allowed=False),
        #             lane=lane_2,
        #             line_length=80
        #         ),
        #     ],
        # )
    ]
    
    display = LedDisplay({}, [])  # Empty display for dev testing without rendering dependency.
    display_manager = DisplayManager(display=display) 

    # Build game instance.
    game = Game(
        players=[player_1, player_2],
        track_modules=track_modules,
        settings=settings,
        signal_receiver=signal_receiver,
        lanes=[lane_1, lane_2],
        display_manager=display_manager
    )

    logger.log("Starting dev game loop with updated game logic settings.")
    game.start_game(fetch_interval_s=0.02, display_interval_s=0.02, game_tick_interval_s=0.02)


def main():
    """Entrypoint for local development execution."""
    simple_game_setup()


if __name__ == "__main__":
    print("Running on dev pc.")
    main()
    