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
    lane = Lane()
    vehicle = Vehicle(lane=lane, position=48)

    vehicle.update_position(delta_position=5, lane_length=50)

    assert vehicle.position == 3
    assert vehicle.round == 1


def test_track_module_position_conversion_between_lanes():
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

    run_game_tick_for_test(game)
    assert vehicle.lane == middle_lane
    assert vehicle.position == 25

    run_game_tick_for_test(game)
    assert vehicle.lane == next_lane
    assert vehicle.position == 30

    run_game_tick_for_test(game)
    assert vehicle.lane == right_lane
    assert vehicle.position == 35

    # First lane change done. Release trigger so the next press is a rising edge.
    controller.update_input("adc_1", 0.0)
    run_game_tick_for_test(game)
    assert vehicle.lane == right_lane
    assert vehicle.position == 35

    # Trigger again from rightmost lane. This should now move left.
    controller.update_input("adc_1", 1.0)
    run_game_tick_for_test(game)
    assert vehicle.lane == right_lane
    assert vehicle.position == 35

    run_game_tick_for_test(game)
    assert vehicle.lane == next_lane
    assert vehicle.position == 30

    run_game_tick_for_test(game)
    assert vehicle.lane == middle_lane
    assert vehicle.position == 25

    run_game_tick_for_test(game)
    assert vehicle.lane == left_lane
    assert vehicle.position == 20
