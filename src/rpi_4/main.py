from src.controller.signal_receiver import SignalReceiver
from src.controller.player_controller import PlayerController
from src.logger.multi_logger import get_logger
from src.display.led_display import (
    LedDisplay,
    VirtualLedStrip,
    PixelStrip,
    RPI_WS281X_AVAILABLE,
)
from src.display.display_manager import DisplayManager
from src.display.config import DisplayConfig
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
    Run with: ``sudo .venv/bin/python -m src.rpi_4.main``

    Sets up the player controllers, signal receiver, and components for
    the display, then builds the game instance and starts the game loop.

    Args:
        None

    Returns:
        None
    """
    logger.log("Raspberry Pi 4: Main script running.")

    # game startup:
    # the game waits for an initial signal of all player controllers pressing
    # their button ``player.PlayerController.special_1 = 1`` for at least 1 second.
    # Then, the game ticks down: 3, 2, 1, GO! and starts the game loop.
    # The start sequence should also start a led animation on the first track module:
    # 3s: all LEDs red.
    # 2s: all LEDs yellow.
    # 1s: all LEDs green.
    # 0s: all LEDs off, as game loop starts
    # Additionally, a "3,2,1, GO!" sound effect should be played at the start of the game loop,
    # in parallel to the LED animation.

    # startup condition checker

    game = build_game()

    logger.log(
        "Setup of Game, SignalReceiver, and PlayerController complete. Starting game loop."
    )
    game.start_game(
        fetch_interval_s=0.02, display_interval_s=0.02, game_tick_interval_s=0.02
    )


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
    signal_receiver = SignalReceiver(
        controllers=[player_controller_1, player_controller_2]
    )
    # signal_receiver = SignalReceiver(controllers=[player_controller_1])

    lane_1 = Lane()
    lane_2 = Lane()

    # Configuring display and display manager
    led_strip_length_m: int = 5
    leds_per_meter: int = 50
    led_count = led_strip_length_m * leds_per_meter
    real_strips = {}
    virtual_strips = []

    if RPI_WS281X_AVAILABLE and PixelStrip is not None:
        strip0 = PixelStrip(
            num=led_count,
            pin=18,
            freq_hz=800_000,
            dma=10,
            invert=False,
            brightness=255,
            channel=0,  # needed for gpio 18
        )
        strip1 = PixelStrip(
            num=led_count,
            pin=19,
            freq_hz=800_000,
            dma=10,
            invert=False,
            brightness=int(255),  # safety with slightly dimmed brightness
            channel=1,  # needed for gpio 19
        )
        strip0.begin()
        strip1.begin()

        real_strips = {
            0: strip0,
            1: strip1,
        }

    virtual_strips = [
        VirtualLedStrip(
            lane=lane_1, real_strip_id=0, min_index=0, max_index=led_count - 1
        ),
        VirtualLedStrip(
            lane=lane_2, real_strip_id=1, min_index=0, max_index=led_count - 1
        ),
    ]

    display = LedDisplay(
        real_strips, virtual_strips
    )  # Provide physical and virtual strips here when available
    display_config = DisplayConfig(
        respawn_tick_color_change=20,
        round_advance_ticks=200,
        round_advance_tick_color_change=20,
    )
    display_manager = DisplayManager(display)

    # settings
    max_speed: int = 40
    settings = Settings(
        max_speed=max_speed,
        respawn_ticks=200,
        friction_percent=0.02,
        acceleration_multiplier=0.01,
        lane_change_ticks=50,
        vehicle_crash_distance=3.0,
    )

    player_1 = Player(
        controller=player_controller_1,
        vehicle=Vehicle(
            lane=lane_1,
            primary_color=GREEN,
            accelerate_color=PURPLE,
            decelerate_color=RED,
        ),
    )
    player_2 = Player(
        controller=player_controller_2,
        vehicle=Vehicle(
            lane=lane_2,
            primary_color=BLUE,
            accelerate_color=PURPLE,
            decelerate_color=RED,
        ),
    )

    track_modules: list[TrackModule] = [
        TrackModule(
            track_type=TrackType.STRAIGHT,
            part_length=50,
            lines=[
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed),
                    lane=lane_1,
                    line_length=50,
                ),
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed),
                    lane=lane_2,
                    line_length=50,
                ),
            ],
        ),
        TrackModule(
            track_type=TrackType.INTERSECTION,
            part_length=20,
            lines=[
                Line(
                    driving_profile=DrivingProfile(
                        max_speed=max_speed * 0.8, lane_change_allowed=True
                    ),
                    lane=lane_1,
                    line_length=50,
                ),
                Line(
                    driving_profile=DrivingProfile(
                        max_speed=max_speed * 0.8, lane_change_allowed=True
                    ),
                    lane=lane_2,
                    line_length=50,
                ),
            ],
        ),
        TrackModule(
            track_type=TrackType.CURVE_LEFT,
            part_length=30,
            lines=[
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed * 0.7),
                    lane=lane_1,
                    line_length=28,
                ),
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed * 0.8),
                    lane=lane_2,
                    line_length=32,
                ),
            ],
        ),
        TrackModule(
            track_type=TrackType.CURVE_RIGHT,
            part_length=50,
            lines=[
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed * 0.6),
                    lane=lane_1,
                    line_length=55,
                ),
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed * 0.5),
                    lane=lane_2,
                    line_length=45,
                ),
            ],
        ),
    ]

    game = Game(
        players=[player_1, player_2],
        # players=[player_1],
        track_modules=track_modules,
        settings=settings,
        signal_receiver=signal_receiver,
        lanes=[lane_1, lane_2],
        display_manager=display_manager,
    )

    return game


if __name__ == "__main__":
    main()
