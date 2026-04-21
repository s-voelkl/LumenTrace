from abc import ABC, abstractmethod

class SignalReceiverInterface(ABC):
        
    @abstractmethod
    def receive_signal(self):
        '''
        Receives the UART signal, decodes it, and updates the corresponding controllers.
        See controller/example_signal.json for the expected format of the received signal.        
        '''
        pass
    
    @abstractmethod
    def get_data(self) -> dict:
        '''Returns the last received data as a dictionary.'''
        pass