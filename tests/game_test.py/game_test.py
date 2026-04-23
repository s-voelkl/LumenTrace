# testing the game class
from collections.abc import Callable
from typing import cast

from src.controller.player_controller import PlayerController
from src.controller.signal_receiver_mock import SignalReceiverMock
from src.game import *
from src.game.lane import Lane
from src.game.track_module import TrackType

# test for basic game setup


def run_game_tick_for_test(game: Game) -> None:
    """Execute one internal game tick for deterministic unit tests.

    This indirection avoids direct private-attribute access warnings in static analysis.
    """
    tick_fn = cast(Callable[[], None], getattr(game, "_Game__game_loop"))
    tick_fn()

def test_game_setup():
    """Validate baseline construction and default values of core game objects."""
    # player
    player_controller_1 = PlayerController()
    assert player_controller_1.forward_press == 0
    assert player_controller_1.controller_id == 1
    
    # lanes
    lane_1 = Lane()
    assert lane_1.lane_id == 0
    lane_2 = Lane()
    assert lane_2.lane_id == 1
    
    vehicle_1 = Vehicle(lane=lane_1)
    assert vehicle_1.speed == 0
    assert vehicle_1.position == 0
    assert vehicle_1.round == 0
    assert vehicle_1.acceleration == 0
    assert vehicle_1.lane == lane_1
    assert vehicle_1.lane.lane_id == lane_1.lane_id
    assert vehicle_1.vehicle_length == 20
    
    player_1 = Player(
        controller=player_controller_1,
        vehicle=vehicle_1
    )
    assert player_1.controller == player_controller_1
    assert player_1.vehicle == vehicle_1
    assert player_1.name == "Player 1"
    
    # signal receiver
    signal_receiver_1 = SignalReceiverMock(controllers=[player_controller_1])
    assert signal_receiver_1.controllers == [player_controller_1]   
     
    # track
    max_speed = 101
    driving_profile_1 = DrivingProfile(max_speed=max_speed, min_speed=-max_speed)
    assert driving_profile_1.lane_change_allowed == False
    assert driving_profile_1.min_speed == -max_speed
    assert driving_profile_1.max_speed == max_speed
    assert driving_profile_1.max_acceleration == 10
    assert driving_profile_1.min_acceleration == -10
    
    line_1 = Line(driving_profile=driving_profile_1, lane=lane_1)
    assert line_1.lane == lane_1
    assert line_1.length == 0
    assert line_1.driving_profile == driving_profile_1
    
    driving_profile_2 = DrivingProfile(max_speed=max_speed * 0.9)
    line_2_length = 50
    line_2 = Line(driving_profile=driving_profile_2, line_length=line_2_length, lane=lane_2)
    assert line_2.lane == lane_2
    assert line_2.length == line_2_length
    
    track_module_1_length = 50
    track_module_1 = TrackModule(part_length=track_module_1_length, lines=[line_1, line_2], track_type=TrackType.STRAIGHT)
    assert track_module_1.length == track_module_1_length
    assert track_module_1.lines == [line_1, line_2]
    assert track_module_1.track_type == TrackType.STRAIGHT
    assert track_module_1.get_line_length_for_lane(lane_1) == line_1.length
    assert track_module_1.get_line_length_for_lane(lane_2) == line_2.length
    
    # game
    settings = Settings(max_speed=max_speed)
    assert settings.max_speed == max_speed
    assert settings.respawn_time == 3000.0
    assert settings.friction_percent == 0.02
    assert settings.acceleration_multiplier == 0.015
    
    game: Game = Game(
        players=[player_1],
        settings=settings,
        track_modules=[track_module_1],
        signal_receiver=signal_receiver_1,
        lanes=[lane_1, lane_2]
    )
    assert game.settings == settings
    assert game.players == [player_1]
    assert game.track_modules == [track_module_1]
    assert game.signal_receiver == signal_receiver_1
    assert game.length == track_module_1_length
    assert game.lanes == [lane_1, lane_2]


def test_vehicle_position_wraparound():
    """Ensure position wraps at lane length and increments lap counter."""
    lane = Lane()
    vehicle = Vehicle(lane=lane, position=48)

    vehicle.update_position(delta_position=5, lane_length=50)

    assert vehicle.position == 3
    assert vehicle.round == 1


def test_track_module_position_conversion_between_lanes():
    """Verify proportional position conversion across lanes of different lengths."""
    left_lane = Lane()
    right_lane = Lane()

    track_module = TrackModule(
        track_type=TrackType.INTERSECTION,
        part_length=50,
        lines=[
            Line(driving_profile=DrivingProfile(lane_change_allowed=True), lane=left_lane, line_length=40),
            Line(driving_profile=DrivingProfile(lane_change_allowed=True), lane=right_lane, line_length=60),
        ],
    )

    assert track_module.convert_position_between_lanes(left_lane, right_lane, 20) == 30


def test_game_lane_change_without_middle_lane(monkeypatch):
    """Confirm lane change works directly between two lanes without an intermediate lane."""
    left_lane = Lane()
    right_lane = Lane()
    controller = PlayerController()
    vehicle = Vehicle(lane=left_lane, position=20)
    player = Player(controller=controller, vehicle=vehicle)
    signal_receiver = SignalReceiverMock(controllers=[controller])

    track_module = TrackModule(
        track_type=TrackType.INTERSECTION,
        part_length=50,
        lines=[
            Line(driving_profile=DrivingProfile(lane_change_allowed=True), lane=left_lane, line_length=40),
            Line(driving_profile=DrivingProfile(lane_change_allowed=True), lane=right_lane, line_length=60),
        ],
    )

    game = Game(
        players=[player],
        settings=Settings(max_speed=101, special_1_threshold=0.5, lane_change_time=500.0),
        track_modules=[track_module],
        signal_receiver=signal_receiver,
        lanes=[left_lane, right_lane],
    )

    controller.update_input("adc_1", 1.0)
    times = iter([1000.0, 1600.0])
    monkeypatch.setattr("src.game.game.time.perf_counter", lambda: next(times))

    run_game_tick_for_test(game)
    assert vehicle.lane == left_lane
    assert vehicle.position == 20

    run_game_tick_for_test(game)
    assert vehicle.lane == right_lane
    assert vehicle.position == 30


def test_game_lane_change_blocked_when_profile_disallows(monkeypatch):
    """Confirm lane change is blocked when source line profile disallows it."""
    left_lane = Lane()
    right_lane = Lane()
    controller = PlayerController()
    vehicle = Vehicle(lane=left_lane, position=20)
    player = Player(controller=controller, vehicle=vehicle)
    signal_receiver = SignalReceiverMock(controllers=[controller])

    track_module = TrackModule(
        track_type=TrackType.INTERSECTION,
        part_length=50,
        lines=[
            Line(driving_profile=DrivingProfile(lane_change_allowed=False), lane=left_lane, line_length=40),
            Line(driving_profile=DrivingProfile(lane_change_allowed=True), lane=right_lane, line_length=60),
        ],
    )

    game = Game(
        players=[player],
        settings=Settings(max_speed=101, special_1_threshold=0.5, lane_change_time=500.0),
        track_modules=[track_module],
        signal_receiver=signal_receiver,
        lanes=[left_lane, right_lane],
    )

    controller.update_input("adc_1", 1.0)
    times = iter([1000.0, 1600.0])
    monkeypatch.setattr("src.game.game.time.perf_counter", lambda: next(times))

    run_game_tick_for_test(game)
    assert vehicle.lane == left_lane
    assert vehicle.position == 20

    # Even after the hop duration passes, no lane-change state should have been active.
    run_game_tick_for_test(game)
    assert vehicle.lane == left_lane
    assert vehicle.position == 20


def test_game_lane_change_across_multiple_lanes(monkeypatch):
    """Start a multi-hop lane change and verify the first tick keeps initial state."""
    left_lane = Lane()
    middle_lane = Lane()
    next_lane = Lane()
    right_lane = Lane()
    controller = PlayerController()
    vehicle = Vehicle(lane=left_lane, position=20)
    player = Player(controller=controller, vehicle=vehicle)
    signal_receiver = SignalReceiverMock(controllers=[controller])

    # 4 lanes. each hop should take another 500 ms and keep the proportional position.
    track_module = TrackModule(
        track_type=TrackType.INTERSECTION,
        part_length=50,
        lines=[
            Line(driving_profile=DrivingProfile(lane_change_allowed=True), lane=left_lane, line_length=40),
            Line(driving_profile=DrivingProfile(lane_change_allowed=True), lane=middle_lane, line_length=50),
            Line(driving_profile=DrivingProfile(lane_change_allowed=True), lane=next_lane, line_length=60),
            Line(driving_profile=DrivingProfile(lane_change_allowed=True), lane=right_lane, line_length=70),
        ],
    )

    game = Game(
        players=[player],
        settings=Settings(max_speed=101, special_1_threshold=0.5, lane_change_time=500.0),
        track_modules=[track_module],
        signal_receiver=signal_receiver,
        lanes=[left_lane, middle_lane, next_lane, right_lane],
    )

    controller.update_input("adc_1", 1.0)
    times = iter([1000.0, 1500.0, 2000.0, 2500.0, 3000.0, 3500.0, 4000.0, 4500.0, 5000.0])
    monkeypatch.setattr("src.game.game.time.perf_counter", lambda: next(times))
    
    run_game_tick_for_test(game)
    assert vehicle.lane == left_lane
    assert vehicle.position == 20

def test_game_push_down_when_speed_exceeds_profile_max(monkeypatch):
    """Ensure profile speed violations trigger a fall and timed respawn at start."""
    lane = Lane()
    controller = PlayerController()
    vehicle = Vehicle(lane=lane, position=10, speed=100)
    player = Player(controller=controller, vehicle=vehicle)
    signal_receiver = SignalReceiverMock(controllers=[controller])

    track_module = TrackModule(
        track_type=TrackType.STRAIGHT,
        part_length=50,
        lines=[
            Line(
                driving_profile=DrivingProfile(max_speed=90, min_speed=-100, max_acceleration=10, min_acceleration=-10),
                lane=lane,
                line_length=50,
            ),
        ],
    )

    game = Game(
        players=[player],
        settings=Settings(max_speed=200, respawn_time=100),
        track_modules=[track_module],
        signal_receiver=signal_receiver,
        lanes=[lane],
    )

    # 1st tick: fall, 2nd tick: still waiting, 3rd tick: respawn window reached.
    times = iter([1000.0, 1050.0, 1200.0])
    monkeypatch.setattr("src.game.game.time.perf_counter", lambda: next(times))

    run_game_tick_for_test(game)
    assert vehicle.speed == 0
    assert vehicle.position == 10

    run_game_tick_for_test(game)
    assert vehicle.position == 10

    run_game_tick_for_test(game)
    assert vehicle.position == 0
    assert vehicle.round == 0


def test_game_push_down_when_acceleration_below_profile_min(monkeypatch):
    """Ensure profile acceleration violations trigger immediate fall behavior."""
    lane = Lane()
    controller = PlayerController()
    vehicle = Vehicle(lane=lane, position=5, speed=0)
    player = Player(controller=controller, vehicle=vehicle)
    signal_receiver = SignalReceiverMock(controllers=[controller])

    track_module = TrackModule(
        track_type=TrackType.STRAIGHT,
        part_length=50,
        lines=[
            Line(
                driving_profile=DrivingProfile(
                    max_speed=100,
                    min_speed=-100,
                    max_acceleration=100,
                    min_acceleration=50,
                ),
                lane=lane,
                line_length=50,
            ),
        ],
    )

    game = Game(
        players=[player],
        settings=Settings(max_speed=200, respawn_time=1000),
        track_modules=[track_module],
        signal_receiver=signal_receiver,
        lanes=[lane],
    )

    times = iter([2000.0])
    monkeypatch.setattr("src.game.game.time.perf_counter", lambda: next(times))

    run_game_tick_for_test(game)
    assert vehicle.speed == 0
    assert vehicle.position == 5


def test_game_collision_front_vehicle_falls(monkeypatch):
    """Ensure same-lane collision removes the front vehicle from active play."""
    lane = Lane()
    controller_a = PlayerController()
    controller_b = PlayerController()
    vehicle_a = Vehicle(lane=lane, position=50)
    vehicle_b = Vehicle(lane=lane, position=60)
    player_a = Player(controller=controller_a, vehicle=vehicle_a)
    player_b = Player(controller=controller_b, vehicle=vehicle_b)
    signal_receiver = SignalReceiverMock(controllers=[controller_a, controller_b])

    track_module = TrackModule(
        track_type=TrackType.STRAIGHT,
        part_length=100,
        lines=[
            Line(driving_profile=DrivingProfile(), lane=lane, line_length=100),
        ],
    )

    game = Game(
        players=[player_a, player_b],
        settings=Settings(max_speed=100, respawn_time=1000),
        track_modules=[track_module],
        signal_receiver=signal_receiver,
        lanes=[lane],
    )

    times = iter([3000.0, 4000.0])
    monkeypatch.setattr("src.game.game.time.perf_counter", lambda: next(times))

    run_game_tick_for_test(game)

    # Player B is in front (higher lap progress) and should fall.
    assert vehicle_b.speed == 0
    assert vehicle_b.position == 60
    
    # Player A should remain unaffected in this scenario.
    assert vehicle_a.speed == 0
    assert vehicle_a.position == 50
    
    run_game_tick_for_test(game)
    # After the second tick, Player B should have respawned at the start of the lane.
    assert vehicle_b.position == 0
    assert vehicle_b.round == 0
    
    # Player A should still be unaffected and remain in place.
    assert vehicle_a.speed == 0
    assert vehicle_a.position == 50 


def test_game_vehicle_falls_when_lane_ends_forward(monkeypatch):
    """Ensure forward movement across a missing lane continuation triggers a fall."""
    lane = Lane()
    controller = PlayerController()
    vehicle = Vehicle(lane=lane, position=49)
    vehicle.set_speed(100)
    player = Player(controller=controller, vehicle=vehicle)
    signal_receiver = SignalReceiverMock(controllers=[controller])

    first_module = TrackModule(
        track_type=TrackType.STRAIGHT,
        part_length=50,
        lines=[
            Line(driving_profile=DrivingProfile(max_speed=200), lane=lane, line_length=50),
        ],
    )
    second_module = TrackModule(track_type=TrackType.STRAIGHT, part_length=50, lines=[])

    game = Game(
        players=[player],
        settings=Settings(max_speed=200, respawn_time=0.02),
        track_modules=[first_module, second_module],
        signal_receiver=signal_receiver,
        lanes=[lane],
    )

    times = iter([0, 1])
    monkeypatch.setattr("src.game.game.time.perf_counter", lambda: next(times))

    run_game_tick_for_test(game)
    assert vehicle.position == 49
    assert vehicle.speed == 0
    
    run_game_tick_for_test(game)
    assert vehicle.position == 0
    assert vehicle.round == 0
    assert vehicle.speed == 0


def test_game_vehicle_falls_when_lane_ends_backward(monkeypatch):
    """Ensure backward movement across a missing lane continuation triggers a fall."""
    lane = Lane()
    controller = PlayerController()
    vehicle = Vehicle(lane=lane, position=0.2)
    vehicle.set_speed(-20)
    player = Player(controller=controller, vehicle=vehicle)
    signal_receiver = SignalReceiverMock(controllers=[controller])

    first_module = TrackModule(track_type=TrackType.STRAIGHT, part_length=50, lines=[])
    second_module = TrackModule(
        track_type=TrackType.STRAIGHT,
        part_length=50,
        lines=[
            Line(driving_profile=DrivingProfile(max_speed=200, min_speed=-200), lane=lane, line_length=40),
        ],
    )

    game = Game(
        players=[player],
        settings=Settings(max_speed=200, respawn_time=1000),
        track_modules=[first_module, second_module],
        signal_receiver=signal_receiver,
        lanes=[lane],
    )

    times = iter([5000.0, 7000.0])
    monkeypatch.setattr("src.game.game.time.perf_counter", lambda: next(times))

    run_game_tick_for_test(game)
    assert vehicle.position == 0.2
    assert vehicle.speed == 0


def test_game_respawn_uses_free_lane_at_start(monkeypatch):
    """Respawn should prefer position zero on a start-eligible unoccupied lane."""
    lane_1 = Lane()
    lane_2 = Lane()
    controller_a = PlayerController()
    controller_b = PlayerController()

    vehicle_a = Vehicle(lane=lane_1, position=0)
    vehicle_b = Vehicle(lane=lane_2, position=10, speed=100)
    player_a = Player(controller=controller_a, vehicle=vehicle_a)
    player_b = Player(controller=controller_b, vehicle=vehicle_b)
    signal_receiver = SignalReceiverMock(controllers=[controller_a, controller_b])

    track_module = TrackModule(
        track_type=TrackType.STRAIGHT,
        part_length=100,
        lines=[
            Line(driving_profile=DrivingProfile(max_speed=100), lane=lane_1, line_length=100),
            Line(driving_profile=DrivingProfile(max_speed=90), lane=lane_2, line_length=100),
        ],
    )

    game = Game(
        players=[player_a, player_b],
        settings=Settings(max_speed=200, respawn_time=100),
        track_modules=[track_module],
        signal_receiver=signal_receiver,
        lanes=[lane_1, lane_2],
    )

    times = iter([6000.0, 6200.0])
    monkeypatch.setattr("src.game.game.time.perf_counter", lambda: next(times))

    # Player B falls due to max speed violation in lane 2.
    run_game_tick_for_test(game)
    assert vehicle_b.position == 10

    # Respawn should place Player B in lane 2 at position 0 (lane 1 is occupied at start).
    run_game_tick_for_test(game)
    assert vehicle_b.lane == lane_2
    assert vehicle_b.position == 0


def test_game_respawn_fallback_uses_first_safe_position(monkeypatch):
    """Respawn should fallback to the first safe buffered position when start is blocked."""
    lane = Lane()
    controller_a = PlayerController()
    controller_b = PlayerController()

    vehicle_a = Vehicle(lane=lane, position=0)
    vehicle_b = Vehicle(lane=lane, position=10, speed=100)
    player_a = Player(controller=controller_a, vehicle=vehicle_a)
    player_b = Player(controller=controller_b, vehicle=vehicle_b)
    signal_receiver = SignalReceiverMock(controllers=[controller_a, controller_b])

    track_module = TrackModule(
        track_type=TrackType.STRAIGHT,
        part_length=100,
        lines=[
            Line(
                driving_profile=DrivingProfile(max_speed=100, max_acceleration=0.5),
                lane=lane,
                line_length=100,
            ),
        ],
    )

    game = Game(
        players=[player_a, player_b],
        settings=Settings(max_speed=200, respawn_time=100),
        track_modules=[track_module],
        signal_receiver=signal_receiver,
        lanes=[lane],
    )

    # Force player B to violate profile in the first tick.
    controller_b.update_input("adc_0", 1.0)

    times = iter([7000.0, 7200.0])
    monkeypatch.setattr("src.game.game.time.perf_counter", lambda: next(times))

    run_game_tick_for_test(game)
    assert vehicle_b.position == 10

    run_game_tick_for_test(game)
    # Position 0 is occupied, so fallback should place the vehicle at a safe distance.
    assert vehicle_b.position >= vehicle_b.vehicle_length * 2
