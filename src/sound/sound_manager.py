import threading
import uuid
from typing import Dict, Optional
import numpy as np
import sounddevice as sd
import soundfile as sf

_MAX_VOLUME = 50.0
_MIN_VOLUME = 0.0
_DEFAULT_CHANNELS = 2
_DEFAULT_SAMPLE_RATE = 44100
_EASING_FACTOR = 0.05

class PlaybackInstance:
    """
    Represents an individual sound being played.
    Stores its own position, pitch, and volume properties.
    """
    def __init__(
        self,
        audio_data: np.ndarray,
        loop: bool = False,
        pitch: float = 1.0,
        volume: float = 100.0,
        left_volume: float = 100.0,
        right_volume: float = 100.0
    ):
        self.audio_data = audio_data
        self.loop = loop
        
        # Audio properties
        self.pitch = pitch
        self.target_pitch = pitch
        
        self.volume = self._clamp_volume(volume)
        self.target_volume = self.volume
        
        self.left_volume = self._clamp_volume(left_volume)
        self.target_left_volume = self.left_volume
        
        self.right_volume = self._clamp_volume(right_volume)
        self.target_right_volume = self.right_volume
        
        # Playback state
        self.position: float = 0.0
        self.is_finished: bool = False

    @staticmethod
    def _clamp_volume(vol: float) -> float:
        return max(_MIN_VOLUME, min(_MAX_VOLUME, vol))

    def update_easing(self) -> None:
        """Smoothly transitions properties towards their target values to prevent audio clipping/popping."""
        self.pitch += (self.target_pitch - self.pitch) * _EASING_FACTOR
        self.volume += (self.target_volume - self.volume) * _EASING_FACTOR
        self.left_volume += (self.target_left_volume - self.left_volume) * _EASING_FACTOR
        self.right_volume += (self.target_right_volume - self.right_volume) * _EASING_FACTOR


class SoundManager:
    """
    A generic audio manager to play and mix multiple sound files simultaneously.
    Provides support for master volume, per-sound volume, left/right panning, and pitch adjustment.
    """

    def __init__(self, sample_rate: int = _DEFAULT_SAMPLE_RATE):
        """
        Initializes the sound manager.
        
        :param sample_rate: The sample rate to use for the output stream.
        """
        self._sample_rate: int = sample_rate
        self._master_volume: float = 100.0
        self._target_master_volume: float = 100.0
        
        self._stream: Optional[sd.OutputStream] = None
        self._lock = threading.Lock()
        
        # Cache of loaded audio data to avoid reading from disk multiple times
        self._audio_cache: Dict[str, np.ndarray] = {}
        
        # Active sounds currently playing
        self._active_sounds: Dict[str, PlaybackInstance] = {}

    def _load_wav(self, file_path: str) -> np.ndarray:
        """Loads and caches audio data from a WAV file, converting to mono internally."""
        if file_path not in self._audio_cache:
            data, fs = sf.read(file_path, dtype='float32')  # type: ignore
            if len(data.shape) > 1:
                # Convert stereo to mono for easier independent panning
                data = data.mean(axis=1)
            # Simple resampling could be done here if fs != self._sample_rate
            self._audio_cache[file_path] = data
            
        return self._audio_cache[file_path]

    def _audio_callback(self, outdata: np.ndarray, frames: int, time, status) -> None:
        """
        Callback used by sounddevice to fetch the next chunk of mixed audio.
        """
        if status:
            print(f"Audio stream status: {status}")

        # Initialize output buffer to zeros
        out = np.zeros((frames, _DEFAULT_CHANNELS), dtype='float32')

        with self._lock:
            # Update master volume easing
            self._master_volume += (self._target_master_volume - self._master_volume) * _EASING_FACTOR
            master_multiplier = self._master_volume / _MAX_VOLUME
            
            finished_keys = []

            for sound_id, instance in self._active_sounds.items():
                if instance.is_finished:
                    finished_keys.append(sound_id)
                    continue

                data_len = len(instance.audio_data)

                for i in range(frames):
                    instance.update_easing()

                    # Stop processing this sound if it has finished
                    if not instance.loop and instance.position >= data_len - 1:
                        instance.is_finished = True
                        break

                    # Linear interpolation for playback
                    pos_int = int(instance.position)
                    pos_frac = instance.position - pos_int

                    idx1 = pos_int % data_len
                    idx2 = (pos_int + 1) % data_len

                    val1 = instance.audio_data[idx1]
                    val2 = instance.audio_data[idx2]

                    sample_val = val1 * (1.0 - pos_frac) + val2 * pos_frac

                    # Apply combined volumes (Master * Instance * Channel)
                    base_vol = master_multiplier * (instance.volume / _MAX_VOLUME)
                    left_mult = base_vol * (instance.left_volume / _MAX_VOLUME)
                    right_mult = base_vol * (instance.right_volume / _MAX_VOLUME)

                    # Mix into output block
                    out[i, 0] += sample_val * left_mult
                    out[i, 1] += sample_val * right_mult

                    instance.position += instance.pitch

            # Cleanup finished sounds
            for key in finished_keys:
                del self._active_sounds[key]

        outdata[:] = out

    def set_master_volume(self, volume: float) -> None:
        """
        Sets the global master volume.
        
        :param volume: Total volume between 0 and 100.
        """
        with self._lock:
            self._target_master_volume = max(_MIN_VOLUME, min(_MAX_VOLUME, float(volume)))

    def play(
        self,
        file_path: str,
        loop: bool = False,
        pitch: float = 1.0,
        volume: float = 100.0,
        left_volume: float = 100.0,
        right_volume: float = 100.0
    ) -> str:
        """
        Starts playing a sound file.
        
        :param file_path: Path to the WAV file.
        :param loop: Whether the sound should loop endlessly.
        :param pitch: Speed/pitch multiplier (1.0 = normal).
        :param volume: Overall volume of this sound (0-100).
        :param left_volume: Left speaker modifier (0-100).
        :param right_volume: Right speaker modifier (0-100).
        :return: Unique string ID identifying the playback instance.
        """
        audio_data = self._load_wav(file_path)
        instance = PlaybackInstance(
            audio_data=audio_data,
            loop=loop,
            pitch=pitch,
            volume=volume,
            left_volume=left_volume,
            right_volume=right_volume
        )
        
        sound_id = str(uuid.uuid4())
        with self._lock:
            self._active_sounds[sound_id] = instance
            
        return sound_id

    def update_sound(
        self,
        sound_id: str,
        pitch: Optional[float] = None,
        volume: Optional[float] = None,
        left_volume: Optional[float] = None,
        right_volume: Optional[float] = None
    ) -> None:
        """
        Updates properties of an actively playing sound seamlessly.
        
        :param sound_id: The ID of the playback instance returned by play().
        """
        with self._lock:
            instance = self._active_sounds.get(sound_id)
            if not instance:
                return
                
            if pitch is not None:
                instance.target_pitch = pitch
            if volume is not None:
                instance.target_volume = PlaybackInstance._clamp_volume(volume)
            if left_volume is not None:
                instance.target_left_volume = PlaybackInstance._clamp_volume(left_volume)
            if right_volume is not None:
                instance.target_right_volume = PlaybackInstance._clamp_volume(right_volume)

    def stop_sound(self, sound_id: str) -> None:
        """Stops a specific playing sound."""
        with self._lock:
            if sound_id in self._active_sounds:
                self._active_sounds[sound_id].is_finished = True

    def start(self) -> None:
        """Starts the audio output stream."""
        if self._stream is None:
            self._stream = sd.OutputStream(
                samplerate=self._sample_rate,
                channels=_DEFAULT_CHANNELS,
                callback=self._audio_callback
            )
            self._stream.start()

    def stop_all(self) -> None:
        """Stops the audio stream and clears all playing sounds."""
        with self._lock:
            self._active_sounds.clear()
            
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

if __name__ == "__main__":
    import time
    
    def example_usage():
        print("Initializing Sound Manager...")
        # 1. Initialize and start the global Sound Manager
        manager = SoundManager()
        manager.start()

        # 2. Adjust the global master volume
        manager.set_master_volume(80.0)

        print("Playing first sound exclusively on the right speaker...")
        # 3. Play a sound exclusively on the right speaker
        # Make sure to provide a valid wav file for your environment
        dummy_wav = "assets/sound/base_engine.wav" 
        try:
            sound1_id = manager.play(
                file_path=dummy_wav,
                loop=True,
                pitch=1.0,
                volume=100.0,
                left_volume=0.0,
                right_volume=100.0 
            )
        except Exception as e:
            print(f"Could not load wave file {dummy_wav}: {e}")
            manager.stop_all()
            return

        time.sleep(2)

        print("Playing a second sound over overlapping the first (both speakers, pitched up)...")
        # 4. Play a second sound overlapping the first
        try:
            sound2_id = manager.play(
                file_path=dummy_wav,
                loop=False, 
                pitch=1.5,
                volume=60.0,
                left_volume=100.0,
                right_volume=100.0
            )
        except Exception:
            pass

        time.sleep(2)

        # 5. Dynamically change properties for the first sound without stopping it
        print("Moving the first sound to the center and lowering pitch...")
        manager.update_sound(sound1_id, pitch=0.8, left_volume=100.0, right_volume=100.0)

        time.sleep(2)

        # 6. Stop all sounds and shut down the output stream
        print("Stopping all sounds.")
        manager.stop_all()

    example_usage()
