from src.controller.signal_receiver import SignalReceiver
from src.controller.player_controller import PlayerController
from src.logger.multi_logger import get_logger
from src.display.display import Display
from src.display.display_manager import DisplayManager
import time

logger = get_logger()

def main():
    logger.log("Raspberry Pi 4: Main script running.")
    player_controller_1 = PlayerController()
    player_controller_2 = PlayerController()
    signal_receiver = SignalReceiver(controllers=[player_controller_1, player_controller_2])
    
    # Optional: Configure the Display and DisplayManager
    display = Display({}, []) # Provide physical and virtual strips here when available
    # For now, it stays empty so the logic runs without crashing.
    # We would pass this Display to the Game initialization.
    
    logger.log("Setup of SignalReceiver and PlayerController complete. Entering main loop.")
    
    while True:
        logger.log("Main loop iteration: Receiving signals...")
        signal_receiver.receive_signal()
        time.sleep(1.20)  # Sleep for a short time to prevent high CPU usage

if __name__ == "__main__":
    main()
    
