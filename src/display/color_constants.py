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
LIGHT_BLUE = (28, 89, 255)
DARK_BLUE = (2, 8, 20)
TURQUOISE = (26, 188, 156)
LIME = (0, 207, 41)
BLUE_ORANGE = (231, 76, 107)

RED = (255, 0, 0)        
ORANGE = (242, 169, 11)    
YELLOW = (255, 255, 0)        

RED_PURPLISH = (255, 0, 30)
MAGENTA = (227, 0, 189)
DARK_PURPLE = (75, 0, 130)
SLIGHT_PURPLE = (10, 0, 20)
PURPLE = (128, 0, 128)   
PINK = (255, 105, 180)        
LIGHT_PINK = (249, 147, 252)

BLACK = (0, 0, 0)             
DARK_GRAY = (64, 64, 64)      
GRAY = (128, 128, 128)        
LIGHT_GRAY = (211, 211, 211)  
WHITE = (255, 255, 255)       

