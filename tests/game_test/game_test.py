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


def set_controller_input(controller: PlayerController, *, forward_press: float = 0.0, special_1: float = 0.0) -> None:
    """Set controller values through production input-mapping API."""
    controller.update_input("adc_0", forward_press)
    controller.update_input("adc_1", special_1)


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
                part_length=max([length for length in lane_lengths if length is not None], default=0.0),
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
            lane_change_ticks=2,
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
    """Run a deterministic number of internal ticks for scenario tests."""
    for _ in range(tick_count):
        run_game_tick_for_test(game)


def assert_lane_after_exact_ticks(
    game: Game,
    player: Player,
    expected_lane: Lane,
    *,
    ticks_until_completion: int,
) -> None:
    """Assert lane-change timing boundaries exactly.

    This helper validates that the lane does not switch one tick too early and does
    switch on the exact completion tick. It is useful for review because it clearly
    verifies edge behavior around off-by-one timing bugs.
    """
    if ticks_until_completion > 1:
        run_ticks(game, ticks_until_completion - 1)
        assert player.vehicle.lane != expected_lane

    run_ticks(game, 1)
    assert player.vehicle.lane == expected_lane


def test_vehicle_physics_basics_friction_speed_position_and_round():
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


def test_lane_change_is_timed_multi_hop_and_reaches_final_lane():
    """Lane change from leftmost to rightmost should proceed in timed adjacent hops."""
    lanes = [Lane(), Lane(), Lane()]
    modules = make_track_modules(lanes, [[60.0, 60.0, 60.0]], lane_change_allowed=True)

    controller = PlayerController()
    set_controller_input(controller, special_1=1.0)
    player = Player(controller=controller, vehicle=Vehicle(lane=lanes[0], position=10.0))
    game = make_game(lanes, [player], modules)

    run_game_tick_for_test(game)
    run_game_tick_for_test(game)
    assert player.vehicle.lane == lanes[1]

    run_game_tick_for_test(game)
    run_game_tick_for_test(game)
    assert player.vehicle.lane == lanes[2]
    assert player.vehicle.line_change_ticks == 0
    assert player.vehicle.line_change_target is None


def test_lane_change_two_lanes_left_to_right_takes_exactly_25_ticks():
    """Lane change from leftmost to rightmost lane in 2-lane setup must take 25 ticks."""
    lanes = [Lane(), Lane()]
    modules = make_track_modules(lanes, [[100.0, 100.0]], lane_change_allowed=True)
    settings = Settings(lane_change_ticks=25)

    controller = PlayerController()
    set_controller_input(controller, special_1=1.0)
    player = Player(controller=controller, vehicle=Vehicle(lane=lanes[0], position=10.0))
    game = make_game(lanes, [player], modules, settings=settings)

    assert_lane_after_exact_ticks(game, player, lanes[1], ticks_until_completion=25)


def test_lane_change_two_lanes_right_to_left_takes_exactly_25_ticks():
    """Lane change from rightmost to leftmost lane in 2-lane setup must take 25 ticks."""
    lanes = [Lane(), Lane()]
    modules = make_track_modules(lanes, [[100.0, 100.0]], lane_change_allowed=True)
    settings = Settings(lane_change_ticks=25)

    controller = PlayerController()
    set_controller_input(controller, special_1=1.0)
    player = Player(controller=controller, vehicle=Vehicle(lane=lanes[1], position=10.0))
    game = make_game(lanes, [player], modules, settings=settings)

    assert_lane_after_exact_ticks(game, player, lanes[0], ticks_until_completion=25)


def test_lane_change_three_lanes_left_to_right_takes_50_ticks_total():
    """Three-lane full crossing should use two adjacent hops, each with 25 ticks."""
    lanes = [Lane(), Lane(), Lane()]
    modules = make_track_modules(lanes, [[100.0, 100.0, 100.0]], lane_change_allowed=True)
    settings = Settings(lane_change_ticks=25)

    controller = PlayerController()
    set_controller_input(controller, special_1=1.0)
    player = Player(controller=controller, vehicle=Vehicle(lane=lanes[0], position=10.0))
    game = make_game(lanes, [player], modules, settings=settings)

    # First hop reaches middle lane after exactly 25 ticks.
    assert_lane_after_exact_ticks(game, player, lanes[1], ticks_until_completion=25)
    # Second hop reaches right lane after another 25 ticks.
    assert_lane_after_exact_ticks(game, player, lanes[2], ticks_until_completion=25)


def test_lane_change_three_lanes_right_to_left_takes_50_ticks_total():
    """Reverse direction in three lanes should mirror timing and adjacency."""
    lanes = [Lane(), Lane(), Lane()]
    modules = make_track_modules(lanes, [[100.0, 100.0, 100.0]], lane_change_allowed=True)
    settings = Settings(lane_change_ticks=25)

    controller = PlayerController()
    set_controller_input(controller, special_1=1.0)
    player = Player(controller=controller, vehicle=Vehicle(lane=lanes[2], position=10.0))
    game = make_game(lanes, [player], modules, settings=settings)

    assert_lane_after_exact_ticks(game, player, lanes[1], ticks_until_completion=25)
    assert_lane_after_exact_ticks(game, player, lanes[0], ticks_until_completion=25)


def test_lane_change_four_lanes_left_to_right_takes_75_ticks_total():
    """Four-lane full crossing should perform three timed adjacent hops (3 * 25)."""
    lanes = [Lane(), Lane(), Lane(), Lane()]
    modules = make_track_modules(lanes, [[100.0, 100.0, 100.0, 100.0]], lane_change_allowed=True)
    settings = Settings(lane_change_ticks=25)

    controller = PlayerController()
    set_controller_input(controller, special_1=1.0)
    player = Player(controller=controller, vehicle=Vehicle(lane=lanes[0], position=10.0))
    game = make_game(lanes, [player], modules, settings=settings)

    assert_lane_after_exact_ticks(game, player, lanes[1], ticks_until_completion=25)
    assert_lane_after_exact_ticks(game, player, lanes[2], ticks_until_completion=25)
    assert_lane_after_exact_ticks(game, player, lanes[3], ticks_until_completion=25)


def test_lane_change_requires_lane_change_allowed_profile():
    """Lane change must be blocked on lines that disallow lane changes."""
    lanes = [Lane(), Lane()]
    modules = make_track_modules(lanes, [[50.0, 50.0]], lane_change_allowed=False)

    controller = PlayerController()
    set_controller_input(controller, special_1=1.0)
    player = Player(controller=controller, vehicle=Vehicle(lane=lanes[0], position=10.0))
    game = make_game(lanes, [player], modules)

    for _ in range(5):
        run_game_tick_for_test(game)

    assert player.vehicle.lane == lanes[0]
    assert player.vehicle.line_change_ticks == 0
    assert player.vehicle.line_change_target is None


def test_lane_change_converts_module_position_proportionally():
    """Lane hop should preserve module progress by proportional conversion."""
    lanes = [Lane(), Lane()]
    modules = make_track_modules(lanes, [[40.0, 80.0]], lane_change_allowed=True)

    controller = PlayerController()
    set_controller_input(controller, special_1=1.0)
    settings = Settings(lane_change_ticks=1)
    player = Player(controller=controller, vehicle=Vehicle(lane=lanes[0], position=20.0))
    game = make_game(lanes, [player], modules, settings=settings)

    run_game_tick_for_test(game)

    assert player.vehicle.lane == lanes[1]
    assert player.vehicle.position == pytest.approx(40.0)


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
    assert player.vehicle.lane is None


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
    # The game copies forward_press directly into vehicle.acceleration before validation.
    set_controller_input(controller, forward_press=5.0)
    player = Player(controller=controller, vehicle=Vehicle(lane=lanes[0], speed=1.0))
    settings = Settings(respawn_ticks=9)
    game = make_game(lanes, [player], modules, settings=settings)

    run_game_tick_for_test(game)

    assert not player.vehicle.active
    assert player.vehicle.respawn_ticks == settings.respawn_ticks
    assert player.vehicle.lane is None


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
        TrackModule(track_type=TrackType.STRAIGHT, part_length=50.0, lines=[Line(low_limit_profile, lane, 50.0)]),
        TrackModule(track_type=TrackType.STRAIGHT, part_length=50.0, lines=[Line(high_limit_profile, lane, 50.0)]),
    ]

    controller = PlayerController()
    set_controller_input(controller, forward_press=0.0)
    player = Player(controller=controller, vehicle=Vehicle(lane=lane, position=49.0, speed=4.0))
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
    assert player.vehicle.lane is None


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
    assert player.vehicle.lane is None


def test_collision_makes_front_vehicle_fall():
    """Within crash distance, front vehicle on same lane must fall."""
    lanes = [Lane()]
    modules = make_track_modules(lanes, [[100.0]], lane_change_allowed=False)

    rear_controller = PlayerController()
    front_controller = PlayerController()
    set_controller_input(rear_controller, forward_press=0.0)
    set_controller_input(front_controller, forward_press=0.0)

    rear_player = Player(controller=rear_controller, vehicle=Vehicle(lane=lanes[0], position=0.0, speed=0.0))
    front_player = Player(controller=front_controller, vehicle=Vehicle(lane=lanes[0], position=15.0, speed=0.0))
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

    rear_player = Player(controller=rear_controller, vehicle=Vehicle(lane=lanes[0], position=0.0, speed=1.0))
    front_player = Player(controller=front_controller, vehicle=Vehicle(lane=lanes[0], position=20.0, speed=0.0))
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
    modules = make_track_modules(lanes, [[50.0, 50.0], [50.0, 50.0]], lane_change_allowed=False)

    occupied_controller = PlayerController()
    falling_controller = PlayerController()
    occupied_player = Player(
        controller=occupied_controller,
        vehicle=Vehicle(lane=lanes[0], position=10.0, speed=0.0),
    )

    respawning_vehicle = Vehicle(lane=lanes[0], position=5.0, round=3)
    respawning_vehicle.trigger_respawn(1)
    respawning_player = Player(controller=falling_controller, vehicle=respawning_vehicle)

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
    modules = make_track_modules(lanes, [[50.0, 50.0], [50.0, 50.0]], lane_change_allowed=False)

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
    blocker = Player(controller=blocker_controller, vehicle=Vehicle(lane=lane, position=10.0))

    waiting_vehicle = Vehicle(lane=lane, position=0.0)
    waiting_vehicle.trigger_respawn(1)
    waiting = Player(controller=waiting_controller, vehicle=waiting_vehicle)
    game = make_game([lane], [blocker, waiting], modules)

    run_game_tick_for_test(game)

    assert not waiting.vehicle.active
    assert waiting.vehicle.respawn_ticks == 0
    assert waiting.vehicle.lane is None


def test_respawn_retries_until_first_module_lane_becomes_free():
    """Respawn must keep retrying each tick when spawn lane is still occupied."""
    lanes = [Lane()]
    modules = make_track_modules(lanes, [[50.0], [50.0]], lane_change_allowed=False)

    blocker_controller = PlayerController()
    waiting_controller = PlayerController()

    blocker = Player(controller=blocker_controller, vehicle=Vehicle(lane=lanes[0], position=10.0))
    waiting_vehicle = Vehicle(lane=lanes[0], position=0.0)
    waiting_vehicle.trigger_respawn(1)
    waiting = Player(controller=waiting_controller, vehicle=waiting_vehicle)

    game = make_game(lanes, [blocker, waiting], modules)

    run_game_tick_for_test(game)
    assert not waiting.vehicle.active
    assert waiting.vehicle.respawn_ticks == 0

    blocker.vehicle.set_position(60.0)
    run_game_tick_for_test(game)
    assert waiting.vehicle.active
    assert waiting.vehicle.position == 0.0
    assert waiting.vehicle.lane == lanes[0]

def test_forward_press_mapping_to_acceleration():
    """Test the mapping of forward_press to acceleration."""
    # Test values below the minimum threshold
    assert Game.map_forward_press_to_acceleration(0) == 0.
    assert Game.map_forward_press_to_acceleration(41999) == 0.
    
    # Test values at the minimum threshold
    assert Game.map_forward_press_to_acceleration(42000) == 0.
    
    # Test values between the minimum and maximum thresholds
    assert Game.map_forward_press_to_acceleration(53768) == 50 # middle value
    
    # Test values at the maximum threshold
    assert Game.map_forward_press_to_acceleration(65536) == 100.
