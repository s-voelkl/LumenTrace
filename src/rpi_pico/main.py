import time
import json
import machine as ma

def main():
    physical_controllers = [
        PhysicalController(adc_pins=[26])
    ]
    signal_transmitter = SignalTransmitter(controllers=physical_controllers)
    while True:
        # print("Transmitting signal...")
        # time.sleep(0.05)
        signal_transmitter.transmit_signal()


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
        controllers = None):
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
        self.controllers = controllers if controllers is not None else []

    def transmit_signal(self, sleep_s = 0.05):
        '''Transmits the current values of the physical controllers as a JSON object via UART.
        Even if no change in the values of the physical controllers is detected, 
        the current values will be transmitted at regular intervals.

        Args:
            sleep_s (float, optional): The time to sleep between transmissions, in seconds. Defaults to 0.05.
        '''

        # read value(s) from ADCs of the physical controllers
        controllers_data = []
        
        for controller in self.controllers:
            values = controller.read_values()
            # Combine ID and data
            entry = {"controller_id": controller.controller_id}
            entry.update(values)
            controllers_data.append(entry)
            

        # build complete json
        data = {"controllers": controllers_data}
        
        # send via UART as JSON string
        self.serial.write(json.dumps(data).encode('utf-8'))
        time.sleep(sleep_s)

class PhysicalController:
    '''
    Represents a physical controller with multiple ADC pins.
    Each controller can have multiple ADC pins, that can be read.
    
    Args:
        controller_id (int): The unique identifier for the controller.
        adc_pins (list[int]): A list of GPIO pin numbers for the ADC pins.
    '''
    
    # static controller count to generate default controller ids
    __controller_count = 0

    def __init__(self, adc_pins):
        '''Initializes the physical controller with a unique identifier and a list of ADC pins.

        Args:
            controller_id (int): The unique identifier for the controller.
            adc_pins (list[int]): A list of GPIO pin numbers for the ADC pins. 
                E.g., [26, 27] for ADC0 and ADC1 on Raspberry Pi Pico.
        '''
        
        self.__controller_count += 1
        self.controller_id = self.__controller_count
        self.adc_controllers = []
        
        # multiple pins allowed per controller, e.g. for multiple sensors
        for pin in adc_pins:
            self.adc_controllers.append(ma.ADC(pin))
            
    def __del__(self):
        # decrement controller count when a controller instance is deleted
        PhysicalController.__controller_count -= 1
                    
    def read_values(self):
        """Read all ADC values from the controller's pins.
        
        Returns:
            dict[str, int]: Dictionary with ADC values keyed by pin index (e.g., "adc_0", "adc_1").
        """
        # read values of adc_0..n and save in self.data
        data = {}
        
        for i, adc_controller in enumerate(self.adc_controllers):
            data["adc_{}".format(i)] = adc_controller.read_u16()
            
        return data
    
if __name__ == "__main__":
    main()
