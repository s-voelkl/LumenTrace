"""Local terminal simulation entrypoint for game logic validation."""

from src.controller.player_controller import PlayerController
from src.game.driving_profile import DrivingProfile
from src.game.game import Game
from src.game.lane import Lane
from src.game.line import Line
from src.game.player import Player
from src.game.settings import Settings
from src.game.track_module import TrackModule, TrackType
from src.game.vehicle import Vehicle
from src.simulation import (
    SimulationOrchestrator,
    SimulationSignalReceiver,
    TerminalSimulationRenderer,
)


def build_simulation_track(
    lane_0: Lane, lane_1: Lane, lane_2: Lane
) -> list[TrackModule]:
    """Create a mixed track with a temporary three-lane intersection.

    Rules requested for local simulation:
    - Standard modules use 2 lanes and block lane changes.
    - The intersection module exposes a temporary 3rd lane and allows lane changes.
    """

    max_speed = 100

    track_modules: list[TrackModule] = [
        TrackModule(
            track_type=TrackType.STRAIGHT,
            part_length=34.3,
            sound_stereo_ratio_left=0.5,
            lines=[
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed),
                    lane=lane_0,
                    line_length=34.0,
                ),
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed),
                    lane=lane_2,
                    line_length=34.6,
                ),
            ],
        ),
        TrackModule(
            track_type=TrackType.CURVE_LEFT,
            part_length=27.3,
            sound_stereo_ratio_left=0.5,
            lines=[
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed * 0.75),
                    lane=lane_0,
                    line_length=22.5,
                ),
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed * 0.85),
                    lane=lane_2,
                    line_length=32.0,
                ),
            ],
        ),
        TrackModule(
            track_type=TrackType.INTERSECTION,
            part_length=45.5,
            sound_stereo_ratio_left=0.5,
            lines=[
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed),
                    lane=lane_0,
                    line_length=45.5,
                ),
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed),
                    lane=lane_1,
                    line_length=45.5,  # TODO: edit this intersection!
                ),
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed),
                    lane=lane_2,
                    line_length=45.5,
                ),
            ],
        ),
        TrackModule(
            track_type=TrackType.CURVE_RIGHT,
            part_length=80.5,
            sound_stereo_ratio_left=0.5,
            lines=[
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed * 0.75),
                    lane=lane_0,
                    line_length=94.5,
                ),
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed * 0.65),
                    lane=lane_2,
                    line_length=66.5,
                ),
            ],
        ),
        TrackModule(
            track_type=TrackType.STRAIGHT,
            part_length=45.7,
            sound_stereo_ratio_left=0.5,
            lines=[
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed),
                    lane=lane_0,
                    line_length=45.7,
                ),
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed),
                    lane=lane_2,
                    line_length=45.7,
                ),
            ],
        ),
        TrackModule(
            track_type=TrackType.LOOPING,
            part_length=103.0,
            sound_stereo_ratio_left=0.5,
            lines=[
                Line(
                    driving_profile=DrivingProfile(
                        max_speed=max_speed * 0.95, min_speed=max_speed * 0.6
                    ),
                    lane=lane_0,
                    line_length=103.0,
                ),
                Line(
                    driving_profile=DrivingProfile(
                        max_speed=max_speed * 0.95, min_speed=max_speed * 0.6
                    ),
                    lane=lane_2,
                    line_length=103.0,
                ),
            ],
        ),
        TrackModule(
            track_type=TrackType.INTERSECTION,
            part_length=34.2,
            sound_stereo_ratio_left=0.5,
            lines=[
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed),
                    lane=lane_0,
                    line_length=34.0,
                ),
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed),
                    lane=lane_1,
                    line_length=34.2,  # TODO: edit this intersection!
                ),
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed),
                    lane=lane_2,
                    line_length=34.3,
                ),
            ],
        ),
        TrackModule(
            track_type=TrackType.CURVE_RIGHT_BENDED,
            part_length=49.4,
            sound_stereo_ratio_left=0.5,
            lines=[
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed * 0.90),
                    lane=lane_0,
                    line_length=41.1,
                ),
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed * 0.95),
                    lane=lane_2,
                    line_length=57.6,
                ),
            ],
        ),
        TrackModule(
            track_type=TrackType.STRAIGHT,
            part_length=11.4,
            sound_stereo_ratio_left=0.5,
            lines=[
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed),
                    lane=lane_0,
                    line_length=11.4,
                ),
                Line(
                    driving_profile=DrivingProfile(max_speed=max_speed),
                    lane=lane_2,
                    line_length=11.4,
                ),
            ],
        ),
    ]

    return track_modules


def create_simulation_game() -> Game:
    """Construct two-player simulation game instance."""
    lane_0 = Lane()
    lane_1 = Lane()  # temporary
    lane_2 = Lane()

    settings = Settings(
        max_speed=100,
        respawn_ticks=6,
        friction_percent=0.05,
        acceleration_multiplier=0.1,
        lane_change_window=20,
        vehicle_crash_distance=3.0,
    )

    player_1 = Player(
        controller=PlayerController(), vehicle=Vehicle(lane=lane_0, position=0)
    )
    player_2 = Player(
        controller=PlayerController(), vehicle=Vehicle(lane=lane_2, position=10)
    )

    track_modules = build_simulation_track(lane_0, lane_1, lane_2)
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
        lanes=[lane_0, lane_1, lane_2],
        display_manager=None,
    )


def main() -> None:
    """Run terminal simulation loop until bounded tick count is reached."""
    game = create_simulation_game()
    renderer = TerminalSimulationRenderer(track_width_chars=72)
    orchestrator = SimulationOrchestrator(
        game=game,
        renderer=renderer,
        game_tick_interval_s=0.25,
        display_interval_ticks=1,
    )

    orchestrator.run(max_ticks=2000)


if __name__ == "__main__":
    main()
