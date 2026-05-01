from src.controller.signal_receiver import SignalReceiver
from src.controller.player_controller import PlayerController
from src.logger.multi_logger import get_logger
import time

logger = get_logger()

def main():
    logger.log("Raspberry Pi 4: Main script running.")
    player_controller_1 = PlayerController()
    signal_receiver = SignalReceiver(controllers=[player_controller_1])
    
    while True:
        signal_receiver.receive_signal()
        time.sleep(0.001)  # Sleep for a short time to prevent high CPU usage

if __name__ == "__main__":
    main()
    
