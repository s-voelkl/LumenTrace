from src.controller.signal_receiver_mock import SignalReceiverMock
from src.logger.multi_logger import get_logger
from src.game.game import Game
from src.controller.player_controller import PlayerController
from src.game.player import Player
from src.game.vehicle import Vehicle
from src.game.track_module import TrackModule
from src.game.line import Line
from src.game.driving_profile import DrivingProfile
from src.game.settings import Settings

logger = get_logger()

def main():
    # player
    player_controller_1 = PlayerController()
    vehicle_1 = Vehicle()
    player_1 = Player(
        controller=player_controller_1,
        vehicle=vehicle_1
    )
    
    # signal receiver
    signal_receiver_1 = SignalReceiverMock(controllers=[player_controller_1])
    
    # track
    max_speed = 100
    line_1 = Line(driving_profile=DrivingProfile(max_speed=max_speed), length=50, lane_id=0)
    line_2 = Line(driving_profile=DrivingProfile(max_speed=max_speed * 0.9), length=45, lane_id=1)
    track_module_1 = TrackModule(length=100, lines=[line_1, line_2])
    
    # game
    settings = Settings(max_speed=max_speed)
    game: Game = Game(
        players=[player_1],
        settings=settings,
        track_modules=[track_module_1],
        signal_receiver=signal_receiver_1
    )
    
    # start game
    game.start_game()
    game.log()

if __name__ == "__main__":
    print("Running on dev pc.")
    main()
    