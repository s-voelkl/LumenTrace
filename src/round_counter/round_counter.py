from typing import Tuple
from src.logger.multi_logger import get_logger

logger = get_logger()

try:
    from rpi_ws281x import PixelStrip

    RPI_WS281X_AVAILABLE = True
except ImportError:
    RPI_WS281X_AVAILABLE = False

    # Mock fallback class for testing and local dry-runs on non-Pi platforms
    class PixelStrip:
        def __init__(self, *args, **kwargs):
            pass

        def begin(self):
            pass

        def setPixelColor(self, index, color):
            pass

        def show(self):
            pass


# 3x5 font mapping for digits '0' through '9'.
# Each element represents 5 rows and 3 columns.
# 1 denotes an active pixel, 0 denotes an inactive pixel.
FONT_3X5 = {
    "0": [[1, 1, 1], [1, 0, 1], [1, 0, 1], [1, 0, 1], [1, 1, 1]],
    "1": [[0, 1, 0], [1, 1, 0], [0, 1, 0], [0, 1, 0], [1, 1, 1]],
    "2": [[1, 1, 1], [0, 0, 1], [1, 1, 1], [1, 0, 0], [1, 1, 1]],
    "3": [[1, 1, 1], [0, 0, 1], [1, 1, 1], [0, 0, 1], [1, 1, 1]],
    "4": [[1, 0, 1], [1, 0, 1], [1, 1, 1], [0, 0, 1], [0, 0, 1]],
    "5": [[1, 1, 1], [1, 0, 0], [1, 1, 1], [0, 0, 1], [1, 1, 1]],
    "6": [[1, 1, 1], [1, 0, 0], [1, 1, 1], [1, 0, 1], [1, 1, 1]],
    "7": [[1, 1, 1], [0, 0, 1], [0, 1, 0], [0, 1, 0], [0, 1, 0]],
    "8": [[1, 1, 1], [1, 0, 1], [1, 1, 1], [1, 0, 1], [1, 1, 1]],
    "9": [[1, 1, 1], [1, 0, 1], [1, 1, 1], [0, 0, 1], [1, 1, 1]],
}


class RoundCounter:
    """Manages an 8x8 WS2812B/NeoPixel LED matrix panel to display round numbers.

    The display fits digits 00 to 99 simultaneously by placing two 3x5 digits
    at columns 0-2 and 4-6, centered vertically.
    """

    def __init__(
        self,
        pin: int,
        brightness: int = 64,
        zigzag: bool = True,
        color: Tuple[int, int, int] = (255, 255, 255),
    ):
        """Initializes the round counter.

        Args:
            pin (int): GPIO pin (BCM) driving the DIN of the matrix panel.
            brightness (int): Global brightness (0 to 255).
            zigzag (bool): Set to True if the physical matrix panel uses
                serpentine/zigzag layout; False for row-by-row progressive layout.
            color (Tuple[int, int, int]): The RGB color utilized to draw the digits.
        """
        self.pin = pin
        self.brightness = brightness
        self.zigzag = zigzag
        self.color = color
        self.current_value = -1  # Sentinel value to enforce rendering on first refresh

        self.strip = None
        if RPI_WS281X_AVAILABLE:
            # Map standard channels based on chosen GPIO pins on the Pi 4.
            # PWM0 channels are GPIO 12/18. PWM1 channels are GPIO 13/19.
            # SPI uses 10 (channel 0). PCM uses 21 (channel 0).
            channel = 0
            if pin in (13, 19):
                channel = 1

            try:
                self.strip = PixelStrip(
                    num=64,
                    pin=pin,
                    freq_hz=800_000,
                    dma=10,
                    invert=False,
                    brightness=brightness,
                    channel=channel,
                )
                self.strip.begin()
                self.clear()
            except Exception as e:
                logger.log(f"Unable to initialize PixelStrip on pin {pin}: {e}")
                self.strip = None

    def _get_pixel_index(self, row: int, col: int) -> int:
        """Translates 2D matrix row and column indices to 1D LED strip indices.

        Args:
            row (int): Vertical position index (0 to 7).
            col (int): Horizontal position index (0 to 7).

        Returns:
            int: The mapped position inside the 64-pixel buffer.
        """
        if self.zigzag:
            if row % 2 == 0:
                return row * 8 + col
            else:
                return row * 8 + (7 - col)
        else:
            return row * 8 + col

    def display_round(self, value: int) -> None:
        """Renders the given round number (0 to 99) onto the 8x8 grid.

        Args:
            value (int): Number representing the round.
        """
        # Constrain value strictly between 0 and 99
        val_clamped = max(0, min(99, value))

        if val_clamped == self.current_value:
            return  # Skip processing if the number has not changed

        self.current_value = val_clamped

        # Format integer to zero-padded 2-character string (e.g., 5 -> "05")
        val_str = f"{val_clamped:02d}"
        digit_tens = val_str[0]
        digit_units = val_str[1]

        # Start with an empty, dark frame buffer
        buffer = [(0, 0, 0)] * 64

        # Draw the Tens digit (columns 0-2, vertically offset by 1 row to center)
        tens_matrix = FONT_3X5.get(digit_tens, FONT_3X5["0"])
        for r_idx, row_data in enumerate(tens_matrix):
            row = r_idx + 1
            for col, active in enumerate(row_data):
                if active:
                    pixel_idx = self._get_pixel_index(row, col)
                    buffer[pixel_idx] = self.color

        # Draw the Units digit (columns 4-6, vertically offset by 1 row to center)
        units_matrix = FONT_3X5.get(digit_units, FONT_3X5["0"])
        for r_idx, row_data in enumerate(units_matrix):
            row = r_idx + 1
            for col_idx, active in enumerate(row_data):
                col = col_idx + 4
                if active:
                    pixel_idx = self._get_pixel_index(row, col)
                    buffer[pixel_idx] = self.color

        # Write the buffer array to the NeoPixel hardware
        if self.strip:
            for idx, rgb in enumerate(buffer):
                # Formulate standard 24-bit GRB/RGB hex representation
                color_val = (rgb[0] << 16) | (rgb[1] << 8) | rgb[2]
                self.strip.setPixelColor(idx, color_val)
            self.strip.show()

    def clear(self) -> None:
        """Resets all display pixels to the off state."""
        self.current_value = -1
        if self.strip:
            for idx in range(64):
                self.strip.setPixelColor(idx, 0)
            self.strip.show()
