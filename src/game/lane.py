# class Lane with lane_id (static)

class Lane:
    '''Lane class representing a lane on the track. 
    Each lane has a unique lane_id assigned sequentially starting from 0.
    Lanes must be ordered from left to right, with the leftmost lane having the lowest lane_id!

    Returns:
        Lane: An instance of the Lane class.
    '''
    
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