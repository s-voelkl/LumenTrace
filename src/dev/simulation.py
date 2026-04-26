"""Local terminal simulation entrypoint for game logic validation."""

from __future__ import annotations

from src.controller.player_controller import PlayerController
from src.game.driving_profile import DrivingProfile
from src.game.game import Game
from src.game.lane import Lane
from src.game.line import Line
from src.game.player import Player
from src.game.settings import Settings
from src.game.track_module import TrackModule, TrackType
from src.game.vehicle import Vehicle
from src.simulation import SimulationOrchestrator, SimulationSignalReceiver, TerminalSimulationRenderer


def build_simulation_track(lane_1: Lane, lane_2: Lane, lane_3: Lane) -> list[TrackModule]:
    """Create a mixed track with a temporary three-lane intersection.

    Rules requested for local simulation:
    - Standard modules use 2 lanes and block lane changes.
    - The intersection module exposes a temporary 3rd lane and allows lane changes.
    """
    return [
        TrackModule(
            track_type=TrackType.STRAIGHT,
            part_length=50,
            lines=[
                Line(
                    lane=lane_1,
                    line_length=50,
                    driving_profile=DrivingProfile(
                        max_speed=95,
                        min_speed=-30,
                        max_acceleration=100,
                        min_acceleration=-80,
                        lane_change_allowed=False,
                    ),
                ),
                Line(
                    lane=lane_3,
                    line_length=52,
                    driving_profile=DrivingProfile(
                        max_speed=95,
                        min_speed=-30,
                        max_acceleration=100,
                        min_acceleration=-80,
                        lane_change_allowed=False,
                    ),
                ),
            ],
        ),
        TrackModule(
            track_type=TrackType.CURVE_LEFT,
            part_length=35,
            lines=[
                Line(
                    lane=lane_1,
                    line_length=33,
                    driving_profile=DrivingProfile(
                        max_speed=78,
                        min_speed=-20,
                        max_acceleration=70,
                        min_acceleration=-70,
                        lane_change_allowed=False,
                    ),
                ),
                Line(
                    lane=lane_3,
                    line_length=37,
                    driving_profile=DrivingProfile(
                        max_speed=82,
                        min_speed=-20,
                        max_acceleration=70,
                        min_acceleration=-70,
                        lane_change_allowed=False,
                    ),
                ),
            ],
        ),
        TrackModule(
            track_type=TrackType.INTERSECTION,
            part_length=44,
            lines=[
                Line(
                    lane=lane_1,
                    line_length=44,
                    driving_profile=DrivingProfile(
                        max_speed=80,
                        min_speed=-15,
                        max_acceleration=70,
                        min_acceleration=-60,
                        lane_change_allowed=True,
                    ),
                ),
                # Temporary intersection lane for visualization and profile testing.
                Line(
                    lane=lane_2,
                    line_length=40,
                    driving_profile=DrivingProfile(
                        max_speed=80,
                        min_speed=-10,
                        max_acceleration=70,
                        min_acceleration=-50,
                        lane_change_allowed=True,
                    ),
                ),
                Line(
                    lane=lane_3,
                    line_length=42,
                    driving_profile=DrivingProfile(
                        max_speed=80,
                        min_speed=-15,
                        max_acceleration=70,
                        min_acceleration=-60,
                        lane_change_allowed=True,
                    ),
                ),
            ],
        ),
        TrackModule(
            track_type=TrackType.CURVE_RIGHT,
            part_length=34,
            lines=[
                Line(
                    lane=lane_1,
                    line_length=36,
                    driving_profile=DrivingProfile(
                        max_speed=80,
                        min_speed=-20,
                        max_acceleration=65,
                        min_acceleration=-65,
                        lane_change_allowed=False,
                    ),
                ),
                Line(
                    lane=lane_3,
                    line_length=32,
                    driving_profile=DrivingProfile(
                        max_speed=76,
                        min_speed=-20,
                        max_acceleration=65,
                        min_acceleration=-65,
                        lane_change_allowed=False,
                    ),
                ),
            ],
        ),
        TrackModule(
            track_type=TrackType.STRAIGHT,
            part_length=55,
            lines=[
                Line(
                    lane=lane_1,
                    line_length=55,
                    driving_profile=DrivingProfile(
                        max_speed=100,
                        min_speed=-30,
                        max_acceleration=90,
                        min_acceleration=-90,
                        lane_change_allowed=False,
                    ),
                ),
                Line(
                    lane=lane_3,
                    line_length=56,
                    driving_profile=DrivingProfile(
                        max_speed=100,
                        min_speed=-30,
                        max_acceleration=90,
                        min_acceleration=-90,
                        lane_change_allowed=False,
                    ),
                ),
            ],
        ),
    ]


def create_simulation_game() -> Game:
    """Construct two-player simulation game instance."""
    lane_1 = Lane()
    lane_2 = Lane() # temporary
    lane_3 = Lane()

    settings = Settings(
        max_speed=100,
        respawn_ticks=5,
        friction_percent=0.02,
        acceleration_multiplier=0.015,
        special_1_threshold=0.5,
        lane_change_ticks=2,
    )

    player_1 = Player(controller=PlayerController(), vehicle=Vehicle(lane=lane_1, position=0, style=[255, 40, 40]))
    player_2 = Player(controller=PlayerController(), vehicle=Vehicle(lane=lane_3, position=10, style=[40, 120, 255]))

    track_modules = build_simulation_track(lane_1, lane_2, lane_3)
    signal_receiver = SimulationSignalReceiver(
        controllers=[player_1.controller, player_2.controller],
        lane_change_period_ticks=12,
    )

    # Include temporary lane in lane order so intersection routing can be exercised.
    return Game(
        players=[player_1, player_2],
        settings=settings,
        track_modules=track_modules,
        signal_receiver=signal_receiver,
        lanes=[lane_1, lane_2, lane_3],
    )


def main() -> None:
    """Run terminal simulation loop until bounded tick count is reached."""
    game = create_simulation_game()
    renderer = TerminalSimulationRenderer(track_width_chars=72)
    orchestrator = SimulationOrchestrator(
        game=game,
        renderer=renderer,
        game_tick_interval_s=0.5,
        display_interval_ticks=1,
    )

    orchestrator.run(max_ticks=2000)


if __name__ == "__main__":
    main()
