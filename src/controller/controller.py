class Controller:
    '''Virtual player controller with multiple inputs (e.g. forward, backward, left, right, special_1, special_2).
    These inputs get updated by the signal receiver based on the received UART signal 
    of the original physical controller via the signal transmitter. 

    Returns:
        Controller: A virtual player controller.
    '''
    
    INPUT_MAPPING: dict[str, str] = {
        "adc_0": "forward_press",
        "adc_1": "backward_press",
        "adc_2": "left_press",
        "adc_3": "right_press"
    }
    
    def __init__(self, controller_id: int):
        '''Initializes the controller with a unique identifier and an empty dictionary for inputs.

        Args:
            controller_id (int): The unique identifier for the controller.
        '''
        self.__controller_id = controller_id
        self.__forward_press: float = 0
        self.__backward_press: float = 0
        self.__left_press: float = 0
        self.__right_press: float = 0
        self.__special_1: float = 0
        self.__special_2: float = 0

        
    def update_input(self, input_name: str, value):
        '''Updates the corresponding input value based on the received signal.
        
        Args:
            input_name (str): The name of the input to be updated (e.g., "adc_0").
            value: The value to update the input with.
        '''
        
        # mapping of keys (e.g. adc_0) to internal names (e.g. forward_press)
        internal_name = self.INPUT_MAPPING.get(input_name)
        if internal_name and value is not None and value != getattr(self, f"__{internal_name}"):
            # TODO: log info for received signal update
            setattr(self, f"__{internal_name}", value)
            print(f"Info: Received signal update for controller {self.__controller_id}: {input_name} -> {internal_name}")
        else:
            # TODO: log warning for unmapped input name
            print(f"Warning: Received unmapped input name '{input_name}' for controller {self.__controller_id}.")
            
    # Getters
    @property
    def controller_id(self) -> int:
        '''Returns the unique identifier for the controller.'''
        return self.__controller_id
    
    @property
    def forward_press(self) -> float:
        '''Returns the forward press value.'''
        return self.__forward_press

    @property
    def backward_press(self) -> float:
        '''Returns the backward press value.'''
        return self.__backward_press

    @property
    def left_press(self) -> float:
        '''Returns the left press value.'''
        return self.__left_press

    @property
    def right_press(self) -> float:
        '''Returns the right press value.'''
        return self.__right_press

    @property
    def special_1(self) -> float:
        '''Returns the special 1 value.'''
        return self.__special_1
    
    @property
    def special_2(self) -> float:
        '''Returns the special 2 value.'''
        return self.__special_2