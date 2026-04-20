from src.controller.signal_transmitter import SignalTransmitter
from src.controller.physical_controller import PhysicalController

def test_signal_transmitter_initialization():
    physical_controller_1 = PhysicalController(controller_id=1, adc_pins=[26, 27])
    physical_controller_2 = PhysicalController(controller_id=2, adc_pins=[28, 29])   

    transmitter = SignalTransmitter(controllers=[physical_controller_1, physical_controller_2])
    assert transmitter is not None
    assert transmitter.serial is not None
    assert transmitter.controllers == [physical_controller_1, physical_controller_2]
    assert transmitter.controllers[0].controller_id == 1
    assert transmitter.controllers[1].controller_id == 2

def test_signal_transmitter_transmit_signal():
    physical_controller_1 = PhysicalController(controller_id=1, adc_pins=[26, 27])

    transmitter = SignalTransmitter(controllers=[physical_controller_1])

    while True:
        transmitter.transmit_signal(0.01)
