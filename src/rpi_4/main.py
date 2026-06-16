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
from src.sound.sound_manager import SoundManager, GameSound
from src.game.game import Game
from src.game.lane import Lane
from src.game.player import Player
from src.game.vehicle import Vehicle
from src.game.track_module import TrackModule, TrackType
from src.game.line import Line
from src.game.driving_profile import DrivingProfile
from src.game.settings import Settings
import time

logger = get_logger()


def main():
    """
    Entrypoint for Raspberry Pi 4 execution.
    Run with: ``sudo .venv/bin/python -m src.rpi_4.main``

    Sets up the sound manager, builds the game and its display, waits for the
    players' start signal, plays the 3-2-1-GO start sequence and then runs the
    game loop.

    Args:
        None

    Returns:
        None
    """
    logger.log("Raspberry Pi 4: Main script running.")

    sound_manager = SoundManager()
    try:
        sound_manager.start()
    except Exception as e:
        logger.log(f"Error starting SoundManager: {e}")
        return

    logger.log("SoundManager started successfully. Building game and display...")
    game, display = build_game(sound_manager)

    # logger.log(
    #     "Setup of Game, SignalReceiver, and PlayerController complete. "
    #     "Waiting for all players to press their start button."
    # )

    # Game startup:
    # The game waits for an initial signal of all player controllers pressing
    # their button (``PlayerController.special_1``) for at least one second.
    # Then the start sequence ticks down 3, 2, 1, GO! while the matching sound
    # effect plays in parallel, before the game loop is started.
    # uncomment for immediate startup
    # wait_for_start_signal(game)

    # uncomment for start sequence
    # logger.log("Start signal received. Running start sequence.")
    # run_start_sequence(display, game, sound_manager)

    logger.log("Start sequence complete. Starting game loop.")
    try:
        game.start_game(
            fetch_interval_s=0.02, display_interval_s=0.02, game_tick_interval_s=0.02
        )
    finally:
        sound_manager.stop_all()


def wait_for_start_signal(
    game: Game,
    hold_seconds: float = 0.2,
    poll_interval_s: float = 0.1,
) -> None:
    """Block until all players hold their start button for ``hold_seconds``.

    The function continuously polls the signal receiver and tracks how long all
    players have simultaneously held their ``special_1`` button. As soon as the
    button has been held continuously for ``hold_seconds`` the function returns.

    Args:
        game (Game): Game instance providing the players and the signal poller.
        hold_seconds (float): Required continuous hold duration in seconds.
        poll_interval_s (float): Delay between consecutive signal polls.

    Returns:
        None
    """
    players = game.players
    held_since: float | None = None

    while True:
        game.fetch_data()

        all_pressed = bool(players) and all(
            player.controller.special_1 for player in players
        )
        now = time.perf_counter()

        if all_pressed:
            if held_since is None:
                held_since = now
            elif now - held_since >= hold_seconds:
                return
        else:
            held_since = None

        time.sleep(poll_interval_s)


def fill_first_track_module(
    display: LedDisplay,
    game: Game,
    color: tuple[int, int, int],
) -> None:
    """Paint the first track module section of every lane in a single color.

    The first module occupies the lane range ``[0, segment / total]`` where
    ``segment`` is the module's line length on the lane and ``total`` is the
    lane's full length. The painted buffers are pushed to the strips immediately.

    Args:
        display (LedDisplay): Display whose virtual buffers are updated.
        game (Game): Game providing track modules, lanes and lane lengths.
        color (tuple[int, int, int]): RGB color used to fill the section.

    Returns:
        None
    """
    track_modules = game.track_modules
    if not track_modules:
        return

    first_module = track_modules[0]
    for lane in game.lanes:
        total_length = game.get_lane_track_length(lane)
        segment_length = first_module.get_line_length_for_lane(lane)
        if total_length <= 0 or segment_length <= 0:
            display.fill_lane(lane, color)
            continue

        end_ratio = min(1.0, segment_length / total_length)
        display.fill_lane_section_by_relative_position(lane, 0.0, end_ratio, color)

    display.render()


def run_start_sequence(
    display: LedDisplay,
    game: Game,
    sound_manager: SoundManager,
    step_seconds: float = 1.0,
) -> None:
    """Run the 3-2-1-GO start animation together with the start sound.

    The "3, 2, 1, GO!" sound effect is started first so that it plays in
    parallel with the LED animation. The first track module then cycles through
    red (3s), yellow (2s) and green (1s) before being cleared as the game loop
    takes over the display.

    Args:
        display (LedDisplay): Display used for the countdown animation.
        game (Game): Game providing the track layout for the animation.
        sound_manager (SoundManager): Manager used to play the start sound.
        step_seconds (float): Duration of each countdown step in seconds.

    Returns:
        None
    """
    # sound for startup
    sound_manager.play(GameSound.START_SIGNAL)

    # colors on first track module
    for color in (RED, YELLOW, GREEN):
        fill_first_track_module(display, game, color)
        time.sleep(step_seconds)

    # GO! Clear the animation so the game loop fully owns the display.
    fill_first_track_module(display, game, BLACK)


def build_game(sound_manager: SoundManager) -> tuple[Game, LedDisplay]:
    """
    Builds and configures the Game object with lanes, players, and track modules.

    This method creates the lanes, sets up two local players, constructs the
    track modules with their respective lines and driving profiles, and initializes the
    Game object along with its base settings. It also configures the display units
    and the display manager for the game simulation.

    Args:
        sound_manager (SoundManager): Shared audio manager passed to the game so
            it can trigger sound effects and per-player engine sounds.

    Returns:
        tuple[Game, LedDisplay]: The configured Game instance and the LED display
            used by the start sequence animation.
    """
    player_controller_1 = PlayerController()
    player_controller_2 = PlayerController()
    signal_receiver = SignalReceiver(
        controllers=[player_controller_1, player_controller_2]
    )
    # signal_receiver = SignalReceiver(controllers=[player_controller_1])

    lane_0 = Lane()  # 0
    lane_1 = Lane()  # 1 middle lane
    lane_2 = Lane()  # 2

    # Configuring display and display manager
    real_strips = {}
    virtual_strips = []

    strip_0_leds = 250 -32
    strip_1_leds = 250 -33
    
    if RPI_WS281X_AVAILABLE and PixelStrip is not None:
        strip0 = PixelStrip(
            num=strip_0_leds,
            pin=18,
            freq_hz=800_000,
            dma=10,
            invert=False,
            brightness=255,
            channel=0,  # needed for gpio 18
        )
        strip1 = PixelStrip(
            num=strip_1_leds,
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
            lane=lane_0, real_strip_id=0, min_index=0, max_index=strip_0_leds - 1
        ),
        VirtualLedStrip(
            lane=lane_2, real_strip_id=1, min_index=0, max_index=strip_1_leds - 1
        ),
    ]

    display = LedDisplay(
        real_strips, virtual_strips
    )  # Provide physical and virtual strips here when available

    display_config = DisplayConfig()
    display_manager = DisplayManager(display, display_config)

    # settings
    max_speed: int = 120
    settings = Settings(
        max_speed=max_speed,
        respawn_ticks=50,
        friction_percent=0.04,
        acceleration_multiplier=0.06,
        lane_change_window=5,
        vehicle_crash_distance=3.0,
    )

    player_1 = Player(
        controller=player_controller_1,
        vehicle=Vehicle(
            lane=lane_0,
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
            part_length=34.3,
            sound_stereo_ratio_left=0.5,
            lines=[
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed),
                    lane=lane_0,
                    line_length=34.0,
                ),
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed),
                    lane=lane_2,
                    line_length=34.6,
                ),
            ],
        ),
        TrackModule(
            track_type=TrackType.CURVE_LEFT,
            part_length=27.3,
            sound_stereo_ratio_left=0.5,
            lines=[
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed * 0.75),
                    lane=lane_0,
                    line_length=22.5,
                ),
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed * 0.85),
                    lane=lane_2,
                    line_length=32.0,
                ),
            ],
        ),
        TrackModule(
            track_type=TrackType.INTERSECTION,
            part_length=45.5,
            sound_stereo_ratio_left=0.5,
            lines=[
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed, lane_change_allowed=True),
                    lane=lane_0,
                    line_length=45.5,
                ),
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed, lane_change_allowed=True),
                    lane=lane_1,
                    line_length=45.5,  # TODO: edit this intersection!
                ),
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed, lane_change_allowed=True),
                    lane=lane_2,
                    line_length=45.5,
                ),
            ],
        ),
        TrackModule(
            track_type=TrackType.CURVE_RIGHT,
            part_length=80.5,
            sound_stereo_ratio_left=0.5,
            lines=[
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed * 0.75),
                    lane=lane_0,
                    line_length=94.5,
                ),
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed * 0.65),
                    lane=lane_2,
                    line_length=66.5,
                ),
            ],
        ),
        TrackModule(
            track_type=TrackType.STRAIGHT,
            part_length=45.7,
            sound_stereo_ratio_left=0.5,
            lines=[
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed),
                    lane=lane_0,
                    line_length=45.7,
                ),
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed),
                    lane=lane_2,
                    line_length=45.7,
                ),
            ],
        ),
        TrackModule(
            track_type=TrackType.LOOPING, 
            part_length=110.0,
            sound_stereo_ratio_left=0.5,
            lines=[
                Line(
                    driving_profile=DrivingProfile(
                        max_speed=max_speed, min_speed=max_speed * 0.6
                    ),
                    lane=lane_0,
                    line_length=110.0,
                ),
                Line(
                    driving_profile=DrivingProfile(
                        max_speed=max_speed, min_speed=max_speed * 0.6
                    ),
                    lane=lane_2,
                    line_length=110.0,
                ),
            ],
        ),
        TrackModule(
            track_type=TrackType.INTERSECTION,
            part_length=34.2,
            sound_stereo_ratio_left=0.5,
            lines=[
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed, lane_change_allowed=True),
                    lane=lane_0,
                    line_length=34.0,
                ),
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed, lane_change_allowed=True),
                    lane=lane_1,
                    line_length=34.2,  # TODO: edit this intersection!
                ),
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed, lane_change_allowed=True),
                    lane=lane_2,
                    line_length=34.3,
                ),
            ],
        ),
        TrackModule(
            track_type=TrackType.CURVE_RIGHT_BENDED,
            part_length=49.4,
            sound_stereo_ratio_left=0.5,
            lines=[
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed * 0.90),
                    lane=lane_0,
                    line_length=41.1,
                ),
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed * 0.95),
                    lane=lane_2,
                    line_length=57.6,
                ),
            ],
        ),
        TrackModule(
            track_type=TrackType.STRAIGHT,
            part_length=11.4,
            sound_stereo_ratio_left=0.5,
            lines=[
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed),
                    lane=lane_0,
                    line_length=11.4,
                ),
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed),
                    lane=lane_2,
                    line_length=11.4,
                ),
            ],
        ),
    ]

    game = Game(
        players=[player_1, player_2],
        track_modules=track_modules,
        settings=settings,
        signal_receiver=signal_receiver,
        lanes=[lane_0, lane_1, lane_2],
        display_manager=display_manager,
        # sound_manager=sound_manager,
    )

    return game, display


if __name__ == "__main__":
    main()
