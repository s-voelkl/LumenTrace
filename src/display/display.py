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

    def get_real_index(self, position_ratio: float) -> int:
        """
        Get the physical LED index corresponding to a relative position on the lane.
        
        Args:
            position_ratio (float): The relative position on the lane, from 0.0 to 1.0.
            
        Returns:
            int: The index on the physical LED strip.
        """
        ratio = max(0.0, min(1.0, position_ratio))
        return self.min_index + int(ratio * (self.length - 1))

class Display:
    """
    Holds the internal array representing the LEDs, and pushes updates to physical strips.
    
    This class abstracts away the physical LED strip mapping and provides a
    logical interface for setting colors on a per-lane basis.
    
    Attributes:
        real_strips (dict[int, PixelStrip]): Mapping of physical strip IDs to PixelStrip instances.
        virtual_strips (list[VirtualLedStrip]): List of virtual strips mapped to lanes.
        virtual_arrays (dict[int, list[tuple[int, int, int]]]): Internal RGB color arrays per lane ID.
    """
    def __init__(self, real_strips: dict[int, PixelStrip], virtual_strips: list[VirtualLedStrip]):
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

    def clear(self):
        """
        Clear the internal virtual LED arrays by setting all pixels to black (0, 0, 0).
        
        Returns:
            None
        """
        for lane_id in self.virtual_arrays:
            length = len(self.virtual_arrays[lane_id])
            self.virtual_arrays[lane_id] = [(0, 0, 0)] * length

    def set_lane_pixel_by_ratio(self, lane: Lane, ratio: float, color: tuple[int,int,int]):
        """
        Set a single pixel's color on a specific lane based on a position ratio.
        
        Args:
            lane (Lane): The lane to update.
            ratio (float): The relative position on the lane (0.0 to 1.0).
            color (tuple[int, int, int]): The RGB color to set.
            
        Returns:
            None
        """
        if lane.lane_id in self.virtual_arrays:
            arr = self.virtual_arrays[lane.lane_id]
            idx = int(ratio * (len(arr) - 1))
            idx = max(0, min(len(arr)-1, idx))
            arr[idx] = color

    def fill_lane(self, lane: Lane, color: tuple[int,int,int]):
        """
        Fill an entire lane's virtual strip with a specific color.
        
        Args:
            lane (Lane): The lane to update.
            color (tuple[int, int, int]): The RGB color to set.
            
        Returns:
            None
        """
        if lane.lane_id in self.virtual_arrays:
            length = len(self.virtual_arrays[lane.lane_id])
            self.virtual_arrays[lane.lane_id] = [color] * length

    def fill_lane_section_by_ratio(self, lane: Lane, start_ratio: float, end_ratio: float, color: tuple[int,int,int]):
        """
        Fill a specific section of a lane's virtual strip with a color.
        
        Args:
            lane (Lane): The lane to update.
            start_ratio (float): The starting relative position (0.0 to 1.0).
            end_ratio (float): The ending relative position (0.0 to 1.0).
            color (tuple[int, int, int]): The RGB color to set.
            
        Returns:
            None
        """
        if lane.lane_id in self.virtual_arrays:
            arr = self.virtual_arrays[lane.lane_id]
            start_idx = int(start_ratio * (len(arr) - 1))
            end_idx = int(end_ratio * (len(arr) - 1))
            start_idx = max(0, min(len(arr)-1, start_idx))
            end_idx = max(0, min(len(arr)-1, end_idx))
            for i in range(start_idx, end_idx + 1):
                arr[i] = color

    def render(self):
        """
        Push the internal virtual LED arrays to the physical LED strips.
        
        This translates the logical lane colors into physical pixel colors
        and calls the show() method on the physical strips if available.
        
        Returns:
            None
        """
        
        # TODO: only send diff to led strip
        if not RPI_WS281X_AVAILABLE:
            return

        for vs in self.virtual_strips:
            strip = self.real_strips.get(vs.real_strip_id)
            if strip:
                arr = self.virtual_arrays.get(vs.lane.lane_id, [])
                for i, color in enumerate(arr):
                    real_idx = vs.min_index + i
                    strip.setPixelColor(real_idx, Color(color[0], color[1], color[2]))
                    
        for strip in self.real_strips.values():
            strip.show()
