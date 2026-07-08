import time
from typing import Tuple
from src.logger.multi_logger import get_logger

logger = get_logger()

try:
    from rpi_ws281x import PixelStrip, Color, ws

    RPI_WS281X_AVAILABLE = True
except ImportError:
    RPI_WS281X_AVAILABLE = False

    # Mock fallback classes for testing and local dry-runs on non-Pi platforms
    class PixelStrip:
        def __init__(self, *args, **kwargs):
            pass

        def begin(self):
            pass

        def setPixelColor(self, index, color):
            pass

        def show(self):
            pass

    def Color(red: int, green: int, blue: int, white: int = 0) -> int:
        return (white << 24) | (red << 16) | (green << 8) | blue

    class ws:
        WS2811_STRIP_GRB = 0x00100800
        WS2811_STRIP_RGB = 0x00100008


# 3x5 font mapping for digits '0' through '9'.
FONT_3X5 = {
    "0": [
        [1, 1, 1], 
        [1, 0, 1], 
        [1, 0, 1], 
        [1, 0, 1], 
        [1, 1, 1]
    ],
    "1": [
        [0, 1, 0], 
        [1, 1, 0], 
        [0, 1, 0], 
        [0, 1, 0], 
        [1, 1, 1]
    ],
    "2": [
        [1, 1, 1], 
        [0, 0, 1], 
        [1, 1, 1], 
        [1, 0, 0], 
        [1, 1, 1]
    ],
    "3": [
        [1, 1, 1], 
        [0, 0, 1], 
        [1, 1, 1], 
        [0, 0, 1], 
        [1, 1, 1]
    ],
    "4": [
        [1, 0, 1], 
        [1, 0, 1], 
        [1, 1, 1], 
        [0, 0, 1], 
        [0, 0, 1]
    ],
    "5": [
        [1, 1, 1], 
        [1, 0, 0], 
        [1, 1, 1], 
        [0, 0, 1], 
        [1, 1, 1]
    ],
    "6": [
        [1, 1, 1], 
        [1, 0, 0], 
        [1, 1, 1], 
        [1, 0, 1], 
        [1, 1, 1]
    ],
    "7": [
        [1, 1, 1], 
        [0, 0, 1], 
        [0, 1, 0], 
        [0, 1, 0], 
        [0, 1, 0]
    ],
    "8": [
        [1, 1, 1], 
        [1, 0, 1], 
        [1, 1, 1], 
        [1, 0, 1], 
        [1, 1, 1]
    ],
    "9": [
        [1, 1, 1], 
        [1, 0, 1], 
        [1, 1, 1], 
        [0, 0, 1], 
        [1, 1, 1]
    ],
}


class RoundCounter:
    """Manages an 8x8 WS2812B/NeoPixel LED matrix panel to display round numbers.

    Shares an existing physical PixelStrip instance, utilizing index offsets.
    """

    def __init__(
        self,
        strip,  # Pass the pre-existing initialized PixelStrip object
        start_index: int,  # The starting LED index of the 8x8 matrix on this strip
        zigzag: bool = True,
        mirror_horizontal: bool = False,
        color: Tuple[int, int, int] = (255, 255, 255),
        auto_show: bool = True,
    ):
        """Initializes the round counter on a shared strip."""
        self.strip = strip
        self.start_index = start_index
        self.zigzag = zigzag
        self.mirror_horizontal = mirror_horizontal
        self.color = color
        self.auto_show = auto_show
        self.current_value = -1  # Sentinel value to enforce rendering on first refresh

        # Pre-calculate internal buffers for all 100 possible round numbers (00-99)
        self._buffers = []
        self._precompute_buffers()

        # Clear local portion of the strip if the physical hardware is available
        if self.strip:
            self.clear()

    def _precompute_buffers(self) -> None:
        """Pre-calculates 64-pixel color buffers for every displayable round number."""
        self._buffers = []
        c_on = Color(*self.color)
        for val in range(100):
            # Start with a black/off buffer
            buf = [0] * 64
            val_str = f"{val:02d}"

            # Tens digit (left side)
            tens_matrix = FONT_3X5.get(val_str[0], FONT_3X5["0"])
            for r_idx, row_data in enumerate(tens_matrix):
                row = r_idx + 1
                for col_idx, active in enumerate(row_data):
                    if active:
                        local_idx = self._get_pixel_index(row, col_idx) - self.start_index
                        buf[local_idx] = c_on

            # Units digit (right side)
            units_matrix = FONT_3X5.get(val_str[1], FONT_3X5["0"])
            for r_idx, row_data in enumerate(units_matrix):
                row = r_idx + 1
                for col_idx, active in enumerate(row_data):
                    col = col_idx + 4
                    if active:
                        local_idx = self._get_pixel_index(row, col) - self.start_index
                        buf[local_idx] = c_on
            self._buffers.append(buf)

    def set_color(self, color: Tuple[int, int, int]) -> None:
        """Updates the display color and re-precomputes internal buffers."""
        if color != self.color:
            self.color = color
            self._precompute_buffers()
            # Force refresh if a value is currently set
            if self.current_value != -1:
                temp_val = self.current_value
                self.current_value = -1
                self.display_round(temp_val)

    def _get_pixel_index(self, row: int, col: int) -> int:
        """Translates 2D matrix coordinates to the shared 1D physical strip index."""
        if self.mirror_horizontal:
            col = 7 - col

        if self.zigzag:
            if row % 2 == 0:
                local_idx = row * 8 + col
            else:
                local_idx = row * 8 + (7 - col)
        else:
            local_idx = row * 8 + col

        return self.start_index + local_idx

    def display_round(self, value: int) -> None:
        """Renders the given round number (0 to 99) onto the 8x8 grid."""
        val_clamped = max(0, min(99, value))

        if val_clamped == self.current_value:
            return  # Skip processing if the number has not changed

        self.current_value = val_clamped

        # Fast path: use pre-calculated color buffer
        if self.strip:
            buf = self._buffers[val_clamped]
            for idx, color_val in enumerate(buf):
                self.strip.setPixelColor(self.start_index + idx, color_val)

            if self.auto_show:
                self.strip.show()

    def clear(self) -> None:
        """Resets the matrix segment's pixels to the off state."""
        self.current_value = -1
        if self.strip:
            for idx in range(64):
                self.strip.setPixelColor(self.start_index + idx, 0)

            if self.auto_show:
                self.strip.show()


if __name__ == "__main__":
    # --- Example Usage ---
    # In a real scenario, you usually have a PixelStrip already initialized.
    # For this demonstration, we create a mock or real strip depending on the platform.

    # Configuration for a standalone matrix test
    # If RPI_WS281X_AVAILABLE is True, it will try to use the real hardware.
    # If False, it uses the Mock classes defined above.
    LED_COUNT = 64
    LED_PIN = 19

    strip = PixelStrip(
        num=LED_COUNT,
        pin=LED_PIN,
        freq_hz=800_000,
        dma=10,
        invert=False,
        brightness=255,  # Slightly dimmed for safety
        channel=1,  # needed for gpio 19
    )
    strip.begin()

    counter = RoundCounter(
        strip=strip,
        start_index=0,
        zigzag=True,  # Matrix uses serpentine/zigzag layout
        mirror_horizontal=True,
        color=(0, 255, 100),  # Cyan-ish green
    )

    try:
        logger.log("RoundCounter demonstration: cycling digits...")
        # Step through a small range of numbers to verify both digits work.
        for i in range(0, 100):
            # logger.log(f"Rendering round: {i}")
            counter.display_round(i)
            time.sleep(0.05)

        counter.display_round(99)
        logger.log("Clearing panel.")
        counter.clear()

    except KeyboardInterrupt:
        # Graceful exit on Ctrl+C
        if counter:
            counter.clear()
        logger.log("Demonstration stopped by user.")
