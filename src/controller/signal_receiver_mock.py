'''
Mock implementation of the SignalReceiverInterface for testing without raspberry pi libraries and actual UART signal.
'''

import random
from .signal_receiver_interface import SignalReceiverInterface
from .player_controller import PlayerController
from src.logger.multi_logger import get_logger

logger = get_logger()

class SignalReceiverMock(SignalReceiverInterface):
    '''Mock implementation of the SignalReceiverInterface for testing without actual UART signal.'''
    
    def __init__(self, controllers: list[PlayerController]):
        self.__controllers = controllers if controllers is not None else []
        self.__data = {"controllers": []}

    def __controller_data(self, controller: PlayerController) -> dict:
        data = {"controller_id": controller.controller_id}

        for adc_index, input_name in enumerate(controller.INPUT_MAPPING.keys()):
            data[f"adc_{adc_index}"] = getattr(controller, controller.INPUT_MAPPING[input_name])

        return data

    def receive_signal(self):
        '''Updates the corresponding controllers with random values between 0 and 1 for testing without actual UART signal.'''
        
        for controller in self.__controllers:
            for input_name in controller.INPUT_MAPPING.keys():
                value = 0.5 + 0.5 * random.random()
                controller.update_input(input_name, value)

        self.__data["controllers"] = [self.__controller_data(controller) for controller in self.__controllers]
                
    # Getters
    def get_data(self) -> dict:
        '''Returns the last received data as a dictionary.'''
        return self.__data
    
    @property
    def controllers(self) -> list[PlayerController]:
        return self.__controllers