from src.controller.signal_receiver import SignalReceiver
from src.controller.player_controller import PlayerController

def test_signal_receiver_initialization():
    controller_1 = PlayerController(controller_id=1)
    controller_2 = PlayerController(controller_id=2)
    receiver = SignalReceiver(controllers=[controller_1, controller_2])
    assert receiver is not None
    assert len(receiver.__controllers) == 2
    assert receiver.__controllers[0].controller_id == 1
    assert receiver.__controllers[1].controller_id == 2 

def test_signal_receiver_receive_signal():
    controller_1 = PlayerController(controller_id=1)
    receiver = SignalReceiver(controllers=[controller_1])

    while True:
        receiver.receive_signal(0.05)
        
        if receiver.__data:
            assert "controllers" in receiver.__data
            assert len(receiver.__data["controllers"]) == 1
            assert receiver.__data["controllers"][0]["controller_id"] == 1
            assert "adc_0" in receiver.__data["controllers"][0]
            
            assert controller_1.controller_id == receiver.__data["controllers"][0]["controller_id"]
            assert controller_1.forward_press == receiver.__data["controllers"][0]["adc_0"]
            assert controller_1.backward_press == 0
            
            
