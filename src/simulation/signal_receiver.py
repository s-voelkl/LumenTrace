"""Deterministic signal receiver for local game simulation.

This module provides a scripted replacement for hardware UART input so local
simulation runs are repeatable and easy to inspect.
"""

import random

from src.controller.player_controller import PlayerController
from src.controller.signal_receiver_interface import SignalReceiverInterface

try:
    import msvcrt  # type: ignore
except ImportError:  # pragma: no cover - only relevant on non-Windows systems
    msvcrt = None


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
        keyboard_controls_enabled: bool = True,
    ) -> None:
        self.__controllers = controllers if controllers is not None else []
        self.__lane_change_period_ticks = max(1, lane_change_period_ticks)
        self.__keyboard_controls_enabled = keyboard_controls_enabled
        self.__tick = 0
        self.__manual_forward_press: float | None = None
        self.__manual_special_1_pulse = False
        self.__data: dict[str, list[dict[str, float | int]]] = {"controllers": []}

    def apply_manual_key(self, key: str) -> bool:
        """Apply one keyboard command for player 1 manual controls.

        Controls:
        - ``1``..``9`` set ``forward_press`` to ``10``..``90``
        - ``0`` sets ``forward_press`` to ``0``
        - ``r`` or ``R`` triggers one-tick ``special_1`` pulse

        Args:
            key (str): One-character keyboard input.

        Returns:
            bool: ``True`` if key was recognized and applied.
        """
        if not key:
            return False

        normalized = key.lower()
        if normalized in {"1", "2", "3", "4", "5", "6", "7", "8", "9"}:
            # Map 1-9 linearly into the active acceleration range [42000, 65535] 
            # used by the game logic.
            fraction = int(normalized) / 10.0
            self.__manual_forward_press = 42000.0 + fraction * (65535.0 - 42000.0)
            return True
        if normalized == "0":
            self.__manual_forward_press = 0.0
            return True
        if normalized == "r":
            self.__manual_special_1_pulse = True
            return True
        return False

    def __consume_keyboard_input(self) -> None:
        """Poll non-blocking keyboard input and apply manual controls.

        This is intentionally Windows-first for local development where the
        simulation is typically executed in a Windows terminal.
        """
        if not self.__keyboard_controls_enabled or msvcrt is None:
            return

        while msvcrt.kbhit():
            key = msvcrt.getwch()
            self.apply_manual_key(key)

    def __build_controller_values(self, controller_index: int) -> tuple[float, float]:
        """Return forward and special values for one controller.

        Args:
            controller_index (int): Index in the configured controller list.

        Returns:
            tuple[float, float]: ``(forward_press, special_1)`` values.
        """
        # Use simple sawtooth-like segments with per-controller phase offsets.
        # Values are scaled into the active range [42000, 65535] used by Game.
        phase = (self.__tick + controller_index * 17) % 120
        if phase < 30:
            percentage = 0.70
        elif phase < 60:
            percentage = 0.42
        elif phase < 90:
            percentage = 0.84
        else:
            percentage = 0.28
        
        forward_press = 42000.0 + percentage * (65535.0 - 42000.0)

        # Trigger lane-change intent.
        special_1 = random.choice([0.0] * 2 + [1.0])
        return forward_press, special_1

    def receive_signal(self) -> None:
        """Update all controllers with deterministic script values."""
        self.__consume_keyboard_input()
        controller_data: list[dict[str, float | int]] = []

        for controller_index, controller in enumerate(self.__controllers):
            if controller_index == 0:
                # Player 1 is manual-only during simulation.
                forward_press = (
                    self.__manual_forward_press
                    if self.__manual_forward_press is not None
                    else 0.0
                )
                special_1 = 1.0 if self.__manual_special_1_pulse else 0.0
            else:
                forward_press, special_1 = self.__build_controller_values(
                    controller_index
                )

            controller.update_input("adc_0", forward_press)
            controller.update_input("dig_0", special_1)
            controller_data.append(
                {
                    "controller_id": controller.controller_id,
                    "adc_0": forward_press,
                    "dig_0": special_1,
                }
            )

        # ``special_1`` key acts like a short button press and is consumed per tick.
        self.__manual_special_1_pulse = False
        self.__data["controllers"] = controller_data
        self.__tick += 1

    def get_data(self) -> dict:
        """Return latest emitted controller payload."""
        return self.__data
