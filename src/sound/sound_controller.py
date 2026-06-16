import os
import time
import pygame

class SoundController:
    def __init__(self, base_volume=1.0, device_id=0):
        self.sound_directory = "./sound-files"
        self.base_volume = base_volume
        
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
        pygame.mixer.init()
        
        os.environ["SDL_AUDIODRIVER"] = "alsa"
        if device_id is not None:
            os.environ["SDL_AUDIO_DEVICE"] = f"hw:{device_id},0"

        self._sound_cache = {}

    def _get_sound(self, filename):
        if filename in self._sound_cache:
            return self._sound_cache[filename]
        
        filepath = os.path.join(self.sound_directory, filename)
        if not os.path.exists(filepath):
            print(f"Error: {filename} not found.")
            return None
            
        try:
            sound = pygame.mixer.Sound(filepath)
            self._sound_cache[filename] = sound
            return sound
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            return None

    def playStartSound(self, left_percent=100, right_percent=100):
        sound = self._get_sound("start_sound.mp3")
        if not sound:
            return
        
        sound.set_volume(self.base_volume)
        
        left_vol = (left_percent / 100.0) * self.base_volume
        right_vol = (right_percent / 100.0) * self.base_volume
        sound.set_volume((left_vol, right_vol))
        
        sound.play()

    def playCarSound(self, speed, left_percent=100, right_percent=100, max_speed=200):
        filename = "engine_loop.mp3"
        sound = self._get_sound(filename)
        if not sound:
            return

        speed_ratio = max(0.1, speed / max_speed)
        
        original_freq = 44100 
        new_freq = int(original_freq * speed_ratio)
        
        sound.set_frequency(new_freq)

        left_vol = (left_percent / 100.0) * self.base_volume
        right_vol = (right_percent / 100.0) * self.base_volume
        sound.set_volume((left_vol, right_vol))

        channel = sound.play(loops=-1)
        
        return channel

    def updateCarSoundSpeed(self, channel, speed, max_speed=200):
        if channel and channel.get_busy():
            speed_ratio = max(0.1, speed / max_speed)
            new_freq = int(44100 * speed_ratio)
            channel.set_frequency(new_freq)

    def play_idle_music(self):
        filename = "idle_music.mp3"
        sound = self._get_sound(filename)
        
        if not sound:
            return
        
        sound.set_volume(self.base_volume)
        channel = sound.play(loops=-1)
        
        return channel
    
    def playCrashSound(self, left_percent=100, right_percent=100):
        filename = "crash_sound.mp3"
        sound = self._get_sound(filename)
        
        if not sound:
            return
    
        left_vol = (left_percent / 100.0) * self.base_volume
        right_vol = (right_percent / 100.0) * self.base_volume
        
        sound.set_volume((left_vol, right_vol))
        
        sound.play()


    """def playSuperSonicSound(self, left_percent=100, right_percent=100):
        filename = "superSonic_sound.mp3"
        sound = self._get_sound(filename)
        
        if not sound:
            return
    
        left_vol = (left_percent / 100.0) * self.base_volume
        right_vol = (right_percent / 100.0) * self.base_volume
        
        sound.set_volume((left_vol, right_vol))
        
        sound.play()"""

    def stop_all(self):
        pygame.mixer.stop()
