from src.controller.player_controller import PlayerController
from .vehicle import Vehicle

class Player:
    def __init__(self, name: str, controller: PlayerController, vehicle: Vehicle):
        self.__name = name if name else "Player"
        self.__controller = controller 
        self.__vehicle = vehicle
        self.__wins = 0
        self.__losses = 0
        
        
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

    @property
    def wins(self) -> int:
        return self.__wins

    @property
    def losses(self) -> int:
        return self.__losses