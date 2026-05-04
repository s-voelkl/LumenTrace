import machine as ma

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