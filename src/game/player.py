from src.controller.player_controller import PlayerController
from .vehicle import Vehicle


class Player:
    # static player count to generate default player names
    __player_count = 0

    def __init__(self, controller: PlayerController, vehicle: Vehicle, name: str = ""):
        Player.__player_count += 1
        self.__name = name if name else f"Player {Player.__player_count}"
        self.__controller = controller
        self.__vehicle = vehicle

    def __del__(self):
        # decrement player count when a player instance is deleted
        Player.__player_count -= 1

    # Getters
    @property
    def name(self) -> str:
        return self.__name

    @property
    def controller(self) -> PlayerController:
        return self.__controller

    @property
    def vehicle(self) -> Vehicle:
        return self.__vehicle
