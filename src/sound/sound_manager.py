import threading
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional
import numpy as np
import sounddevice as sd
import soundfile as sf
from src.logger.multi_logger import get_logger

logger = get_logger()

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

    ENGINE = SoundEffect("Engine Loop", "assets/sound/base-engine-1.wav")
    CAR_CRASH_1 = SoundEffect("Car Crash 1", "assets/sound/car-crash-1.mp3")
    CAR_CRASH_2 = SoundEffect("Car Crash 2", "assets/sound/car-crash-2.mp3")
    CAR_LAP_1 = SoundEffect("Lap Complete 1", "assets/sound/car-lap-1.mp3")
    CAR_LAP_2 = SoundEffect("Lap Complete 2", "assets/sound/car-lap-2.mp3")
    STARTUP = SoundEffect("Startup", "assets/sound/startup-1.mp3")
    RACE_FINISH = SoundEffect("Race Finish", "assets/sound/race-finish.mp3")
    GAME_INIT = SoundEffect("Game Init", "assets/sound/game-initialization.mp3")
    COIN_1 = SoundEffect("Coin 1", "assets/sound/coin-1.mp3")
    COIN_2 = SoundEffect("Coin 2", "assets/sound/coin-2.mp3")
    WARNING_1 = SoundEffect("Warning 1", "assets/sound/warning-1.mp3")
    WARNING_2 = SoundEffect("Warning 2", "assets/sound/warning-2.mp3")
    PUNCH_1 = SoundEffect("Punch 1", "assets/sound/punch-1.mp3")
    VIBE_1 = SoundEffect("Vibe 1", "assets/sound/vibe-1-retro.mp3")
    VIBE_2 = SoundEffect("Vibe 2", "assets/sound/vibe-2-retro.mp3")
    VIBE_3 = SoundEffect("Vibe 3", "assets/sound/vibe-3-retro.mp3")

    @property
    def display_name(self) -> str:
        """Return the human readable name of this sound effect."""
        return self.value.display_name

    @property
    def path(self) -> str:
        """Return the source file path of this sound effect."""
        return self.value.path


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


class SoundManager:
    """A comprehensive audio manager that mixes and plays multiple sound assets simultaneously.

    The SoundManager loads audio from the ``GameSound`` catalog, caches the
    underlying arrays to minimize disk I/O, and continuously mixes active
    playback instances using a background thread and a system output stream.
    It provides overarching controls such as a global master volume with easing,
    as well as real-time per-sound controls for volume, left/right stereo
    panning, and pitch adjustments.
    """

    def __init__(self, sample_rate: int = _DEFAULT_SAMPLE_RATE):
        """Initialize the sound manager with a specific target sample rate.

        Note that the manager does not start the audio stream immediately upon
        initialization. Call :meth:`start` to activate the playback thread.

        Args:
            sample_rate (int): The sample rate in Hz used for the output stream
                and mixing pipeline. Defaults to 44100 Hz.
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

    def _load_audio(self, sound: GameSound) -> np.ndarray:
        """Loads and caches audio data from a GameSound, converting to mono internally."""
        file_path = sound.path

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
        """Callback invoked by `sounddevice` to stream the next chunk of mixed audio.

        This method is called periodically by the background audio thread. It fills
        the provided output buffer (`outdata`) with the combined audio of all currently
        active sounds. To prevent audio artifacts like clicks or pops, any dynamic changes to
        pitch, volume, or stereo panning are smoothed out (eased) over the duration of the chunk.
        
        Optimized to perform block-level parameter updates and linear interpolation,
        drastically reducing the computational workload compared to sample-by-sample ramping.

        Args:
            outdata (np.ndarray): The numpy array to be filled with audio data.
                Its shape is `(frames, channels)`.
            frames (int): The number of sample frames requested by the system.
            time (CData): A CFFI struct containing timing information (ignored).
            status (CallbackFlags): Status flags indicating underflow/overflow.
        """
        # Initialize the output buffer with silence
        out = np.zeros((frames, _DEFAULT_CHANNELS), dtype="float32")

        with self._lock:
            # 1. Update the global master volume at the block level
            self._master_volume += _EASING_FACTOR * (self._target_master_volume - self._master_volume)
            master_mult = self._master_volume / _MAX_VOLUME

            finished_keys = []
            
            # Generate the frame indices once per callback instead of per-sound
            arange_frames = np.arange(frames, dtype=np.float32)

            # 2. Process each active playback instance
            for sound_id, instance in self._active_sounds.items():
                if instance.is_finished:
                    finished_keys.append(sound_id)
                    continue

                # Block-level easing for instance parameters (pitch, volume, panning)
                instance.pitch += _EASING_FACTOR * (instance.target_pitch - instance.pitch)
                instance.volume += _EASING_FACTOR * (instance.target_volume - instance.volume)
                instance.left_volume += _EASING_FACTOR * (instance.target_left_volume - instance.left_volume)
                instance.right_volume += _EASING_FACTOR * (instance.target_right_volume - instance.right_volume)

                data_len = len(instance.audio_data)
                pitch = instance.pitch

                # 3. Calculate source positions using constant pitch step across the block
                positions = instance.position + arange_frames * pitch
                valid_frames = frames

                # 4. Handle End-Of-File (EOF) for non-looping sounds
                if not instance.loop and positions[-1] >= data_len - 1:
                    # Find exactly how many frames we can play before hitting the end
                    valid_frames = int(np.searchsorted(positions, data_len - 1, side="right"))
                    instance.is_finished = True
                    finished_keys.append(sound_id)

                    if valid_frames == 0:
                        continue  # Sound finished exactly before this chunk started

                    positions = positions[:valid_frames]

                # Update the instance's read cursor for the next chunk callback
                instance.position = positions[-1]
                if instance.loop:
                    instance.position %= data_len

                # 5. Read source audio using fractional positions (Linear Interpolation)
                pos_int = positions.astype(np.int32)
                pos_frac = positions - pos_int

                if instance.loop:
                    idx1 = pos_int % data_len
                    idx2 = (pos_int + 1) % data_len
                else:
                    idx1 = np.minimum(pos_int, data_len - 1)
                    idx2 = np.minimum(pos_int + 1, data_len - 1)

                # Fetch adjacent samples and interpolate
                val1 = instance.audio_data[idx1]
                val2 = instance.audio_data[idx2]
                sample_vals = val1 * (1.0 - pos_frac) + val2 * pos_frac

                # 6. Apply block-level scalar volume and panning multipliers
                base_vol = master_mult * (instance.volume / _MAX_VOLUME)
                left_mult = base_vol * (instance.left_volume / _MAX_VOLUME)
                right_mult = base_vol * (instance.right_volume / _MAX_VOLUME)

                # Mix calculated frames directly into the global output buffer (scalar multiplication)
                out[:valid_frames, 0] += sample_vals * left_mult
                out[:valid_frames, 1] += sample_vals * right_mult

            # 7. Discard sounds that finished playing during this chunk
            for key in finished_keys:
                if key in self._active_sounds:
                    del self._active_sounds[key]

        # Commit the mixed chunk back to the sound device buffer
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
        sound: GameSound,
        loop: bool = False,
        pitch: float = 1.0,
        volume: float = 100.0,
        left_volume: float = 100.0,
        right_volume: float = 100.0,
    ) -> str:
        """
        Starts playing a sound from the GameSound catalog.

        :param sound: A GameSound member representing the audio asset to play.
        :param loop: Whether the sound should loop endlessly.
        :param pitch: Speed/pitch multiplier (1.0 = normal).
        :param volume: Overall volume of this sound (0-100).
        :param left_volume: Left speaker modifier (0-100).
        :param right_volume: Right speaker modifier (0-100).
        :return: Unique string ID identifying the playback instance.
        """
        audio_data = self._load_audio(sound)
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
        """Starts the audio output stream and preloads all sounds into memory."""
        for sound in GameSound:
            try:
                self._load_audio(sound)
            except Exception as e:
                logger.log(f"Failed to preload {sound.path}: {e}")

        try:
            if self._stream is None:
                # Attempt to create output stream on the default device
                self._stream = sd.OutputStream(
                    samplerate=self._sample_rate,
                    channels=_DEFAULT_CHANNELS,
                    callback=self._audio_callback,
                    blocksize=1024,  # Larger block size gives more execution time per callback
                    latency="high",  # Instructs the OS driver to use safer, larger buffer sizes
                )
                self._stream.start()
                logger.log("Audio stream started successfully.")
        except Exception as e:
            logger.log(f"Error starting audio stream: {e}")
            logger.log("Audio will be disabled. Game will continue without sound.")
            self._stream = None

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
        logger.log("Initializing Sound Manager...")
        # 1. Initialize and start the global Sound Manager
        manager = SoundManager()
        manager.start()

        # 2. Adjust the global master volume
        manager.set_master_volume(50.0)
        logger.log("Playing first sound exclusively on the right speaker...")

        # 3. Play a sound exclusively on the right speaker
        engine_sound = GameSound.ENGINE
        try:
            sound1_id = manager.play(
                sound=engine_sound,
                loop=True,
                pitch=1.0,
                volume=10.0,
                left_volume=0.0,
                right_volume=100.0,
            )
        except Exception as e:
            logger.log(f"Could not load wave file {engine_sound.path}: {e}")
            manager.stop_all()
            return

        time.sleep(0.5)

        logger.log(
            "Playing a second sound over overlapping the first (both speakers, pitched up)..."
        )

        # 4. Play a second sound overlapping the first
        coin2 = GameSound.COIN_2
        try:
            manager.play(
                sound=coin2,
                loop=False,
                pitch=1.5,
                volume=100.0,
                left_volume=100.0,
                right_volume=100.0,
            )
        except Exception as e:
            logger.log(f"Could not play sound '{coin2.display_name}': {e}")

        time.sleep(0.5)

        logger.log("Playing a third sound (MP3 format) on the left speaker...")

        # 5. Dynamically change properties for the first sound without stopping it
        logger.log("Moving the first sound to the center and lowering pitch...")
        manager.update_sound(sound1_id, pitch=0.8, left_volume=30.0, right_volume=30.0)

        time.sleep(0.5)

        # 6. Overlap with a second engine sound at a different pitch to create a richer effect
        logger.log(
            "Adding a second engine sound at a different pitch for a richer effect..."
        )
        try:
            manager.play(
                sound=engine_sound,
                loop=True,
                pitch=1.2,
                volume=10.0,
                left_volume=0.0,
                right_volume=100.0,
            )
        except Exception as e:
            logger.log(f"Could not load wave file {engine_sound.path}: {e}")

        time.sleep(0.5)

        # Add multiple sounds at once to demonstrate mixing
        logger.log("Adding multiple sounds at once to demonstrate mixing...")

        # play all sounds from the gamesound
        for sound in GameSound:
            try:
                manager.play(
                    sound=sound,
                    loop=False,
                    pitch=1.0,
                    volume=10.0,
                    left_volume=100.0,
                    right_volume=100.0,
                )
                time.sleep(0.5)
            except Exception as e:
                logger.log(f"Could not play sound '{sound.display_name}': {e}")

        time.sleep(2.0)

        # Stop all sounds and shut down the output stream
        logger.log("Stopping all sounds.")
        manager.stop_all()

    example_usage()