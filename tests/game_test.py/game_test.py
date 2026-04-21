# testing the game class
from src.controller.player_controller import PlayerController
from src.controller.signal_receiver_mock import SignalReceiverMock
from src.game import *
from src.game.lane import Lane

# test for basic game setup

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
    max_speed = 100
    driving_profile_1 = DrivingProfile(max_speed=max_speed)
    assert driving_profile_1.lane_change_allowed == False
    assert driving_profile_1.min_speed == -100
    assert driving_profile_1.max_speed == max_speed
    assert driving_profile_1.max_acceleration == 10
    assert driving_profile_1.min_acceleration == -10
    
    line_1 = Line(driving_profile=driving_profile_1, lane=lane_1)
    assert line_1.lane == lane_1
    assert line_1.length == 0
    assert line_1.driving_profile == driving_profile_1
    
    driving_profile_2 = DrivingProfile(max_speed=max_speed * 0.9)
    line_2_length = 50
    line_2 = Line(driving_profile=driving_profile_2, length=line_2_length, lane=lane_2)
    assert line_2.lane == lane_2
    assert line_2.length == line_2_length
    
    track_module_1_length = 50
    track_module_1 = TrackModule(length=track_module_1_length, lines=[line_1, line_2])
    assert track_module_1.length == track_module_1_length
    assert track_module_1.lines == [line_1, line_2]
    
    # game
    settings = Settings(max_speed=max_speed)
    assert settings.max_speed == max_speed
    
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