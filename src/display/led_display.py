try:
    from rpi_ws281x import PixelStrip, Color
    RPI_WS281X_AVAILABLE = True
except ImportError:
    RPI_WS281X_AVAILABLE = False
    PixelStrip = None
    Color = None

from src.game.lane import Lane

class VirtualLedStrip:
    """
    Represents a virtual LED strip mapped to a single Lane.
    
    This allows a physical LED strip to be logically divided into multiple
    virtual strips, each corresponding to a different game lane or segment.
    
    Attributes:
        lane (Lane): The game lane associated with this virtual strip.
        real_strip_id (int): The ID of the physical strip this virtual strip belongs to.
        min_index (int): The minimum pixel index on the physical strip.
        max_index (int): The maximum pixel index on the physical strip.
        length (int): The total number of pixels in this virtual strip.
    """
    def __init__(self, lane: Lane, real_strip_id: int, min_index: int, max_index: int):
        """
        Initialize a VirtualLedStrip.
        
        Args:
            lane (Lane): The lane to map to this virtual strip.
            real_strip_id (int): The ID of the backing physical LED strip.
            min_index (int): The starting index on the physical strip.
            max_index (int): The ending index on the physical strip (inclusive).
        """
        self.lane = lane
        self.real_strip_id = real_strip_id
        self.min_index = min_index
        self.max_index = max_index
        self.length = max_index - min_index + 1

    def get_real_index(self, relative_position: float) -> int:
        """
        Get the physical LED index corresponding to a relative position on the lane.
        
        Args:
            relative_position (float): The relative position on the lane, from 0.0 to 1.0.
            
        Returns:
            int: The index on the physical LED strip.
        """
        clamped_relative_position = max(0.0, min(1.0, relative_position))
        return self.min_index + int(clamped_relative_position * (self.length - 1))

class LedDisplay:
    """
    Holds the internal array representing the LEDs, and pushes updates to physical strips.
    
    This class abstracts away the physical LED strip mapping and provides a
    logical interface for setting colors on a per-lane basis.
    
    Attributes:
        real_strips (dict[int, PixelStrip]): Mapping of physical strip IDs to PixelStrip instances.
        virtual_strips (list[VirtualLedStrip]): List of virtual strips mapped to lanes.
        virtual_arrays (dict[int, list[tuple[int, int, int]]]): Internal RGB color arrays per lane ID.
    """
    def __init__(self, real_strips: dict[int, PixelStrip], virtual_strips: list[VirtualLedStrip]): # type: ignore
        """
        Initialize the Display instance.
        
        Args:
            real_strips (dict[int, PixelStrip]): Dictionary mapping IDs to py physical strips.
            virtual_strips (list[VirtualLedStrip]): List of virtual strip mappings.
        """
        self.real_strips = real_strips
        self.virtual_strips = virtual_strips
        
        # Internal array: Dict[lane_id, list of colors (r,g,b)]
        self.virtual_arrays: dict[int, list[tuple[int, int, int]]] = {}
        for vs in virtual_strips:
            self.virtual_arrays[vs.lane.lane_id] = [(0, 0, 0)] * vs.length
        # Notes:
        # - `virtual_arrays` holds a per-lane list of RGB tuples. The display
        #   manager updates these lists and `render()` translates them to the
        #   underlying physical strips.
        # - Virtual strips allow splitting a physical strip into multiple
        #   logical lanes. The mapping between virtual and real indices is
        #   maintained by `VirtualLedStrip` instances.

    def clear(self):
        """
        Clear the internal virtual LED arrays by setting all pixels to black (0, 0, 0).
        
        Returns:
            None
        """
        for lane_id in self.virtual_arrays:
            length = len(self.virtual_arrays[lane_id])
            self.virtual_arrays[lane_id] = [(0, 0, 0)] * length
        # Clear leaves the virtual buffers in a consistent black state so that
        # subsequent rendering stages can apply layered updates deterministically.

    def _scale_color_ratio(
        self,
        color: tuple[int, int, int],
        relative_to_black_ratio: float,
    ) -> tuple[int, int, int]:
        """
        Scale an RGB color relative to black using a ratio in the range [0.0, 1.0].

        Example: (100, 100, 100) with 0.1 becomes (10, 10, 10).
        """
        clamped_ratio = max(0.0, min(1.0, float(relative_to_black_ratio)))
        return (
            int(color[0] * clamped_ratio),
            int(color[1] * clamped_ratio),
            int(color[2] * clamped_ratio),
        )

    def set_lane_pixel_by_relative_position(
        self,
        lane: Lane,
        relative_position: float,
        color: tuple[int, int, int],
        color_ratio: float = 1.0,
    ):
        """
        Set a single pixel's color on a specific lane based on a position ratio.
        
        Args:
            lane (Lane): The lane to update.
            relative_position (float): The relative position on the lane (0.0 to 1.0).
            color (tuple[int, int, int]): The RGB color to set.
            
        Returns:
            None
        """
        if lane.lane_id in self.virtual_arrays:
            arr = self.virtual_arrays[lane.lane_id]
            idx = int(relative_position * (len(arr) - 1))
            idx = max(0, min(len(arr)-1, idx))
            scaled = self._scale_color_ratio(color, color_ratio)
            arr[idx] = scaled
            # Single pixel updates are intentionally in-place; higher-priority
            # renderers can overwrite the same index during the update cycle.

    def set_lane_pixel_by_ratio(self, lane: Lane, ratio: float, color: tuple[int, int, int]):
        """Backward-compatible alias for `set_lane_pixel_by_relative_position`."""
        self.set_lane_pixel_by_relative_position(lane, ratio, color)

    def set_lane_pixel_window_by_relative_position(
        self,
        lane: Lane,
        relative_position: float,
        color: tuple[int, int, int],
        pixel_count: int = 3,
    ):
        """Paint a centered pixel window around a relative lane position.

        The window wraps around the lane buffer so vehicles near the start or
        end of a circular track remain visually contiguous.
        """
        if lane.lane_id not in self.virtual_arrays:
            return

        arr = self.virtual_arrays[lane.lane_id]
        if not arr:
            return

        clamped_relative_position = max(0.0, min(1.0, relative_position))
        window_size = max(1, int(pixel_count))
        center_idx = int(clamped_relative_position * (len(arr) - 1))
        start_idx = center_idx - (window_size // 2)

        for offset in range(window_size):
            arr[(start_idx + offset) % len(arr)] = color

    def fill_lane(
        self,
        lane: Lane,
        color: tuple[int, int, int],
        color_ratio: float = 1.0,
    ):
        """
        Fill an entire lane's virtual strip with a specific color.
        
        Args:
            lane (Lane): The lane to update.
            color (tuple[int, int, int]): The RGB color to set.
            color_ratio (float): Color ratio. Multiplier from black (0.0-1.0).
            
        Returns:
            None
        """
        if lane.lane_id in self.virtual_arrays:
            length = len(self.virtual_arrays[lane.lane_id])
            scaled_color = self._scale_color_ratio(color, color_ratio)
            self.virtual_arrays[lane.lane_id] = [scaled_color] * length
            # Full-lane fills are used for animations and module-wide effects.

    def fill_lane_section_by_relative_position(
        self,
        lane: Lane,
        start_relative_position: float,
        end_relative_position: float,
        color: tuple[int, int, int],
        color_ratio: float = 1.0,
    ):
        """
        Fill a specific section of a lane's virtual strip with a color.
        
        Args:
            lane (Lane): The lane to update.
            start_relative_position (float): The starting relative position (0.0 to 1.0).
            end_relative_position (float): The ending relative position (0.0 to 1.0).
            color (tuple[int, int, int]): The RGB color to set.
            color_ratio (float): Color ratio. Multiplier from black (0.0-1.0).
            
        Returns:
            None
        """
        if lane.lane_id in self.virtual_arrays:
            arr = self.virtual_arrays[lane.lane_id]
            start_idx = int(start_relative_position * (len(arr) - 1))
            end_idx = int(end_relative_position * (len(arr) - 1))
            start_idx = max(0, min(len(arr)-1, start_idx))
            end_idx = max(0, min(len(arr)-1, end_idx))
            scaled_color = self._scale_color_ratio(color, color_ratio)
            for i in range(start_idx, end_idx + 1):
                arr[i] = scaled_color
            # Section fills operate on index ranges calculated from ratios so
            # that rendering logic remains independent from the physical strip
            # length.

    def render(self):
        """
        Push the internal virtual LED arrays to the physical LED strips.
        
        This translates the logical lane colors into physical pixel colors
        and calls the show() method on the physical strips if available.
        
        Returns:
            None
        """
        
        # Attempt to push the virtual buffers to the real hardware. When the
        # rpi_ws281x library is not available (e.g. during unit tests on a
        # developer machine) this function is a no-op.
        # TODO: optimize to only write diffs to the strips to reduce latency.
        if not RPI_WS281X_AVAILABLE:
            return

        for vs in self.virtual_strips:
            strip = self.real_strips.get(vs.real_strip_id)
            if strip:
                arr = self.virtual_arrays.get(vs.lane.lane_id, [])
                if Color is None:
                    continue
                for i, color in enumerate(arr):
                    real_idx = vs.min_index + i
                    strip.setPixelColor(real_idx, Color(color[0], color[1], color[2]))
                
        # Request the physical strips to show the pushed colors.
        for strip in self.real_strips.values():
            strip.show()
