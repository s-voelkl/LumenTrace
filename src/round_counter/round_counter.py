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
    ):
        """Initializes the round counter on a shared strip."""
        logger.log(
            __file__
            + f" -> __init__: Initializing RoundCounter starting at index {start_index}, zigzag={zigzag}, mirror={mirror_horizontal}, color={color}"
        )
        self.strip = strip
        self.start_index = start_index
        self.zigzag = zigzag
        self.mirror_horizontal = mirror_horizontal
        self.color = color
        self.current_value = -1  # Sentinel value to enforce rendering on first refresh

        # Clear local portion of the strip if the physical hardware is available
        if self.strip:
            self.clear()

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

        val_str = f"{val_clamped:02d}"
        digit_tens = val_str[0]
        digit_units = val_str[1]

        # Start with an empty, dark local buffer
        buffer = [(0, 0, 0)] * 64

        # Draw the Tens digit
        tens_matrix = FONT_3X5.get(digit_tens, FONT_3X5["0"])
        for r_idx, row_data in enumerate(tens_matrix):
            row = r_idx + 1
            for col, active in enumerate(row_data):
                if active:
                    local_idx = self._get_pixel_index(row, col) - self.start_index
                    buffer[local_idx] = self.color

        # Draw the Units digit
        units_matrix = FONT_3X5.get(digit_units, FONT_3X5["0"])
        for r_idx, row_data in enumerate(units_matrix):
            row = r_idx + 1
            for col_idx, active in enumerate(row_data):
                col = col_idx + 4
                if active:
                    local_idx = self._get_pixel_index(row, col) - self.start_index
                    buffer[local_idx] = self.color

        # Write the buffer array to the shared physical strip
        if self.strip:
            for idx, rgb in enumerate(buffer):
                color_val = Color(rgb[0], rgb[1], rgb[2])
                # Shift by start_index when sending to physical strip
                self.strip.setPixelColor(self.start_index + idx, color_val)
            self.strip.show()

    def clear(self) -> None:
        """Resets the matrix segment's pixels to the off state."""
        self.current_value = -1
        if self.strip:
            for idx in range(64):
                self.strip.setPixelColor(self.start_index + idx, 0)
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
