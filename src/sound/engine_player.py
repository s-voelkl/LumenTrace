import threading
import numpy as np
import sounddevice as sd
import soundfile as sf

class EngineSoundPlayer:
    """
    Plays an engine sound file and allows dynamic, real-time pitch and speed shifting.
    Uses 'sounddevice' to stream audio and dynamically steps through the audio data
    to change the pitch based on the given speed.
    """

    def __init__(self, wav_file="assets/sound/base_engine.wav", min_pitch=0.8, max_pitch=3.0):
        self.wav_file = wav_file
        
        # Load audio data
        self.data, self.fs = sf.read(self.wav_file, dtype='float32')
        
        # Convert to mono if it's stereo
        if len(self.data.shape) > 1:
            self.data = self.data.mean(axis=1)
            
        self.stream = None
        self.position = 0.0
        
        # Speed represents throttle: 0.0 (idle) to 1.0 (max speed)
        self.speed = 0.0
        
        # Pitch multipliers limits
        self.min_pitch = min_pitch
        self.max_pitch = max_pitch
        self.current_pitch = self.min_pitch
        self.target_pitch = self.min_pitch
        
        # Stereo Panning: -1.0 (Left) to 1.0 (Right)
        self.current_pan = 0.0
        self.target_pan = 0.0
        
        self._lock = threading.Lock()

    def _audio_callback(self, outdata, frames, time, status):
        """
        Callback used by sounddevice to fetch the next chunk of audio.
        """
        if status:
            print(f"Audio stream status: {status}")
            
        # Allocate output buffer (2 channels for stereo)
        out = np.zeros((frames, 2), dtype='float32')
        data_len = len(self.data)
        
        # Iterate over the number of requested frames and interpolate pitch
        for i in range(frames):
            with self._lock:
                # Easing function for smooth pitch transition (keine Sprünge!)
                self.current_pitch += (self.target_pitch - self.current_pitch) * 0.005
                self.current_pan += (self.target_pan - self.current_pan) * 0.005
                pitch = self.current_pitch
                pan = self.current_pan
                
            # Lineare Interpolation zwischen zwei Samples für kristallklaren Sound
            pos_int = int(self.position)
            pos_frac = self.position - pos_int
            
            idx1 = pos_int % data_len
            idx2 = (pos_int + 1) % data_len
            
            val1 = self.data[idx1]
            val2 = self.data[idx2]
            
            sample_val = val1 * (1.0 - pos_frac) + val2 * pos_frac
            
            # Stereo Panning Math
            left_vol = min(1.0, 1.0 - pan)
            right_vol = min(1.0, 1.0 + pan)
            
            out[i, 0] = sample_val * left_vol  # Left channel
            out[i, 1] = sample_val * right_vol # Right channel
            
            self.position += pitch
            
        # Optional: Prevent position counter from growing indefinitely
        self.position %= data_len
        
        outdata[:] = out

    def set_speed(self, speed: float):
        """
        Changes the pitch of the motor sound dynamically.
        :param speed: Float between 0.0 (idle) and 1.0 (top speed)
        """
        speed = max(0.0, min(1.0, speed))  # Clamp between 0.0 and 1.0
        with self._lock:
            self.speed = speed
            # Map speed 0.0-1.0 to pitch range min_pitch-max_pitch target
            self.target_pitch = self.min_pitch + speed * (self.max_pitch - self.min_pitch)

    def set_pan(self, pan: float):
        """
        Changes the stereo panning dynamically.
        :param pan: Float from -1.0 (full left) to 1.0 (full right).
        """
        pan = max(-1.0, min(1.0, pan))
        with self._lock:
            self.target_pan = pan

    def start(self):
        """Starts real-time engine playback."""
        if self.stream is None:
            # Start asynchronous audio output stream (2 channels now)
            self.stream = sd.OutputStream(
                samplerate=self.fs, 
                channels=2, 
                callback=self._audio_callback
            )
            self.stream.start()

    def stop(self):
        """Stops the audio playback."""
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None
