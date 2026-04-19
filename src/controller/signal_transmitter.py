from controller.physical_controller import PhysicalController
import time
import json
import machine as ma


class SignalTransmitter:
    '''Handles the outgoing UART-signal as the transmitter for further processing.'''

    __BAUD_RATE = 115200

    def __init__(self,
        tx_pin=0,
        rx_pin=1,
        baud_rate=__BAUD_RATE,
        bits=8,
        parity=None,
        stop=1,
        controllers: list[PhysicalController] = []):
        '''Initializes the SignalTransmitter with the specified UART configuration and a list of physical controllers to read values from.

        Args:
            tx_pin (int, optional): The GPIO pin number for the UART transmit pin. Defaults to 0.
            rx_pin (int, optional): The GPIO pin number for the UART receive pin. Defaults to 1.
            baud_rate (_type_, optional): The baud rate for the UART communication. Defaults to __BAUD_RATE.
            bits (int, optional): The number of data bits for the UART communication. Defaults to 8.
            parity (_type_, optional): The parity setting for the UART communication. Defaults to None.
            stop (int, optional): The number of stop bits for the UART communication. Defaults to 1.
            controllers (list[PhysicalController], optional): A list of physical controllers to read values from. Defaults to [].
        '''

        self.serial = ma.UART(0, baudrate=baud_rate, tx=ma.Pin(tx_pin), rx=ma.Pin(rx_pin),
            bits=bits, parity=parity, stop=stop)
        self.controllers: list[PhysicalController] = controllers if controllers is not None else []

    def __transmit_signal(self, sleep_s: float = 0.05):
        '''Transmits the current values of the physical controllers as a JSON object via UART.
        Even if no change in the values of the physical controllers is detected, 
        the current values will be transmitted at regular intervals.

        Args:
            sleep_s (float, optional): The time to sleep between transmissions, in seconds. Defaults to 0.05.
        '''

        # read value(s) from ADCs of the physical controllers
        controllers_data = []
        for controller in self.controllers:
            values: dict = controller.read_values()
            controllers_data.append({
                "controller_id": controller.controller_id,
                **values
            })

        # build complete json
        data = {"controllers": controllers_data}
        
        # send via UART as JSON string
        self.serial.write(json.dumps(data).encode('utf-8'))
        time.sleep(sleep_s)
