import json
import re
import time

from controller.player_controller import PlayerController
from typing import List
import serial
import RPi.GPIO as GPIO
from src.logger.multi_logger import get_logger

logger = get_logger()


class SignalReceiver:
    '''Handles the incoming UART-signal of the transmitter for further processing.'''
    __BAUD_RATE = 115200

    def __init__(self,
        baud_rate=__BAUD_RATE,
        bits=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stop=serial.STOPBITS_ONE,
        port='/dev/ttyS0',  # Default UART port on GPIO 14/15
        rx_pin=15,
        controllers=None):

        self.__controllers: List[PlayerController] = controllers if controllers is not None else []

        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(rx_pin, GPIO.IN)  # RX pin

        self.serial = serial.Serial(
            port=port,  # Default UART port on GPIO 14/15
            baudrate=baud_rate,
            parity=parity,
            stopbits=stop,
            bytesize=bits,
            timeout=1
        )
        self.data: dict = {}

    def receive_signal(self, wait_s: float = 0.1):
        '''Receives the UART signal, decodes it, and updates the corresponding controllers.
        See controller/example_signal.json for the expected format of the received signal.
        
        Args:
            wait_s (float): The time to wait between receiving signals, in seconds. Default is 0.1 seconds.
        '''

        # receive uart signal and decode it
        received_data = self.serial.read()              #read serial port
        data_left = self.serial.inWaiting()             #check for remaining byte
        received_data += self.serial.read(data_left)
        decoded_data = received_data.decode('utf-8')

        # find valid JSON objects with regex
        json_matches = re.findall(r'\{[^}]+\}', decoded_data)

        # get newest complete JSON object, update controllers if data is updated
        if json_matches:
            try:
                # get newest complete JSON object
                data = json.loads(json_matches[-1])

                # update controllers if data changed.
                if data != self.data:
                    self.data = data
                    controllers_list = data.get('controllers')

                    if controllers_list is not None:
                        for controller_data in controllers_list:
                            controller_id = controller_data.get('controller_id')
                            if controller_id is not None:
                                self.__update_controller(controller_id, controller_data)
                                logger.log(f"Updated controller {controller_id} with data: {controller_data}")

            except json.JSONDecodeError as e:
                logger.log(f"JSON decode error: {e}")
        else:
            logger.log("No valid JSON object found in received data.")
            
        time.sleep(wait_s)
    
    def __update_controller(self, controller_id: int, data: dict):
        '''Updates the corresponding controller with the received signal.

        Args:
            controller_id (int): The unique identifier for the controller to be updated.
            data (dict): A dictionary containing the input names and their corresponding values.
        '''
        for controller in self.__controllers:
            if controller.controller_id == controller_id:
                for input_name, value in data.items():
                    controller.update_input(input_name, value)
                break