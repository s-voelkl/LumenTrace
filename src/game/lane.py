# class Lane with lane_id (static)

class Lane:
    # static line id
    __lane_count: int = 0
    
    def __init__(self):
        self.__lane_id = Lane.__lane_count
        Lane.__lane_count += 1
        
    def __del__(self):
        Lane.__lane_count -= 1
    
    @property
    def lane_id(self) -> int:
        return self.__lane_id