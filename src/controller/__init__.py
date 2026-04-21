# on development machine, the machine and RPI.GPIO libraries are not available,
# so we need to handle the import errors gracefully.
try:
    import machine  # noqa: F401  # pyright: ignore[reportMissingImports]
    import os

    uname = getattr(os, "uname", None)
    _IS_RPI_3 = bool(uname and "rpi_3" in uname().machine.lower())
except Exception:
    _IS_RPI_3 = False

if _IS_RPI_3:
    from .physical_controller import PhysicalController
    from .signal_transmitter import SignalTransmitter
    from .signal_receiver import SignalReceiver
    
from .signal_receiver_mock import SignalReceiverMock
from .signal_receiver_interface import SignalReceiverInterface
from .player_controller import PlayerController

__all__ = [
    "SignalReceiver",
    "SignalReceiverMock",
    "SignalReceiverInterface",
    "PlayerController"
]

if _IS_RPI_3:
    __all__.extend([
        "PhysicalController",
        "SignalTransmitter",
    ])