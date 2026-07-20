import queue
import threading
import uuid
from typing import Any, Dict, Optional
import numpy as np
from src.logger.multi_logger import get_logger
from src.sound.sound_manager import GameSound, PlaybackInstance, SoundManager

logger = get_logger()


class ThreadedSoundManager:
    """A thread-safe, non-blocking asynchronous wrapper around SoundManager.

    This class decouples the calling game threads (e.g., physics, rendering,
    or input processing threads) from the sound manager's internal locking.
    It queues all play, update, and stop requests into a thread-safe Queue,
    which are sequentially executed by a dedicated background worker thread.
    
    It exposes the same public interface as SoundManager, allowing it to act
    as a transparent, drop-in replacement.
    """

    def __init__(self, sound_manager: SoundManager):
        """Initialize the threaded wrapper.

        Args:
            sound_manager (SoundManager): The synchronous sound manager instance
                to wrap and manage.
        """
        self._manager: SoundManager = sound_manager
        self._queue: queue.Queue = queue.Queue()
        self._worker_thread: Optional[threading.Thread] = None
        self._running: bool = False

    def start(self) -> None:
        """Starts the underlying audio streams and spawns the background worker thread."""
        if self._running:
            return

        logger.log("Starting Threaded Sound Manager...")

        # Start the low-level sound manager (preloading assets and opening streams)
        self._manager.start()

        self._running = True
        self._worker_thread = threading.Thread(
            target=self._process_queue,
            name="SoundWorkerThread",
            daemon=True,
        )
        self._worker_thread.start()
        logger.log("Sound background worker thread started successfully.")

    def _process_queue(self) -> None:
        """Continuously pulls and executes sound commands from the FIFO queue."""
        while self._running:
            try:
                # Use a timeout so that the loop can check the self._running flag periodically
                command = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue

            try:
                cmd_type, args, kwargs = command

                if cmd_type == "play":
                    sound_id, sound, loop, pitch, volume, left_volume, right_volume = (
                        args
                    )
                    self._play_on_manager(
                        sound_id, sound, loop, pitch, volume, left_volume, right_volume
                    )
                elif cmd_type == "update_sound":
                    sound_id, pitch, volume, left_volume, right_volume = args
                    self._manager.update_sound(
                        sound_id=sound_id,
                        pitch=pitch,
                        volume=volume,
                        left_volume=left_volume,
                        right_volume=right_volume,
                    )
                elif cmd_type == "stop_sound":
                    sound_id = args[0]
                    self._manager.stop_sound(sound_id)
                elif cmd_type == "stop_all":
                    # Clear active playback dictionary without closing the PortAudio stream.
                    # This ensures sound remains functional across subsequent race restarts.
                    with self._manager._lock:
                        self._manager._active_sounds.clear()
                elif cmd_type == "set_master_volume":
                    volume = args[0]
                    self._manager.set_master_volume(volume)

            except Exception as e:
                logger.log(f"Error executing command in SoundWorkerThread: {e}")
            finally:
                self._queue.task_done()

    def _play_on_manager(
        self,
        sound_id: str,
        sound: GameSound,
        loop: bool,
        pitch: float,
        volume: float,
        left_volume: float,
        right_volume: float,
    ) -> None:
        """Directly loads and registers a play instance on the underlying manager.

        Bypasses the original manager's UUID generation to ensure that the pre-generated
        ID is used for tracking across threads.
        """
        try:
            audio_data = self._manager._load_audio(sound)
            instance = PlaybackInstance(
                audio_data=audio_data,
                loop=loop,
                pitch=pitch,
                volume=volume,
                left_volume=left_volume,
                right_volume=right_volume,
            )

            with self._manager._lock:
                self._manager._active_sounds[sound_id] = instance
        except Exception as e:
            logger.log(f"Failed asynchronous play for {sound.display_name}: {e}")

    # --- Public API (Non-blocking Proxies) ---

    def play(
        self,
        sound: GameSound,
        loop: bool = False,
        pitch: float = 1.0,
        volume: float = 100.0,
        left_volume: float = 100.0,
        right_volume: float = 100.0,
    ) -> str:
        """Asynchronously schedules a sound to play.

        Generates a unique ID on the calling thread immediately so the game loop
        can reference it without waiting, then enqueues the request.
        """
        sound_id = str(uuid.uuid4())
        self._queue.put(
            (
                "play",
                (sound_id, sound, loop, pitch, volume, left_volume, right_volume),
                {},
            )
        )
        return sound_id

    def update_sound(
        self,
        sound_id: str,
        pitch: Optional[float] = None,
        volume: Optional[float] = None,
        left_volume: Optional[float] = None,
        right_volume: Optional[float] = None,
    ) -> None:
        """Asynchronously registers real-time modifications for a playing sound."""
        self._queue.put(
            ("update_sound", (sound_id, pitch, volume, left_volume, right_volume), {})
        )

    def stop_sound(self, sound_id: str) -> None:
        """Asynchronously registers a stop request for a specific playing sound."""
        self._queue.put(("stop_sound", (sound_id,), {}))

    def stop_all(self) -> None:
        """Asynchronously stops all active sounds and resets the device queue."""
        self._queue.put(("stop_all", (), {}))

    def set_master_volume(self, volume: float) -> None:
        """Asynchronously updates the global master volume."""
        self._queue.put(("set_master_volume", (volume,), {}))

    def stop(self) -> None:
        """Gracefully halts the background thread and releases low-level resources."""
        self._running = False
        if self._worker_thread is not None:
            self._worker_thread.join(timeout=1.0)
            self._worker_thread = None
        self._manager.stop_all()
        logger.log("Threaded Sound Manager stopped.")
