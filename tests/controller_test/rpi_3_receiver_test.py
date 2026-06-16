from src.controller.signal_receiver import SignalReceiver
from src.controller.player_controller import PlayerController
from src.controller.signal_receiver_mock import SignalReceiverMock


def test_signal_receiver_initialization():
    controller_1 = PlayerController()
    controller_2 = PlayerController()
    receiver = SignalReceiverMock(controllers=[controller_1, controller_2])
    assert receiver is not None
    assert len(receiver.controllers) == 2
    assert receiver.controllers[0].controller_id == 1
    assert receiver.controllers[1].controller_id == 2


def test_signal_receiver_receive_signal():
    controller_1 = PlayerController()
    receiver = SignalReceiverMock(controllers=[controller_1])

    receiver.receive_signal()
    assert "controllers" in receiver.get_data()
    assert len(receiver.get_data()["controllers"]) == 1
    assert receiver.get_data()["controllers"][0]["controller_id"] == 1
    assert "adc_0" in receiver.get_data()["controllers"][0]

    assert (
        controller_1.controller_id
        == receiver.get_data()["controllers"][0]["controller_id"]
    )
    assert controller_1.forward_press == receiver.get_data()["controllers"][0]["adc_0"]
