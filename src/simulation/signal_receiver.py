"""Deterministic signal receiver for local game simulation.

This module provides a scripted replacement for hardware UART input so local
simulation runs are repeatable and easy to inspect.
"""

from __future__ import annotations

from src.controller.player_controller import PlayerController
from src.controller.signal_receiver_interface import SignalReceiverInterface
import random

class SimulationSignalReceiver(SignalReceiverInterface):
    """Provide deterministic controller values for simulation runs.

    The receiver emits a smooth throttle curve and configurable lane-change
    pulses. It intentionally avoids random numbers so state transitions can be
    reproduced during debugging and in tests.
    """

    def __init__(
        self,
        controllers: list[PlayerController],
        lane_change_period_ticks: int = 2,
    ) -> None:
        self.__controllers = controllers if controllers is not None else []
        self.__lane_change_period_ticks = max(1, lane_change_period_ticks)
        self.__tick = 0
        self.__data: dict[str, list[dict[str, float | int]]] = {"controllers": []}

    def __build_controller_values(self, controller_index: int) -> tuple[float, float]:
        """Return forward and special values for one controller.

        Args:
            controller_index (int): Index in the configured controller list.

        Returns:
            tuple[float, float]: ``(forward_press, special_1)`` values.
        """
        # Use simple sawtooth-like segments with per-controller phase offsets.
        phase = (self.__tick + controller_index * 17) % 120
        if phase < 30:
            forward_press = 70.0
        elif phase < 60:
            forward_press = 42.0
        elif phase < 90:
            forward_press = 84.0
        else:
            forward_press = 28.0

        # Trigger lane-change intent.
        special_1 = random.choice([0.0] * 2 + [1.0])
        return forward_press, special_1

    def receive_signal(self) -> None:
        """Update all controllers with deterministic script values."""
        controller_data: list[dict[str, float | int]] = []

        for controller_index, controller in enumerate(self.__controllers):
            forward_press, special_1 = self.__build_controller_values(controller_index)
            controller.update_input("adc_0", forward_press)
            controller.update_input("adc_1", special_1)
            controller_data.append(
                {
                    "controller_id": controller.controller_id,
                    "adc_0": forward_press,
                    "adc_1": special_1,
                }
            )

        self.__data["controllers"] = controller_data
        self.__tick += 1

    def get_data(self) -> dict:
        """Return latest emitted controller payload."""
        return self.__data
