from src.controller.signal_receiver import SignalReceiver
from src.controller.player_controller import PlayerController
from src.logger.multi_logger import get_logger
from src.display.led_display import (
    LedDisplay,
    VirtualLedStrip,
    PixelStrip,  # type: ignore
    RPI_WS281X_AVAILABLE,
)
from src.display.display_manager import DisplayManager
from src.display.config import DisplayConfig
from src.display.color_constants import *  # noqa: F403
from src.round_counter.round_counter import RoundCounter
from src.sound.sound_manager import SoundManager, GameSound
from src.sound.threaded_sound_manager import ThreadedSoundManager

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

    # Instantiate the low-level manager and wrap it inside the threaded manager
    raw_sound_manager = SoundManager()
    sound_manager = ThreadedSoundManager(raw_sound_manager)
    try:
        sound_manager.start()
        sound_manager.set_master_volume(100)
    except Exception as e:
        logger.log(f"Error starting SoundManager: {e}")
        logger.log("Continuing without audio.")

    first_run: bool = True

    while True:
        # new game for every loop iteration, to ensure a clean state.
        logger.log("SoundManager initialized. Building game and display...")
        game, led_display = build_game(sound_manager)

        if first_run:
            logger.log("Clearing all LEDs on startup and playing startup sound...")
            clear_all_leds(led_display)
            time.sleep(0.25)  # cleaner display clearing

            # startup sound and initial LED colors
            set_all_leds(led_display, game.lanes, DARK_PURPLE)
            sound_manager.play(GameSound.GAME_INIT, volume=20)
            time.sleep(1)
            first_run = False

        logger.log(
            "Setup of Game, SignalReceiver, and PlayerController complete. "
            "Waiting for all players to press their start button."
        )

        # start waiting music, end if the start signal is received
        vibe_music: str = sound_manager.play(GameSound.VIBE_2, loop=True, volume=10)

        # Game startup:
        # The game waits for an initial signal of all player controllers pressing
        # their button (``PlayerController.special_1``).
        # Then the start sequence ticks down 3, 2, 1, GO! while the matching sound
        # effect plays in parallel, before the game loop is started.
        wait_for_start_signal(game)

        # stop waiting music
        sound_manager.stop_sound(vibe_music)

        # uncomment for start sequence
        logger.log("Start signal received. Running start sequence.")
        run_start_sequence(led_display, game, sound_manager)

        logger.log("Start sequence complete. Starting game loop.")
        try:
            game.start_game(
                fetch_interval_s=0.02,
                display_interval_s=0.03,
                game_tick_interval_s=0.02,
            )
        except Exception as e:
            logger.log(f"Error during game loop: {e}")
            raise e
        finally:
            # end of game
            sound_manager.stop_all()
            sound_manager.play(GameSound.RACE_FINISH, volume=30)
            logger.log("Race finished. Restarting...")
            time.sleep(4)
            game.clear_round_counters()
            # ensure cleanup of game resources before next iteration
            del game


def clear_all_leds(display: LedDisplay) -> None:
    """Clear all LEDs to black before applying new colors on startup."""
    
    display.clear()
    display.render()


def set_all_leds(
    display: LedDisplay, lanes: list[Lane], color: tuple[int, int, int]
) -> None:
    """Set all LEDs to a single color before applying new colors on startup."""
    for lane in lanes:
        display.fill_lane(lane, color, color_ratio=0.3)
    display.render()


def wait_for_start_signal(
    game: Game,
    poll_interval_s: float = 0.25,
) -> None:
    """Block until all players press their start button.

    The function continuously polls the signal receiver and checks if all
    players have simultaneously pressed their ``special_1`` button.

    Args:
        game (Game): Game instance providing the players and the signal poller.
        hold_seconds (float): Required continuous hold duration in seconds.
        poll_interval_s (float): Delay between consecutive signal polls.

    Returns:
        None
    """
    players = game.players
    logger.log(f"Waiting for start signal from both players...")

    while True:
        game.fetch_data()

        all_pressed = bool(players) and all(
            player.controller.special_1 for player in players
        )


        if all_pressed:
            return

        time.sleep(poll_interval_s)


def fill_first_track_module(
    display: LedDisplay,
    game: Game,
    color: tuple[int, int, int],
) -> None:
    """Paint only first-track-module lanes in a single color.

    For each lane that is explicitly part of the first module, the painted
    range is ``[0, segment / total]`` where ``segment`` is the module's line
    length on that lane and ``total`` is the lane's full length. Lanes not
    present in the first module are not touched.

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
    for line in first_module.lines:
        lane = line.lane
        total_length = game.get_lane_track_length(lane)
        segment_length = line.length
        if total_length <= 0 or segment_length <= 0:
            continue

        end_ratio = min(1.0, segment_length / total_length)
        display.fill_lane_section_by_relative_position(lane, 0.0, end_ratio, color)

    display.render()


def run_start_sequence(
    display: LedDisplay,
    game: Game,
    sound_manager: ThreadedSoundManager,
    step_seconds: float = 1.0,
) -> None:
    """Run the 3-2-1-GO start animation together with the start sound.

    The "3, 2, 1, GO!" sound effect is started first so that it plays in
    parallel with the LED animation. The first track module then cycles through
    three colors before being cleared as the game loop takes over the display.

    Args:
        display (LedDisplay): Display used for the countdown animation.
        game (Game): Game providing the track layout for the animation.
        sound_manager (ThreadedSoundManager): Manager used to play the start sound.
        step_seconds (float): Duration of each countdown step in seconds.

    Returns:
        None
    """
    # sound for startup
    sound_manager.play(GameSound.STARTUP, volume=30)
    clear_all_leds(display)

    # colors on first track module
    for i in range(3, 0, -1):
        fill_first_track_module(display, game, DARK_PURPLE)
        time.sleep(step_seconds * 0.25)
        clear_all_leds(display)
        time.sleep(step_seconds * 0.75)

    # GO! Clear the animation so the game loop fully owns the display.
    fill_first_track_module(display, game, BLACK)


def build_game(sound_manager: ThreadedSoundManager) -> tuple[Game, LedDisplay]:
    """
    Builds and configures the Game object with lanes, players, and track modules.

    This method creates the lanes, sets up two local players, constructs the
    track modules with their respective lines and driving profiles, and initializes the
    Game object along with its base settings. It also configures the display units
    and the display manager for the game simulation.

    Args:
        sound_manager (ThreadedSoundManager): Shared audio manager passed to the game so
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

    lane_0 = Lane()  # 0 -> inner
    lane_1 = Lane()  # 1 -> middle
    lane_2 = Lane()  # 2 -> outer

    # Configuring display and display manager
    real_strips = {}
    virtual_strips = []
    
    # beginning: 64 matrix leds
    leds_matrix_count = 64
    
    # middle: main track leds    
    leds_track_main_0 = 219
    leds_track_main_1 = 218
    
    # end: intersection track leds
    leds_track_intersection_0 = 24
    leds_track_intersection_1 = 18
    
    leds_strip_0 = leds_track_main_0 + leds_track_intersection_0
    leds_strip_1 = leds_track_main_1 + leds_track_intersection_1

    # Initialize physical strips ONLY on the first run
    if RPI_WS281X_AVAILABLE and PixelStrip is not None:
        strip0 = PixelStrip(
            num=leds_strip_0 + leds_matrix_count,
            pin=18,
            freq_hz=800_000,
            dma=10,
            invert=False,
            brightness=255,
            channel=0,  # needed for gpio 18
        )
        strip1 = PixelStrip(
            num=leds_strip_1 + leds_matrix_count,
            pin=19,
            freq_hz=800_000,
            dma=10,
            invert=False,
            brightness=255,
            channel=1,  # needed for gpio 19
        )
        strip0.begin()
        strip1.begin()

        real_strips = {
            0: strip0,
            1: strip1,
        }

    virtual_strips = [
        VirtualLedStrip( # main track 0
            lane=lane_0,
            real_strip_id=0,
            min_index=leds_matrix_count,
            max_index=leds_matrix_count + leds_track_main_0 - 1,
        ),
        VirtualLedStrip( # intersection 0
            lane=lane_1,
            real_strip_id=0,
            min_index=leds_matrix_count + leds_track_main_0, 
            max_index=leds_matrix_count + leds_track_main_0 + leds_track_intersection_0 - 1,
        ),
        VirtualLedStrip( # intersection 1
            lane=lane_1,
            real_strip_id=1,
            min_index=leds_matrix_count + leds_track_main_1,
            max_index=leds_matrix_count + leds_track_main_1 + leds_track_intersection_1 - 1,
        ),
        VirtualLedStrip( # main track 1
            lane=lane_2,
            real_strip_id=1,
            min_index=leds_matrix_count,
            max_index=leds_matrix_count + leds_track_main_1 - 1,
        ),
    ]

    display = LedDisplay(real_strips, virtual_strips)
    display_config = DisplayConfig()
    display_manager = DisplayManager(display, display_config)

    # players
    player_1 = Player(
        controller=player_controller_1,
        vehicle=Vehicle(
            lane=lane_0,
            primary_color=LIGHT_BLUE,
            accelerate_color=GRAY,
            decelerate_color=LIME,
        ),
    )
    player_2 = Player(
        controller=player_controller_2,
        vehicle=Vehicle(
            lane=lane_2,
            primary_color=MAGENTA,
            accelerate_color=GRAY,
            decelerate_color=RED_PURPLISH,
        ),
    )

    # Instantiate the round counters.
    # Colors are matched to the primary colors of each player's vehicle.
    round_counters = {
        player_1: RoundCounter(
            strip=real_strips.get(0),
            start_index=0,  # Matrix is placed at the very beginning
            zigzag=True,
            mirror_horizontal=True,
            color=player_1.vehicle.primary_color,
            auto_show=False,
        ),
        player_2: RoundCounter(
            strip=real_strips.get(1),
            start_index=0,  # Matrix is placed at the very beginning
            zigzag=True,
            mirror_horizontal=True,
            color=player_2.vehicle.primary_color,
            auto_show=False,
        ),
    }

    max_speed: int = 100
    settings = Settings(
        max_speed=max_speed,
        respawn_ticks=75,
        friction_percent=0.05,
        acceleration_multiplier=0.06,
        lane_change_window=8,
        vehicle_crash_distance=3.0,
        rounds_to_win=20,
    )

    track_modules: list[TrackModule] = [
        TrackModule(
            track_type=TrackType.STRAIGHT,
            part_length=34.3,
            sound_stereo_ratio_left=0.6,
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
            sound_stereo_ratio_left=0.4,
            lines=[
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed * 0.85),
                    lane=lane_0,
                    line_length=22.5,
                ),
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed * 0.90),
                    lane=lane_2,
                    line_length=32.0,
                ),
            ],
        ),
        TrackModule(
            track_type=TrackType.INTERSECTION,
            part_length=45.5,
            sound_stereo_ratio_left=0.2,
            lines=[
                Line(
                    driving_profile=DrivingProfile(
                        max_speed=max_speed, lane_change_allowed=True
                    ),
                    lane=lane_0,
                    line_length=45.5,
                ),
                Line(
                    driving_profile=DrivingProfile(
                        max_speed=max_speed, lane_change_allowed=True
                    ),
                    lane=lane_1,
                    line_length=45.5,
                ),
                Line(
                    driving_profile=DrivingProfile(
                        max_speed=max_speed, lane_change_allowed=True
                    ),
                    lane=lane_2,
                    line_length=45.5,
                ),
            ],
        ),
        TrackModule(
            track_type=TrackType.CURVE_RIGHT,
            part_length=80.5,
            sound_stereo_ratio_left=0.1,
            lines=[
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed * 0.80),
                    lane=lane_0,
                    line_length=94.5,
                ),
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed * 0.70),
                    lane=lane_2,
                    line_length=66.5,
                ),
            ],
        ),
        TrackModule(
            track_type=TrackType.STRAIGHT,
            part_length=45.7,
            sound_stereo_ratio_left=0.3,
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
            sound_stereo_ratio_left=0.6,
            lines=[
                Line(
                    driving_profile=DrivingProfile(
                        max_speed=max_speed, min_speed=max_speed * 0.4
                    ),
                    lane=lane_0,
                    line_length=110.0,
                ),
                Line(
                    driving_profile=DrivingProfile(
                        max_speed=max_speed, min_speed=max_speed * 0.4
                    ),
                    lane=lane_2,
                    line_length=110.0,
                ),
            ],
        ),
        TrackModule(
            track_type=TrackType.INTERSECTION,
            part_length=34.2,
            sound_stereo_ratio_left=0.8,
            lines=[
                Line(
                    driving_profile=DrivingProfile(
                        max_speed=max_speed, lane_change_allowed=True
                    ),
                    lane=lane_0,
                    line_length=34.0,
                ),
                Line(
                    driving_profile=DrivingProfile(
                        max_speed=max_speed, lane_change_allowed=True
                    ),
                    lane=lane_1,
                    line_length=34.2,
                ),
                Line(
                    driving_profile=DrivingProfile(
                        max_speed=max_speed, lane_change_allowed=True
                    ),
                    lane=lane_2,
                    line_length=34.3,
                ),
            ],
        ),
        TrackModule(
            track_type=TrackType.CURVE_RIGHT_BENDED,
            part_length=49.4,
            sound_stereo_ratio_left=0.9,
            lines=[
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed * 0.90),
                    lane=lane_0,
                    line_length=41.1,
                ),
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed * 0.93),
                    lane=lane_2,
                    line_length=57.6,
                ),
            ],
        ),
        TrackModule(
            track_type=TrackType.STRAIGHT,
            part_length=11.4,
            sound_stereo_ratio_left=0.8,
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
        sound_manager=sound_manager,
        round_counters=round_counters,
    )

    return game, display


if __name__ == "__main__":
    main()
