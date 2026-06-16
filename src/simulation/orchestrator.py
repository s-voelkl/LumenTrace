"""Runtime orchestration for terminal simulation."""

import time

from src.game.game import Game
from src.simulation.terminal_renderer import TerminalSimulationRenderer


class SimulationOrchestrator:
    """Run deterministic game ticks and render dashboard frames.

    This orchestrator avoids the threaded ``Game.start_game`` path so simulation
    runs are easier to reason about and test.
    """

    def __init__(
        self,
        game: Game,
        renderer: TerminalSimulationRenderer,
        game_tick_interval_s: float = 0.05,
        display_interval_ticks: int = 1,
    ) -> None:
        self.__game = game
        self.__renderer = renderer
        self.__game_tick_interval_s = max(0.001, game_tick_interval_s)
        self.__display_interval_ticks = max(1, display_interval_ticks)

    def run(self, max_ticks: int = 1000) -> None:
        """Run simulation loop for a bounded number of ticks.

        Args:
            max_ticks (int): Maximum number of ticks before stopping.
        """
        tick = 0
        while tick < max_ticks:
            loop_start = time.perf_counter()
            self.__game.tick_once(fetch_data=True, show_display=False, game_tick_interval_s=self.__game_tick_interval_s)

            if tick % self.__display_interval_ticks == 0:
                self.__renderer.render_to_terminal(self.__game, tick)

            tick += 1
            elapsed = time.perf_counter() - loop_start
            sleep_time = self.__game_tick_interval_s - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
