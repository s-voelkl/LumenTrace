from src.controller.signal_receiver import SignalReceiver
from src.controller.player_controller import PlayerController
from src.logger.multi_logger import get_logger
logger = get_logger()



def main():
    logger.log("Raspberry Pi 3: Main script running.")
    player_controller_1 = PlayerController()
    signal_receiver = SignalReceiver(controllers=[player_controller_1])
    
    while True:
        signal_receiver.receive_signal()


if __name__ == "__main__":
    main()
    
