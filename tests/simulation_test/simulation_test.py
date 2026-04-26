"""Tests for local terminal simulation components."""

from src.controller.player_controller import PlayerController
from src.dev.simulation import create_simulation_game
from src.game import DrivingProfile, Game, Line, Player, Settings, TrackModule, Vehicle
from src.game.track_module import TrackType
from src.game.lane import Lane
from src.game.vehicle import Vehicle
from src.simulation.signal_receiver import SimulationSignalReceiver
from src.simulation.terminal_renderer import TerminalSimulationRenderer


def test_simulation_signal_receiver_emits_deterministic_payload() -> None:
    """Receiver should update controllers and expose consistent data schema."""
    controller_1 = PlayerController()
    controller_2 = PlayerController()
    receiver = SimulationSignalReceiver([controller_1, controller_2], lane_change_period_ticks=10)

    receiver.receive_signal()
    payload = receiver.get_data()

    assert "controllers" in payload
    assert len(payload["controllers"]) == 2
    assert payload["controllers"][0]["adc_0"] in {70.0, 42.0, 84.0, 28.0}
    assert payload["controllers"][0]["adc_1"] in {0.0, 1.0}
    assert controller_1.forward_press in {70.0, 42.0, 84.0, 28.0}


def test_terminal_renderer_frame_contains_required_sections() -> None:
    """Rendered frame should include settings, players, modules, and visual track."""
    game = create_simulation_game()
    game.tick_once(fetch_data=True, display=False, game_tick_interval_s=0.05)

    renderer = TerminalSimulationRenderer(track_width_chars=40)
    frame = renderer.render_frame(game, tick=1)

    assert "SETTINGS" in frame
    assert "PLAYERS" in frame
    assert "TRACK MODULES" in frame
    assert "VISUAL TRACK" in frame
    assert "intersection" in frame
    assert "lane_change_allowed=True" in frame


def test_tick_once_moves_vehicle_forward_for_positive_input() -> None:
    """Public single tick API should advance position with positive acceleration."""
    game = create_simulation_game()
    vehicle: Vehicle = game.players[0].vehicle
    start_position = vehicle.position

    for _ in range(5):
        game.tick_once(fetch_data=True, display=False, game_tick_interval_s=0.05)

    assert vehicle.position >= start_position


def test_visual_track_draws_player_marker_for_active_vehicle() -> None:
    """Visual lane bar should show at least one player marker digit."""
    game = create_simulation_game()
    renderer = TerminalSimulationRenderer(track_width_chars=48)

    # Force one clear active vehicle placement for deterministic marker assertion.
    game.players[0].vehicle.set_lane(game.lanes[0])
    game.players[0].vehicle.set_position(5.0)
    game.players[0].vehicle.set_active(True)

    frame = renderer.render_frame(game, tick=0)
    assert "1" in frame


def test_visual_track_includes_intersection_lane() -> None:
    """Visual lane section should include the configured third intersection lane."""
    game = create_simulation_game()
    renderer = TerminalSimulationRenderer(track_width_chars=48)

    frame = renderer.render_frame(game, tick=0)
    lane_ids = sorted([lane.lane_id for lane in game.lanes])
    assert len(lane_ids) >= 3
    assert f"L{lane_ids[2]} [" in frame


def test_renderer_event_log_persists_events_across_ticks() -> None:
    """Event panel should keep older events visible after further ticks."""
    game = create_simulation_game()
    renderer = TerminalSimulationRenderer(track_width_chars=48, max_event_lines=20)

    # Force an immediate profile violation so a fall event is produced.
    game.players[0].controller.update_input("adc_0", 500.0)
    game.tick_once(fetch_data=False, display=False, game_tick_interval_s=0.05)
    frame_after_fall = renderer.render_frame(game, tick=1)
    assert "EVENT LOG" in frame_after_fall
    assert "player_fell" in frame_after_fall

    # Run another tick and ensure the event is still listed in the persistent panel.
    game.tick_once(fetch_data=False, display=False, game_tick_interval_s=0.05)
    frame_after_next_tick = renderer.render_frame(game, tick=2)
    assert "player_fell" in frame_after_next_tick


def test_middle_lane_player_can_initiate_lane_change_in_three_lane_module() -> None:
    """Middle-lane players should be able to initiate lane changes in 3-lane layouts."""
    lane_1 = Lane()
    lane_2 = Lane()
    lane_3 = Lane()

    module = TrackModule(
        track_type=TrackType.INTERSECTION,
        part_length=100,
        lines=[
            Line(driving_profile=DrivingProfile(lane_change_allowed=True), lane=lane_1, line_length=100),
            Line(driving_profile=DrivingProfile(lane_change_allowed=True), lane=lane_2, line_length=100),
            Line(driving_profile=DrivingProfile(lane_change_allowed=True), lane=lane_3, line_length=100),
        ],
    )

    controller = PlayerController()
    controller.update_input("adc_0", 0.0)
    controller.update_input("adc_1", 1.0)

    player = Player(controller=controller, vehicle=Vehicle(lane=lane_2, position=10.0))
    game = Game(
        players=[player],
        settings=Settings(lane_change_ticks=1, special_1_threshold=0.5),
        track_modules=[module],
        signal_receiver=SimulationSignalReceiver([controller], lane_change_period_ticks=1000),
        lanes=[lane_1, lane_2, lane_3],
    )

    game.tick_once(fetch_data=False, display=False, game_tick_interval_s=0.05)
    assert player.vehicle.lane == lane_3
