from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.game.game import Game
    from src.game.lane import Lane

try:
    from rpi_ws281x import PixelStrip, Color as WsColor
    _HAS_HW = True
except ImportError:
    _HAS_HW = False

_SAFETY_BRIGHTNESS_CAP = 80  # max 80/255 ≈ 31 % – strip draws less current


@dataclass
class LaneStripConfig:
    """Maps one lane to a contiguous segment on the physical LED strip.

    Args:
        lane_id: ID of the lane this config applies to.
        led_offset: Index of the first LED belonging to this lane on the strip.
        led_count: Number of LEDs reserved for this lane.
    """
    lane_id: int
    led_offset: int
    led_count: int


class Display:
    """Renders live game state onto a WS2812 LED strip connected to the RPi 4.

    Only LEDs around active vehicle positions and the start/finish marker are
    lit. The strip background stays dark at all times to stay within safe
    power limits. Overall brightness is capped at _SAFETY_BRIGHTNESS_CAP.

    If rpi_ws281x is not available (development machine) the class silently
    skips hardware writes; the internal buffer is still updated for testing.

    Args:
        lane_configs: One LaneStripConfig per lane, mapping lane IDs to strip
            segments.
        total_led_count: Total number of LEDs on the physical strip.
        gpio_pin: BCM pin number the strip data line is connected to (default 18).
        units_per_meter: How many position units equal one meter (default 100
            for centimetres). Used only for documentation / future scaling;
            the mapping is always proportional to lane length.
        brightness: Global strip brightness 0–255. Clamped to
            _SAFETY_BRIGHTNESS_CAP regardless of the value passed.
    """

    _COLOR_HEADLIGHT: tuple[int, int, int] = (220, 220, 160)
    _COLOR_TAILLIGHT: tuple[int, int, int] = (180, 0, 0)
    _COLOR_FINISH:    tuple[int, int, int] = (0, 80, 0)
    _COLOR_INACTIVE:  tuple[int, int, int] = (30, 0, 0)   # dim red = respawning

    def __init__(
        self,
        lane_configs: list[LaneStripConfig],
        total_led_count: int,
        gpio_pin: int = 18,
        units_per_meter: float = 100.0,
        brightness: int = 80,
    ) -> None:
        self.__configs: dict[int, LaneStripConfig] = {
            cfg.lane_id: cfg for cfg in lane_configs
        }
        self.__total = total_led_count
        self.__units_per_meter = units_per_meter
        self.__brightness = min(max(brightness, 0), _SAFETY_BRIGHTNESS_CAP)
        self.__buffer: list[tuple[int, int, int]] = [(0, 0, 0)] * total_led_count

        if _HAS_HW:
            self.__strip: PixelStrip | None = PixelStrip(
                total_led_count,
                gpio_pin,
                freq_hz=800_000,
                dma=10,
                invert=False,
                brightness=self.__brightness,
                channel=0,
            )
            self.__strip.begin()
        else:
            self.__strip = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, game: Game) -> None:
        """Recompute LED colours from current game state and push to strip."""
        self.__clear_buffer()
        self.__draw_finish_markers(game)
        self.__draw_vehicles(game)
        self.__flush()

    def cleanup(self) -> None:
        """Turn all LEDs off and release hardware. Call on shutdown."""
        self.__clear_buffer()
        self.__flush()

    # ------------------------------------------------------------------
    # Internal rendering
    # ------------------------------------------------------------------

    def __draw_finish_markers(self, game: Game) -> None:
        for lane in game.lanes:
            cfg = self.__configs.get(lane.lane_id)
            if cfg is None:
                continue
            # position 0 is start/finish → first LED of the lane segment
            self.__set_led(cfg.led_offset, self._COLOR_FINISH)

    def __draw_vehicles(self, game: Game) -> None:
        for player in game.players:
            vehicle = player.vehicle

            if vehicle.lane is None:
                continue

            cfg = self.__configs.get(vehicle.lane.lane_id)
            if cfg is None:
                continue

            if not vehicle.active:
                # show a dim marker at strip start while respawning
                self.__set_led(cfg.led_offset, self._COLOR_INACTIVE)
                continue

            total_length = self.__lane_length(game, vehicle.lane)
            if total_length <= 0:
                continue

            progress = max(0.0, min(vehicle.position / total_length, 1.0))
            center = cfg.led_offset + int(progress * (cfg.led_count - 1))

            body_color = self.__resolve_color(vehicle.style)

            # rear – body – front  (positive movement = increasing index)
            self.__set_led(center - 1, self._COLOR_TAILLIGHT)
            self.__set_led(center,     body_color)
            self.__set_led(center + 1, self._COLOR_HEADLIGHT)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def __lane_length(self, game: Game, lane: Lane) -> float:
        return sum(tm.get_line_length_for_lane(lane) for tm in game.track_modules)

    def __resolve_color(self, style: list[int]) -> tuple[int, int, int]:
        if style and len(style) >= 3 and any(v > 0 for v in style[:3]):
            return (
                max(0, min(style[0], 255)),
                max(0, min(style[1], 255)),
                max(0, min(style[2], 255)),
            )
        return (0, 120, 255)  # default blue if style is unset / all-zero

    def __set_led(self, index: int, color: tuple[int, int, int]) -> None:
        if 0 <= index < self.__total:
            self.__buffer[index] = color

    def __clear_buffer(self) -> None:
        for i in range(self.__total):
            self.__buffer[i] = (0, 0, 0)

    def __flush(self) -> None:
        if self.__strip is None:
            return
        for i, (r, g, b) in enumerate(self.__buffer):
            self.__strip.setPixelColor(i, WsColor(r, g, b))
        self.__strip.show()

    # ------------------------------------------------------------------
    # Read-only access for tests / debugging
    # ------------------------------------------------------------------

    @property
    def buffer(self) -> list[tuple[int, int, int]]:
        """Current LED colour buffer (copy). All zeros when strip is dark."""
        return list(self.__buffer)

    @property
    def brightness(self) -> int:
        return self.__brightness

    @property
    def units_per_meter(self) -> float:
        return self.__units_per_meter
