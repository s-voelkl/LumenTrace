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
    settings = Settings(max_speed=max_speed, respawn_ticks=200.0, lane_change_ticks=25.0, friction_percent=0.02, 
        acceleration_multiplier=0.015, special_1_threshold=0.5)
    assert settings.max_speed == max_speed
    assert settings.respawn_ticks == 200.0
    assert settings.lane_change_ticks == 25.0
    assert settings.friction_percent == 0.02
    assert settings.acceleration_multiplier == 0.015
    assert settings.special_1_threshold == 0.5
    
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


# TODO:
# basic acceleration, speed, position and round test for vehicle.
# e.g. set speed to 10, apply friction, check if speed is reduced by 2% (0.02) to 9.8.
# e.g. set speed to 10, acceleration to 100, apply update_speed with max_speed 100 and acceleration_multiplier 0.015.
# make one round for the vehicle passing the vehicle through one round of the track
# ...

# TODO: lane change tests:
# - lane change from left to right with only to lanes. 25 ticks needed for the whole operation.
# - lane change from right to left with only to lanes. 25 ticks
# - lane change from left to right with three lanes. 25 + 25 ticks
# - lane change from right to left with three lanes. 25 + 25 ticks
# - lane change from left to right with four lanes. 25 + 25 + 25 ticks

# TODO: collision detection tests:
# - no collision in bounds for speed and acceleration. test this on two track modules with different limits.
# - collision when speed not in bounds or acceleration not in bounds. the vehicle.active == True, vehicle.respawn_ticks == settings.respawn_ticks.
# - collision when crossing lane gap. example: 3 lanes. first track module with 3 lanes, 
# second track module with 2 lanes 
# (missing lane in the middle). vehicle on first track module is on lane 2 (middle), 
# with max position on this line (e.g. 50). with speed > 0, the vehicle would go on on lane 2
# (middle) of the second track module, which does not exist. this should be detected as a 
# collision and cause a fall.
# - collision with another player. example: one line, first player at position 0, 
# second player at position 20. when first player moves with speed > 0, it would collide
# with the second player. first player should not fall, second player should fall. 
# check attributes vehicle.active and vehicle.respawn_ticks.
# - respawn vehicle on one track without other players. should place the vehicle
# on vehicle.position==0, vehicle.active==True, vehicle.lane==<lane>, vehicle.respawn_ticks==0, and vehicle.round==<round>.
# - respawn vehicle. with two track modules and two lanes on it. first player exists on first lane, second player is respawned at second lane.
# - respawn vehicle. with two track modules and two lanes on it. first player exists on second lane, second player is respawned at first lane.
# - respawn vehicle. with on track module and one lane. first player exists on this lane, second player attempts to respawn.
# second player should not respawn, because the lane is occupied. 
# - respawn vehicle. with two track module and one lane. first player exists on the first track module, 
# second player attempts to respawn on first track module. second player should not respawn, 
# because the lane is occupied. before the second tick, the first player is moved to the second
# track module. in the second tick, the second player should respawn, because the lane on the 
# first track module is now unoccupied.
