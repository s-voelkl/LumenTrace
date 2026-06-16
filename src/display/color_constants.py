"""
Color constants used by the LED display subsystem.

This module exposes RGB tuples for colors that are referenced by the
display manager and LED rendering code. Inline comments document the
intended semantic use for each color to keep the visual language
consistent across the codebase.

All colors are expressed as (R, G, B) tuples with values in the range
[0, 255].
"""

GREEN = (0, 255, 0)           
BLUE = (0, 0, 255)            

RED = (255, 0, 0)             
ORANGE = (255, 165, 0)        
YELLOW = (255, 255, 0)        

DARK_PURPLE = (75, 0, 130)
PURPLE = (128, 0, 128)        
PINK = (255, 105, 180)        
LIGHT_PINK = (255, 182, 193)  

BLACK = (0, 0, 0)             
DARK_GRAY = (64, 64, 64)      
GRAY = (128, 128, 128)        
LIGHT_GRAY = (211, 211, 211)  
WHITE = (255, 255, 255)       

