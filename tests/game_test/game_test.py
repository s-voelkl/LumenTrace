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
            special_1_threshold=0.5,
            lane_change_ticks=2,
        )

    return Game(
        players=players,
        settings=settings,
        track_modules=track_modules,
        signal_receiver=SignalReceiverMock([player.controller for player in players]),
        lanes=lanes,
    )


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
    settings = Settings(lane_change_ticks=1, special_1_threshold=0.5)
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
