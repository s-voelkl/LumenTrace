"""High-signal unit tests for game simulation rules.

These tests validate rule boundaries described in the project README:
- timed multi-hop lane changes
- proportional position conversion during lane changes
- profile-based falls and lane-gap falls
- same-lane rear-end collisions
- respawn retry behavior and spawn-lane occupancy checks
"""

from collections.abc import Callable
from typing import cast

import pytest

from src.controller.player_controller import PlayerController
from src.controller.signal_receiver_mock import SignalReceiverMock
from src.game import DrivingProfile, Game, Line, Player, Settings, TrackModule, Vehicle
from src.game.lane import Lane
from src.game.track_module import TrackType


def run_game_tick_for_test(game: Game) -> None:
    """Execute one internal game tick.

    Tests call the private loop directly to keep execution deterministic and avoid
    background thread timing side effects.
    """
    tick_fn = cast(Callable[[], None], getattr(game, "_Game__game_loop"))
    tick_fn()


def set_controller_input(
    controller: PlayerController, *, forward_press: float = 0.0, special_1: float = 0.0
) -> None:
    """Set controller values through production input-mapping API."""
    controller.update_input("adc_0", forward_press)
    controller.update_input("dig_0", special_1)


def make_track_modules(
    lanes: list[Lane],
    module_lane_lengths: list[list[float | None]],
    *,
    lane_change_allowed: bool,
    max_speed: float = 100.0,
    min_speed: float = -100.0,
    max_acceleration: float = 10.0,
    min_acceleration: float = -10.0,
) -> list[TrackModule]:
    """Create track modules where each entry defines per-lane line lengths.

    Args:
        lanes (list[Lane]): Lane order from left to right.
        module_lane_lengths (list[list[float | None]]):
            Outer list is module order. Inner list maps 1:1 to lanes.
            ``None`` means lane is missing in that module.
    """
    modules: list[TrackModule] = []
    for lane_lengths in module_lane_lengths:
        lines: list[Line] = []
        for lane, line_length in zip(lanes, lane_lengths):
            if line_length is None:
                continue
            lines.append(
                Line(
                    driving_profile=DrivingProfile(
                        max_speed=max_speed,
                        min_speed=min_speed,
                        max_acceleration=max_acceleration,
                        min_acceleration=min_acceleration,
                        lane_change_allowed=lane_change_allowed,
                    ),
                    lane=lane,
                    line_length=line_length,
                )
            )

        modules.append(
            TrackModule(
                track_type=TrackType.STRAIGHT,
                part_length=max(
                    [length for length in lane_lengths if length is not None],
                    default=0.0,
                ),
                lines=lines,
            )
        )
    return modules


def make_game(
    lanes: list[Lane],
    players: list[Player],
    track_modules: list[TrackModule],
    *,
    settings: Settings | None = None,
) -> Game:
    """Construct a game with deterministic settings for unit tests."""
    if settings is None:
        settings = Settings(
            max_speed=100.0,
            respawn_ticks=5,
            friction_percent=0.02,
            acceleration_multiplier=0.015,
            lane_change_window=20.0,
            vehicle_crash_distance=20.0,
        )
    return Game(
        players=players,
        settings=settings,
        track_modules=track_modules,
        signal_receiver=SignalReceiverMock([player.controller for player in players]),
        lanes=lanes,
        display_manager=None,
    )


def run_ticks(game: Game, tick_count: int) -> None:
    for _ in range(tick_count):
        run_game_tick_for_test(game)
    """Validate core vehicle kinematics rules independent from Game orchestration.

    Why this exists:
    - We keep this test close to the Vehicle API to isolate physics correctness.
    - If this fails, game-level tests should not be blamed first.
    """
    lane = Lane()
    vehicle = Vehicle(lane=lane, position=48.0, speed=10.0, acceleration=100.0)

    # Friction: with 2% friction, speed should become 10 * 0.98 = 9.8.
    vehicle.apply_friction(0.02)
    assert vehicle.speed == pytest.approx(9.8)

    # Speed update: delta = 100 * 0.015 = 1.5, therefore 9.8 + 1.5 = 11.3.
    vehicle.update_speed(max_speed=100.0, acceleration_multiplier=0.015)
    assert vehicle.speed == pytest.approx(11.3)

    # Position/lap: moving by +5 at position 48 on lane length 50 wraps to 3 and adds one lap.
    vehicle.update_position(delta_position=5.0, lane_length=50.0)
    assert vehicle.position == pytest.approx(3.0)
    assert vehicle.round == 1


def test_lane_change_immediately_moves_to_middle_lane_when_button_pressed_before_end_window():
    """Lane change switches immediately to the middle lane if button is pressed before the last 20 units."""
    lanes = [Lane(), Lane(), Lane()]
    modules = make_track_modules(
        lanes, [[100.0, 100.0, 100.0]], lane_change_allowed=True
    )
    settings = Settings(lane_change_window=20.0)

    controller = PlayerController()
    set_controller_input(controller, special_1=1.0)
    # Position = 70.0, distance to end is 30.0 > 20.0, allowed
    player = Player(
        controller=controller, vehicle=Vehicle(lane=lanes[0], position=70.0)
    )
    game = make_game(lanes, [player], modules, settings=settings)

    run_game_tick_for_test(game)
    assert player.vehicle.lane == lanes[1]


def test_lane_change_is_ignored_if_button_pressed_inside_end_window():
    """Lane change must be blocked if button is pressed in the last 20 units."""
    lanes = [Lane(), Lane(), Lane()]
    modules = make_track_modules(
        lanes, [[100.0, 100.0, 100.0]], lane_change_allowed=True
    )
    settings = Settings(lane_change_window=20.0)

    controller = PlayerController()
    set_controller_input(controller, special_1=1.0)
    # Position = 90.0, distance to end is 10.0 <= 20.0, blocked
    player = Player(
        controller=controller, vehicle=Vehicle(lane=lanes[0], position=90.0)
    )
    game = make_game(lanes, [player], modules, settings=settings)

    run_game_tick_for_test(game)
    assert player.vehicle.lane == lanes[0]


def test_lane_change_manual_switch_from_middle_lane():
    """Lane switch from middle lane manually after travelling lane_change_window units."""
    lanes = [Lane(), Lane(), Lane()]
    modules = make_track_modules(
        lanes, [[100.0, 100.0, 100.0]], lane_change_allowed=True
    )
    settings = Settings(lane_change_window=20.0, max_speed=0.0)

    controller = PlayerController()
    player = Player(
        controller=controller, vehicle=Vehicle(lane=lanes[0], position=10.0)
    )
    game = make_game(lanes, [player], modules, settings=settings)

    # Press button, distance to end 90 > 20
    set_controller_input(controller, special_1=1.0)
    run_game_tick_for_test(game)
    assert player.vehicle.lane == lanes[1]

    # Stop pressing button
    set_controller_input(controller, special_1=0.0)
    run_game_tick_for_test(game)

    # Move vehicle to position 25 (only travelled 15 units, < 20)
    player.vehicle.set_position(25.0)
    set_controller_input(controller, special_1=1.0)
    run_game_tick_for_test(game)
    assert player.vehicle.lane == lanes[1] # Manual change blocked

    # Stop pressing button
    set_controller_input(controller, special_1=0.0)
    run_game_tick_for_test(game)

    # Move vehicle to position 35 (travelled 25 units, >= 20)
    player.vehicle.set_position(35.0)
    set_controller_input(controller, special_1=1.0)
    run_game_tick_for_test(game)
    assert player.vehicle.lane == lanes[2] # Manual change succeeded


def test_lane_change_finishes_automatically_near_end_of_middle_lane():
    """Vehicle automatically switches to the final lane 20 units before the end of the middle lane."""
    lanes = [Lane(), Lane(), Lane()]
    modules = make_track_modules(
        lanes, [[100.0, 100.0, 100.0]], lane_change_allowed=True
    )
    settings = Settings(lane_change_window=20.0, max_speed=10.0)

    controller = PlayerController()
    player = Player(
        controller=controller, vehicle=Vehicle(lane=lanes[0], position=10.0)
    )
    game = make_game(lanes, [player], modules, settings=settings)

    # Press button within the first 20 units
    set_controller_input(controller, special_1=1.0)
    run_game_tick_for_test(game)
    assert player.vehicle.lane == lanes[1]

    # Stop pressing button
    set_controller_input(controller, special_1=0.0)

    # Move strictly near the end of the module
    # Middle lane length is 100. The change is triggered when distance_to_end <= 20.0
    # Thus, when local_position >= 80.0
    player.vehicle.set_speed(0.0)
    player.vehicle.set_position(79.0)
    run_game_tick_for_test(game)
    assert player.vehicle.lane == lanes[1]  # Still middle lane since distance is 21.0

    player.vehicle.set_position(81.0)
    run_game_tick_for_test(game)
    # Distance is 19.0 <= 20.0, so it automatically jumps to the right lane (2)
    assert player.vehicle.lane == lanes[2]


def test_lane_change_requires_lane_change_allowed_profile():
    """Lane change must be blocked on lines that disallow lane changes."""
    lanes = [Lane(), Lane(), Lane()]
    modules = make_track_modules(lanes, [[50.0, 50.0, 50.0]], lane_change_allowed=False)
    settings = Settings(lane_change_window=20.0)

    controller = PlayerController()
    set_controller_input(controller, special_1=1.0)
    player = Player(
        controller=controller, vehicle=Vehicle(lane=lanes[0], position=10.0)
    )
    game = make_game(lanes, [player], modules, settings=settings)

    run_game_tick_for_test(game)

    assert player.vehicle.lane == lanes[0]


def test_lane_change_converts_module_position_proportionally():
    """Lane hop from middle to target should preserve module progress by proportional conversion."""
    lanes = [Lane(), Lane(), Lane()]
    # Middle lane is 80 units long, target lane is 40 units long
    modules = make_track_modules(lanes, [[100.0, 80.0, 40.0]], lane_change_allowed=True)
    settings = Settings(lane_change_window=20.0, max_speed=0.0)

    controller = PlayerController()
    player = Player(
        controller=controller, vehicle=Vehicle(lane=lanes[0], position=10.0)
    )
    game = make_game(lanes, [player], modules, settings=settings)

    # Initiate change, move to middle lane
    set_controller_input(controller, special_1=1.0)
    run_game_tick_for_test(game)
    assert player.vehicle.lane == lanes[1]

    # We are on middle lane (length 80), switch triggers at distance <= 20, so at position >= 60
    # Let's set position to 60 (75% of middle lane length)
    player.vehicle.set_position(60.0)
    run_game_tick_for_test(game)
    # Should switch to right lane (length 40). 75% of 40 is 30.0
    assert player.vehicle.lane == lanes[2]
    assert player.vehicle.position == pytest.approx(30.0)


def test_player_falls_on_driving_profile_violation():
    """Speed and acceleration outside profile bounds must trigger immediate fall."""
    lanes = [Lane()]
    modules = make_track_modules(
        lanes,
        [[100.0]],
        lane_change_allowed=False,
        max_speed=5.0,
        min_speed=-5.0,
        max_acceleration=2.0,
        min_acceleration=-2.0,
    )

    controller = PlayerController()
    set_controller_input(controller, forward_press=0.0)
    vehicle = Vehicle(lane=lanes[0], speed=10.0)
    player = Player(controller=controller, vehicle=vehicle)
    settings = Settings(respawn_ticks=7)
    game = make_game(lanes, [player], modules, settings=settings)

    run_game_tick_for_test(game)

    assert not player.vehicle.active
    assert player.vehicle.respawn_ticks == settings.respawn_ticks
    assert player.vehicle.lane == lanes[0]
    assert player.vehicle.speed == 0.0
    assert player.vehicle.acceleration == 0.0


def test_player_falls_on_acceleration_profile_violation():
    """Acceleration outside profile bounds must trigger respawn state immediately."""
    lanes = [Lane()]
    modules = make_track_modules(
        lanes,
        [[100.0]],
        lane_change_allowed=False,
        max_speed=100.0,
        min_speed=-100.0,
        max_acceleration=2.0,
        min_acceleration=-2.0,
    )

    controller = PlayerController()
    # forward_press uses thresholds [42000, 65536]. 45000 yields ~12.7 acc, which violates max 2.0
    set_controller_input(controller, forward_press=45000.0)
    player = Player(controller=controller, vehicle=Vehicle(lane=lanes[0], speed=1.0))
    settings = Settings(respawn_ticks=9)
    game = make_game(lanes, [player], modules, settings=settings)

    run_game_tick_for_test(game)

    assert not player.vehicle.active
    assert player.vehicle.respawn_ticks == settings.respawn_ticks
    assert player.vehicle.lane == lanes[0]
    assert player.vehicle.speed == 0.0
    assert player.vehicle.acceleration == 0.0


def test_no_fall_when_speed_and_acceleration_stay_in_bounds_across_two_modules():
    """Vehicles should remain active if profile limits are respected across module boundaries."""
    lane = Lane()
    low_limit_profile = DrivingProfile(
        max_speed=8.0,
        min_speed=-8.0,
        max_acceleration=2.0,
        min_acceleration=-2.0,
        lane_change_allowed=False,
    )
    high_limit_profile = DrivingProfile(
        max_speed=12.0,
        min_speed=-12.0,
        max_acceleration=4.0,
        min_acceleration=-4.0,
        lane_change_allowed=False,
    )
    modules = [
        TrackModule(
            track_type=TrackType.STRAIGHT,
            part_length=50.0,
            lines=[Line(low_limit_profile, lane, 50.0)],
        ),
        TrackModule(
            track_type=TrackType.STRAIGHT,
            part_length=50.0,
            lines=[Line(high_limit_profile, lane, 50.0)],
        ),
    ]

    controller = PlayerController()
    set_controller_input(controller, forward_press=0.0)
    player = Player(
        controller=controller, vehicle=Vehicle(lane=lane, position=49.0, speed=4.0)
    )
    settings = Settings(friction_percent=0.0, respawn_ticks=6)
    game = make_game([lane], [player], modules, settings=settings)
    setattr(game, "_Game__game_tick_interval_s", 1.0)

    run_ticks(game, 4)

    assert player.vehicle.active
    assert player.vehicle.lane == lane
    assert player.vehicle.respawn_ticks == 0


def test_player_falls_when_moving_into_lane_gap():
    """Crossing a module boundary into a missing lane must trigger a fall."""
    lanes = [Lane(), Lane()]
    modules = make_track_modules(
        lanes,
        [
            [50.0, 50.0],
            [50.0, None],
        ],
        lane_change_allowed=False,
    )

    controller = PlayerController()
    set_controller_input(controller, forward_press=0.0)
    vehicle = Vehicle(lane=lanes[1], position=49.0, speed=2.0)
    player = Player(controller=controller, vehicle=vehicle)
    game = make_game(lanes, [player], modules)
    setattr(game, "_Game__game_tick_interval_s", 1.0)

    run_game_tick_for_test(game)

    assert not player.vehicle.active
    assert player.vehicle.lane == lanes[1]
    assert player.vehicle.speed == 0.0
    assert player.vehicle.acceleration == 0.0


def test_player_falls_when_crossing_middle_lane_gap_between_modules():
    """Exact TODO scenario: middle lane exists in module 1, disappears in module 2."""
    lanes = [Lane(), Lane(), Lane()]
    modules = make_track_modules(
        lanes,
        [
            [50.0, 50.0, 50.0],
            [50.0, None, 50.0],
        ],
        lane_change_allowed=False,
    )

    controller = PlayerController()
    set_controller_input(controller, forward_press=0.0)
    player = Player(
        controller=controller,
        vehicle=Vehicle(lane=lanes[1], position=49.0, speed=2.0),
    )
    game = make_game(lanes, [player], modules)
    setattr(game, "_Game__game_tick_interval_s", 1.0)

    run_game_tick_for_test(game)

    assert not player.vehicle.active
    assert player.vehicle.lane == lanes[1]
    assert player.vehicle.speed == 0.0
    assert player.vehicle.acceleration == 0.0


def test_collision_makes_front_vehicle_fall():
    """Within crash distance, front vehicle on same lane must fall."""
    lanes = [Lane()]
    modules = make_track_modules(lanes, [[100.0]], lane_change_allowed=False)

    rear_controller = PlayerController()
    front_controller = PlayerController()
    set_controller_input(rear_controller, forward_press=0.0)
    set_controller_input(front_controller, forward_press=0.0)

    rear_player = Player(
        controller=rear_controller,
        vehicle=Vehicle(lane=lanes[0], position=0.0, speed=0.0),
    )
    front_player = Player(
        controller=front_controller,
        vehicle=Vehicle(lane=lanes[0], position=15.0, speed=0.0),
    )
    game = make_game(lanes, [rear_player, front_player], modules)

    run_game_tick_for_test(game)

    assert rear_player.vehicle.active
    assert not front_player.vehicle.active
    assert front_player.vehicle.respawn_ticks == game.settings.respawn_ticks


def test_collision_front_vehicle_falls_when_rear_player_closes_gap():
    """Exact TODO-style setup: rear at 0, front at 20, rear moves and front falls."""
    lanes = [Lane()]
    modules = make_track_modules(lanes, [[100.0]], lane_change_allowed=False)

    rear_controller = PlayerController()
    front_controller = PlayerController()
    set_controller_input(rear_controller, forward_press=0.0)
    set_controller_input(front_controller, forward_press=0.0)

    rear_player = Player(
        controller=rear_controller,
        vehicle=Vehicle(lane=lanes[0], position=0.0, speed=1.0),
    )
    front_player = Player(
        controller=front_controller,
        vehicle=Vehicle(lane=lanes[0], position=20.0, speed=0.0),
    )
    game = make_game(lanes, [rear_player, front_player], modules)
    setattr(game, "_Game__game_tick_interval_s", 1.0)

    run_game_tick_for_test(game)

    # Front vehicle should fall according to same-lane crash rule.
    assert rear_player.vehicle.active
    assert not front_player.vehicle.active
    assert front_player.vehicle.respawn_ticks == game.settings.respawn_ticks


def test_respawn_on_single_track_without_other_players():
    """Single fallen vehicle should respawn at position 0 on available lane."""
    lane = Lane()
    modules = make_track_modules([lane], [[50.0]], lane_change_allowed=False)

    controller = PlayerController()
    player_vehicle = Vehicle(lane=lane, position=20.0, round=2)
    player_vehicle.trigger_respawn(1)
    player = Player(controller=controller, vehicle=player_vehicle)
    game = make_game([lane], [player], modules)

    run_game_tick_for_test(game)

    assert player.vehicle.active
    assert player.vehicle.position == 0.0
    assert player.vehicle.lane == lane
    assert player.vehicle.respawn_ticks == 0
    assert player.vehicle.round == 2


def test_respawn_uses_free_lane_on_first_module_without_changing_round():
    """Respawn should select an available lane at module zero and keep lap count unchanged."""
    lanes = [Lane(), Lane()]
    modules = make_track_modules(
        lanes, [[50.0, 50.0], [50.0, 50.0]], lane_change_allowed=False
    )

    occupied_controller = PlayerController()
    falling_controller = PlayerController()
    occupied_player = Player(
        controller=occupied_controller,
        vehicle=Vehicle(lane=lanes[0], position=10.0, speed=0.0),
    )

    respawning_vehicle = Vehicle(lane=lanes[0], position=5.0, round=3)
    respawning_vehicle.trigger_respawn(1)
    respawning_player = Player(
        controller=falling_controller, vehicle=respawning_vehicle
    )

    game = make_game(lanes, [occupied_player, respawning_player], modules)
    run_game_tick_for_test(game)

    assert respawning_player.vehicle.active
    assert respawning_player.vehicle.lane == lanes[1]
    assert respawning_player.vehicle.position == 0.0
    assert respawning_player.vehicle.speed == 0.0
    assert respawning_player.vehicle.acceleration == 0.0
    assert respawning_player.vehicle.respawn_ticks == 0
    assert respawning_player.vehicle.round == 3


def test_respawn_uses_first_lane_when_second_lane_is_occupied():
    """If lane 2 is occupied in first module, respawn should select lane 1."""
    lanes = [Lane(), Lane()]
    modules = make_track_modules(
        lanes, [[50.0, 50.0], [50.0, 50.0]], lane_change_allowed=False
    )

    occupied_controller = PlayerController()
    waiting_controller = PlayerController()

    occupied_player = Player(
        controller=occupied_controller,
        vehicle=Vehicle(lane=lanes[1], position=10.0, speed=0.0),
    )
    waiting_vehicle = Vehicle(lane=lanes[1], position=5.0, round=1)
    waiting_vehicle.trigger_respawn(1)
    waiting_player = Player(controller=waiting_controller, vehicle=waiting_vehicle)

    game = make_game(lanes, [occupied_player, waiting_player], modules)
    run_game_tick_for_test(game)

    assert waiting_player.vehicle.active
    assert waiting_player.vehicle.lane == lanes[0]
    assert waiting_player.vehicle.position == 0.0
    assert waiting_player.vehicle.round == 1


def test_respawn_stays_inactive_when_single_lane_is_occupied_on_first_module():
    """With one lane in module 0 and that lane occupied, respawn must not happen."""
    lane = Lane()
    modules = make_track_modules([lane], [[50.0]], lane_change_allowed=False)

    blocker_controller = PlayerController()
    waiting_controller = PlayerController()
    blocker = Player(
        controller=blocker_controller, vehicle=Vehicle(lane=lane, position=10.0)
    )

    waiting_vehicle = Vehicle(lane=lane, position=0.0)
    waiting_vehicle.trigger_respawn(1)
    waiting = Player(controller=waiting_controller, vehicle=waiting_vehicle)
    game = make_game([lane], [blocker, waiting], modules)

    run_game_tick_for_test(game)

    assert not waiting.vehicle.active
    assert waiting.vehicle.respawn_ticks == 0
    assert waiting.vehicle.lane == lane


def test_respawn_falls_back_to_least_occupied_module_when_preferred_is_blocked():
    """If preferred module is full, respawn should move to the least occupied module."""
    lanes = [Lane()]
    modules = make_track_modules(lanes, [[50.0], [50.0]], lane_change_allowed=False)

    blocker_controller = PlayerController()
    waiting_controller = PlayerController()

    blocker = Player(
        controller=blocker_controller, vehicle=Vehicle(lane=lanes[0], position=10.0)
    )
    waiting_vehicle = Vehicle(lane=lanes[0], position=0.0)
    waiting_vehicle.set_respawn_module_index(0)
    waiting_vehicle.trigger_respawn(1)
    waiting = Player(controller=waiting_controller, vehicle=waiting_vehicle)

    game = make_game(lanes, [blocker, waiting], modules)

    run_game_tick_for_test(game)

    assert waiting.vehicle.active
    assert waiting.vehicle.respawn_ticks == 0
    assert waiting.vehicle.position == 50.0
    assert waiting.vehicle.lane == lanes[0]


def test_respawn_from_loop_module_uses_previous_module_start():
    """Falling in a lane-change-enabled module should respawn one module earlier."""
    lane = Lane()
    modules = [
        TrackModule(
            track_type=TrackType.STRAIGHT,
            part_length=50.0,
            lines=[
                Line(
                    DrivingProfile(lane_change_allowed=False),
                    lane,
                    50.0,
                )
            ],
        ),
        TrackModule(
            track_type=TrackType.STRAIGHT,
            part_length=50.0,
            lines=[
                Line(
                    DrivingProfile(lane_change_allowed=False),
                    lane,
                    50.0,
                )
            ],
        ),
        TrackModule(
            track_type=TrackType.LOOPING,
            part_length=50.0,
            lines=[
                Line(
                    DrivingProfile(lane_change_allowed=True),
                    lane,
                    50.0,
                )
            ],
        ),
        TrackModule(
            track_type=TrackType.STRAIGHT,
            part_length=50.0,
            lines=[
                Line(
                    DrivingProfile(lane_change_allowed=False),
                    lane,
                    50.0,
                )
            ],
        ),
    ]

    controller = PlayerController()
    player_vehicle = Vehicle(lane=lane, position=120.0, speed=0.0)
    player = Player(controller=controller, vehicle=player_vehicle)
    game = make_game([lane], [player], modules, settings=Settings(respawn_ticks=1))

    # Trigger fall while in module index 2 (the looping module).
    fall_fn = cast(Callable[[Player, str], None], getattr(game, "_Game__fall_player"))
    fall_fn(player, "test")

    run_game_tick_for_test(game)

    assert player.vehicle.active
    # Module index 1 starts at global lane position 50.
    assert player.vehicle.position == pytest.approx(50.0)
    assert player.vehicle.lane == lane
    assert player.vehicle.speed == 0.0
    assert player.vehicle.acceleration == 0.0


def test_forward_press_mapping_to_acceleration():
    """Test the mapping of forward_press to acceleration."""
    # Test values below the minimum threshold
    assert Game.map_forward_press_to_acceleration(0) == 0.0
    assert Game.map_forward_press_to_acceleration(41999) == 0.0

    # Test values at the minimum threshold
    assert Game.map_forward_press_to_acceleration(42000) == 0.0

    # Test values between the minimum and maximum thresholds
    assert Game.map_forward_press_to_acceleration(53768) == 50  # middle value

    # Test values at the maximum threshold
    assert Game.map_forward_press_to_acceleration(65536) == 100.0
