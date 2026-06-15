import threading
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Union
import numpy as np
import sounddevice as sd
import soundfile as sf

_MAX_VOLUME = 50.0
_MIN_VOLUME = 0.0
_DEFAULT_CHANNELS = 2
_DEFAULT_SAMPLE_RATE = 44100
_EASING_FACTOR = 0.05


@dataclass(frozen=True)
class SoundEffect:
    """Immutable catalog entry describing a single playable sound asset.

    Attributes:
        display_name (str): Human readable name of the sound effect.
        path (str): Relative path to the audio file on disk.
    """

    display_name: str
    path: str


class GameSound(Enum):
    """Structured catalog of all game sound effects.

    Each member pairs a friendly display name with the source path of the
    audio file. Sources are documented in ``README.md``. Use the members of
    this enum (for example ``GameSound.CAR_LAP_1``) when triggering sounds so
    that call sites stay decoupled from concrete file paths.
    """

    ENGINE = SoundEffect("Engine Loop", "assets/sound/base-engine.wav")
    START_SIGNAL = SoundEffect(
        "Start Signal 3-2-1-Go", "assets/sound/startup-sound.mp3"
    )
    CAR_CRASH_1 = SoundEffect("Car Crash 1", "assets/sound/car-crash-1.mp3")
    CAR_CRASH_2 = SoundEffect("Car Crash 2", "assets/sound/car-crash-2.mp3")
    CAR_LAP_1 = SoundEffect("Lap Complete 1", "assets/sound/car-lap-1.mp3")
    CAR_LAP_2 = SoundEffect("Lap Complete 2", "assets/sound/car-lap-2.mp3")
    RACE_FINISH = SoundEffect("Race Finish", "assets/sound/race-finish.mp3")
    COIN_1 = SoundEffect("Coin 1", "assets/sound/coin-1.mp3")
    COIN_2 = SoundEffect("Coin 2", "assets/sound/coin-2.mp3")
    WARNING_1 = SoundEffect("Warning 1", "assets/sound/warning-1.mp3")

    @property
    def display_name(self) -> str:
        """Return the human readable name of this sound effect."""
        return self.value.display_name

    @property
    def path(self) -> str:
        """Return the source file path of this sound effect."""
        return self.value.path


# Backwards compatible mapping of logical lowercase names to source paths.
# Derived from ``GameSound`` so the catalog stays single-sourced.
AVAILABLE_SOUNDS: Dict[str, str] = {
    sound.name.lower(): sound.path for sound in GameSound
}


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
        right_volume: float = 100.0,
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
        self.left_volume += (
            self.target_left_volume - self.left_volume
        ) * _EASING_FACTOR
        self.right_volume += (
            self.target_right_volume - self.right_volume
        ) * _EASING_FACTOR


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

    @staticmethod
    def _resolve_path(sound: Union["GameSound", str]) -> str:
        """Resolve a sound reference to a concrete file path.

        Args:
            sound (GameSound | str): A ``GameSound`` member, a logical
                lowercase name (see ``AVAILABLE_SOUNDS``), or a direct path.

        Returns:
            str: The resolved file path of the audio asset.
        """
        if isinstance(sound, GameSound):
            return sound.path
        return AVAILABLE_SOUNDS.get(sound, sound)

    def _load_audio(self, file_path_or_name: Union["GameSound", str]) -> np.ndarray:
        """Loads and caches audio data from a WAV or MP3 file (or logical name), converting to mono internally."""
        file_path = self._resolve_path(file_path_or_name)

        if file_path not in self._audio_cache:
            # Soundfile >= 1.2.0 supports MP3 directly from libsndfile.
            data, fs = sf.read(file_path, dtype="float32")  # type: ignore
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
        out = np.zeros((frames, _DEFAULT_CHANNELS), dtype="float32")

        with self._lock:
            # Update master volume easing
            self._master_volume += (
                self._target_master_volume - self._master_volume
            ) * _EASING_FACTOR
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
            self._target_master_volume = max(
                _MIN_VOLUME, min(_MAX_VOLUME, float(volume))
            )

    def play(
        self,
        sound_name_or_path: Union["GameSound", str],
        loop: bool = False,
        pitch: float = 1.0,
        volume: float = 100.0,
        left_volume: float = 100.0,
        right_volume: float = 100.0,
    ) -> str:
        """
        Starts playing a sound file or logical sound name.

        :param sound_name_or_path: A GameSound member, logical name from AVAILABLE_SOUNDS or path to the audio file (WAV/MP3).
        :param loop: Whether the sound should loop endlessly.
        :param pitch: Speed/pitch multiplier (1.0 = normal).
        :param volume: Overall volume of this sound (0-100).
        :param left_volume: Left speaker modifier (0-100).
        :param right_volume: Right speaker modifier (0-100).
        :return: Unique string ID identifying the playback instance.
        """
        audio_data = self._load_audio(sound_name_or_path)
        instance = PlaybackInstance(
            audio_data=audio_data,
            loop=loop,
            pitch=pitch,
            volume=volume,
            left_volume=left_volume,
            right_volume=right_volume,
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
        right_volume: Optional[float] = None,
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
                instance.target_left_volume = PlaybackInstance._clamp_volume(
                    left_volume
                )
            if right_volume is not None:
                instance.target_right_volume = PlaybackInstance._clamp_volume(
                    right_volume
                )

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
                callback=self._audio_callback,
            )
            self._stream.start()  # type: ignore

    def stop_all(self) -> None:
        """Stops the audio stream and clears all playing sounds."""
        with self._lock:
            self._active_sounds.clear()

        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None


# example run scripts
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
                sound_name_or_path=dummy_wav,
                loop=True,
                pitch=1.0,
                volume=100.0,
                left_volume=0.0,
                right_volume=100.0,
            )
        except Exception as e:
            print(f"Could not load wave file {dummy_wav}: {e}")
            manager.stop_all()
            return

        time.sleep(2)

        print(
            "Playing a second sound over overlapping the first (both speakers, pitched up)..."
        )
        # 4. Play a second sound overlapping the first using its logical name
        try:
            sound2_id = manager.play(
                sound_name_or_path="bump",  # Resolved automatically via AVAILABLE_SOUNDS
                loop=False,
                pitch=1.5,
                volume=60.0,
                left_volume=100.0,
                right_volume=100.0,
            )
        except Exception:
            pass

        time.sleep(1)

        print("Playing a third sound (MP3 format) on the left speaker...")
        # 4.5 Play an MP3 sound (assuming the file exists)
        try:
            sound3_id = manager.play(
                sound_name_or_path="start_signal",
                loop=False,
                pitch=1.0,
                volume=80.0,
                left_volume=100.0,
                right_volume=0.0,
            )
        except Exception:
            print("Start signal MP3 not found, skipping...")

        time.sleep(2)

        # 5. Dynamically change properties for the first sound without stopping it
        print("Moving the first sound to the center and lowering pitch...")
        manager.update_sound(
            sound1_id, pitch=0.8, left_volume=100.0, right_volume=100.0
        )

        time.sleep(2)

        # 6. Stop all sounds and shut down the output stream
        print("Stopping all sounds.")
        manager.stop_all()

    example_usage()
