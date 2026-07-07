from src.display.led_display import LedDisplay, VirtualLedStrip
from src.display.display_manager import DisplayManager
from src.display.color_constants import (
    GREEN,
    BLUE,
    PURPLE,
    WHITE,
    GRAY,
    LIGHT_PINK,
    LIGHT_GRAY,
    YELLOW,
    BLACK,
)
from src.display.config import DisplayConfig
from src.game.lane import Lane
from src.game.vehicle import Vehicle
from src.game.driving_profile import DrivingProfile
from src.game.track_module import TrackModule, TrackType
from src.game.line import Line
from src.game.game import Game
from src.game.settings import Settings


class MockGame(Game):
    def __init__(self, players, lanes, track_modules):
        self._Game__players = players
        self._Game__lanes = lanes
        self._Game__track_modules = track_modules
        self._Game__settings = Settings(vehicle_crash_distance=3.0)

    def _Game__get_lane_track_length(self, lane):
        return sum(
            [tm.get_line_length_for_lane(lane) for tm in self._Game__track_modules]
        )

    def _Game__get_track_module_for_lane_position(self, lane, position):
        # simplified mock
        curr = 0.0
        for tm in self._Game__track_modules:
            length = tm.get_line_length_for_lane(lane)
            curr += length
            if position <= curr:
                return tm, position - (curr - length)
        return None, 0.0


class MockPlayer:
    def __init__(self, vehicle):
        self.vehicle = vehicle


def test_display_manager_hierarchy():
    lane1 = Lane()
    dp = DrivingProfile(max_speed=100.0, min_speed=-100.0)
    line1 = Line(dp, lane1, 100.0)
    tm1 = TrackModule(TrackType.STRAIGHT, 100.0, [line1])

    vehicle = Vehicle(
        lane=lane1,
        position=50.0,
        speed=0.0,
        primary_color=GREEN,
        decelerate_color=BLUE,
        accelerate_color=PURPLE,
    )
    player = MockPlayer(vehicle)
    config = DisplayConfig()
    game = MockGame([player], [lane1], [tm1])

    vs = VirtualLedStrip(lane1, 0, 0, 9)
    display = LedDisplay({}, [vs])
    manager = DisplayManager(display, config)

    # 1. Active Vehicle at pos 50 out of 100 -> ratio 0.5 -> index 4
    manager.update(game)
    assert display.virtual_arrays[lane1.lane_id][3:6] == [GREEN, GREEN, GREEN]
    assert display.virtual_arrays[lane1.lane_id][0] == GRAY  # start of track

    # 2. Inactive Vehicle (40% primary + 60% gray)
    vehicle.set_respawn_ticks(10)
    manager.update(game)
    assert display.virtual_arrays[lane1.lane_id][3:6] == [
        (76, 178, 76),
        (76, 178, 76),
        (76, 178, 76),
    ]

    # 3. Round advance
    vehicle.set_active(True)
    vehicle.set_respawn_ticks(0)

    # Simulate advance round
    manager.update(game)  # manager registers initial round = 0
    vehicle.set_round(1)  # trigger advance
    manager.update(game)

    # Config is round_advance_ticks=20, config.round_advance_tick_color_change=5
    # During the update, ticks goes 20 -> 19
    # ticks=19, change=5 -> 19//5 = 3 -> 3 % 2 == 1 -> WHITE
    assert display.virtual_arrays[lane1.lane_id][0] == WHITE
    assert display.virtual_arrays[lane1.lane_id][6] == (
        3,
        0,
        5,
    )  # adjustment of dark purple

    # 4. Active Vehicle High Speed (warning)
    # let the round advance wear off
    for _ in range(20):
        manager.update(game)

    vehicle.set_speed(100.0)
    manager.update(game)
    assert display.virtual_arrays[lane1.lane_id][3:6] == [
        BLUE,
        BLUE,
        BLUE,
    ]  # completely decelerate color

    # 5. Intersection Animation & Module
    setattr(tm1, "_TrackModule__track_type", TrackType.INTERSECTION)
    setattr(dp, "_DrivingProfile__lane_change_allowed", True)
    manager.update(game)
    # intersection overrides everything except active vehicle / etc?
    # Actually active vehicle is calculated AFTER intersection, so active vehicle overrides intersection.
    # intersection animation fills the lane with LIGHT_PINK, then start track GRAY, then vehicle.
    assert display.virtual_arrays[lane1.lane_id][2] == (12, 12, 12)
    assert display.virtual_arrays[lane1.lane_id][3:6] == [BLUE, BLUE, BLUE]


def test_display_manager_active_color_interpolation():
    lane1 = Lane()
    dp = DrivingProfile(max_speed=100.0, min_speed=-100.0)
    line1 = Line(dp, lane1, 100.0)
    tm1 = TrackModule(TrackType.STRAIGHT, 100.0, [line1])

    vehicle = Vehicle(
        lane=lane1,
        position=50.0,
        speed=0.0,
        primary_color=(0, 255, 0),
        decelerate_color=(0, 0, 255),
        accelerate_color=(255, 0, 0),
    )
    player = MockPlayer(vehicle)
    config = DisplayConfig()
    game = MockGame([player], [lane1], [tm1])

    vs = VirtualLedStrip(lane1, 0, 0, 9)
    display = LedDisplay({}, [vs])
    manager = DisplayManager(display, config)

    # test center speed (no interp)
    vehicle.set_speed(0.0)
    manager.update(game)
    color = manager._get_active_color(vehicle, dp)
    assert color == (0, 255, 0)

    # test 75 speed (halfway to max threshold)
    # half_max = 50.0, max = 100.0. ratio = (75-50)/(100-50) = 0.5
    vehicle.set_speed(75.0)
    manager.update(game)
    color = manager._get_active_color(vehicle, dp)
    assert color == (0, 127, 127)  # 50% between (0, 255, 0) and (0, 0, 255)

    # test -75 speed (halfway to min threshold)
    # half_min = 50.0, abs_min = 100.0. ratio = (75-50)/(100-50) = 0.5
    vehicle.set_speed(-75.0)
    manager.update(game)
    color = manager._get_active_color(vehicle, dp)
    assert color == (127, 127, 0)  # 50% between (0, 255, 0) and (255, 0, 0)


def test_display_manager_inactive_vehicle_uses_fixed_gray_blend():
    lane1 = Lane()
    dp = DrivingProfile(max_speed=100.0, min_speed=-100.0)
    line1 = Line(dp, lane1, 100.0)
    tm1 = TrackModule(TrackType.STRAIGHT, 100.0, [line1])

    vehicle = Vehicle(lane=lane1, position=50.0, speed=0.0)
    player = MockPlayer(vehicle)
    config = DisplayConfig(respawn_tick_color_change=10)
    game = MockGame([player], [lane1], [tm1])

    vs = VirtualLedStrip(lane1, 0, 0, 9)
    display = LedDisplay({}, [vs])
    manager = DisplayManager(display, config)

    vehicle.set_active(False)

    vehicle.set_respawn_ticks(3)
    manager.update(game)
    assert display.virtual_arrays[lane1.lane_id][3:6] == [
        (76, 178, 76),
        (76, 178, 76),
        (76, 178, 76),
    ]

    vehicle.set_respawn_ticks(15)
    manager.update(game)
    assert display.virtual_arrays[lane1.lane_id][3:6] == [
        (76, 178, 76),
        (76, 178, 76),
        (76, 178, 76),
    ]
