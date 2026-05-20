try:
    from rpi_ws281x import PixelStrip, Color
    RPI_WS281X_AVAILABLE = True
except ImportError:
    RPI_WS281X_AVAILABLE = False
    PixelStrip = None
    Color = None

from src.game.lane import Lane

class VirtualLedStrip:
    """Represents a virtual LED strip mapped to a single Lane."""
    def __init__(self, lane: Lane, real_strip_id: int, min_index: int, max_index: int):
        self.lane = lane
        self.real_strip_id = real_strip_id
        self.min_index = min_index
        self.max_index = max_index
        self.length = max_index - min_index + 1

    def get_real_index(self, position_ratio: float) -> int:
        ratio = max(0.0, min(1.0, position_ratio))
        return self.min_index + int(ratio * (self.length - 1))

class Display:
    """Holds the internal array representing the LEDs, and pushes updates to physical strips."""
    def __init__(self, real_strips: dict[int, PixelStrip], virtual_strips: list[VirtualLedStrip]):
        self.real_strips = real_strips
        self.virtual_strips = virtual_strips
        
        # Internal array: Dict[lane_id, list of colors (r,g,b)]
        self.virtual_arrays: dict[int, list[tuple[int, int, int]]] = {}
        for vs in virtual_strips:
            self.virtual_arrays[vs.lane.lane_id] = [(0, 0, 0)] * vs.length

    def clear(self):
        for lane_id in self.virtual_arrays:
            length = len(self.virtual_arrays[lane_id])
            self.virtual_arrays[lane_id] = [(0, 0, 0)] * length

    def set_lane_pixel_by_ratio(self, lane: Lane, ratio: float, color: tuple[int,int,int]):
        if lane.lane_id in self.virtual_arrays:
            arr = self.virtual_arrays[lane.lane_id]
            idx = int(ratio * (len(arr) - 1))
            idx = max(0, min(len(arr)-1, idx))
            arr[idx] = color

    def fill_lane(self, lane: Lane, color: tuple[int,int,int]):
        if lane.lane_id in self.virtual_arrays:
            length = len(self.virtual_arrays[lane.lane_id])
            self.virtual_arrays[lane.lane_id] = [color] * length

    def fill_lane_section_by_ratio(self, lane: Lane, start_ratio: float, end_ratio: float, color: tuple[int,int,int]):
        if lane.lane_id in self.virtual_arrays:
            arr = self.virtual_arrays[lane.lane_id]
            start_idx = int(start_ratio * (len(arr) - 1))
            end_idx = int(end_ratio * (len(arr) - 1))
            start_idx = max(0, min(len(arr)-1, start_idx))
            end_idx = max(0, min(len(arr)-1, end_idx))
            for i in range(start_idx, end_idx + 1):
                arr[i] = color

    def render(self):
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
