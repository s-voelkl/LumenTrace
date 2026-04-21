from src.controller.signal_receiver_mock import SignalReceiverMock
from src.game.lane import Lane
from src.logger.multi_logger import get_logger
from src.game.game import Game
from src.controller.player_controller import PlayerController
from src.game.player import Player
from src.game.vehicle import Vehicle
from src.game.track_module import TrackModule, TrackType
from src.game.line import Line
from src.game.driving_profile import DrivingProfile
from src.game.settings import *

logger = get_logger()
settings = get_settings(max_speed=100.0)

def simple_game_setup():
    # lanes
    lane_1 = Lane()
    lane_2 = Lane()

    # players
    player_1 = Player(
        controller=PlayerController(),
        vehicle=Vehicle(lane=lane_1)
    )
    player_2 = Player(
        controller=PlayerController(),
        vehicle=Vehicle(lane=lane_2)
    )
    
    # signal receiver
    signal_receiver = SignalReceiverMock(controllers=[player_1.controller, player_2.controller])
    
    # track with 5 modules and different driving profiles
    track_modules: list[TrackModule] = [
        TrackModule(
            track_type=TrackType.STRAIGHT,
            length=50,
            lines=[
                Line(
                    driving_profile=DrivingProfile(max_speed=100),
                    lane=lane_1,
                    length=50,
                ),
                Line(
                    driving_profile=DrivingProfile(max_speed=90),
                    lane=lane_2,
                    length=50
                ),
            ],
        ),
        TrackModule(
            track_type=TrackType.CURVE_LEFT,
            length=30,
            lines=[
                Line(
                    driving_profile=DrivingProfile(max_speed=65, max_acceleration=7),
                    lane=lane_1,
                    length=28,
                ),
                Line(
                    driving_profile=DrivingProfile(max_speed=75, max_acceleration=8),
                    lane=lane_2,
                    length=32
                ),
            ],
        ),
        TrackModule(
            track_type=TrackType.CURVE_RIGHT,
            length=50,
            lines=[
                Line(
                    driving_profile=DrivingProfile(max_speed=85, max_acceleration=9),
                    lane=lane_1,
                    length=55,
                ),
                Line(
                    driving_profile=DrivingProfile(max_speed=75, max_acceleration=8),
                    lane=lane_2,
                    length=45
                ),
            ],
        ),
        TrackModule(
            track_type=TrackType.LOOPING,
            length=80,
            lines=[
                Line(
                    driving_profile=DrivingProfile(min_speed=70),
                    lane=lane_1,
                    length=80,
                ),
                Line(
                    driving_profile=DrivingProfile(min_speed=70),
                    lane=lane_2,
                    length=80
                ),
            ],
        )
    ]
    
    # game
    game = Game(
        players=[player_1, player_2],
        track_modules=track_modules,
        settings=settings, # type: ignore
        signal_receiver=signal_receiver,
        lanes=[lane_1, lane_2]
    )
    
    # start game
    game.start_game(fetch_interval_s=1, display_interval_s=1, game_tick_interval_s=2)
    

def main():
    simple_game_setup()

if __name__ == "__main__":
    print("Running on dev pc.")
    main()
    