"""Per-vehicle motor sound handling.

This module provides :class:`MotorSound`, a small data model that owns the
continuous engine sound of a single vehicle. It wraps a looping engine sample
played through a shared :class:`~src.sound.sound_manager.SoundManager` and
modulates the playback in real time:

* The **background** of the engine (pitch and base loudness) follows the
  vehicle speed.
* The **acceleration** layer adds extra loudness while the vehicle accelerates.
* The **stereo balance** follows the current track module so the sound is
  panned left or right depending on where the vehicle currently is.
"""

from typing import Optional

from .sound_manager import GameSound, SoundManager


def _clamp_unit(value: float) -> float:
    """Clamp a value into the inclusive [0.0, 1.0] range."""
    return min(1.0, max(0.0, value))


class MotorSound:
    """Continuous engine sound for a single vehicle.

    A looping engine sample is played through the shared sound manager. The
    pitch and volume are continuously adjusted to reflect the vehicle's speed
    and acceleration, while the stereo balance reflects the active track module.

    Attributes:
        min_pitch (float): Pitch multiplier used when the vehicle is idle.
        max_pitch (float): Pitch multiplier used at full speed.
        idle_volume (float): Base volume (0-100) of the idling engine.
        max_volume (float): Volume (0-100) reached at full speed.
        acceleration_volume_boost (float): Additional volume (0-100) applied
            proportionally to the current acceleration.
    """

    def __init__(
        self,
        sound_manager: Optional[SoundManager],
        sound: GameSound = GameSound.ENGINE,
        min_pitch: float = 0.7,
        max_pitch: float = 2.4,
        idle_volume: float = 12.0,
        max_volume: float = 42.0,
        acceleration_volume_boost: float = 8.0,
    ):
        """Initialize the motor sound controller.

        Args:
            sound_manager (SoundManager | None): Shared audio manager used for
                playback. When ``None`` all operations become no-ops, which
                keeps the model usable in headless simulations and tests.
            sound (GameSound): Engine sample to loop.
            min_pitch (float): Idle pitch multiplier.
            max_pitch (float): Full-speed pitch multiplier.
            idle_volume (float): Idle volume between 0 and 100.
            max_volume (float): Full-speed volume between 0 and 100.
            acceleration_volume_boost (float): Extra volume added when
                accelerating, between 0 and 100.
        """
        self._sound_manager = sound_manager
        self._sound = sound
        self._min_pitch = min_pitch
        self._max_pitch = max_pitch
        self._idle_volume = idle_volume
        self._max_volume = max_volume
        self._acceleration_volume_boost = acceleration_volume_boost
        self._sound_id: Optional[str] = None

    def start(self) -> None:
        """Start the looping engine sound.

        Does nothing when no sound manager is configured or when the engine
        loop is already running.
        """
        if self._sound_manager is None or self._sound_id is not None:
            return

        self._sound_id = self._sound_manager.play(
            self._sound,
            loop=True,
            pitch=self._min_pitch,
            volume=self._idle_volume,
            left_volume=50.0,
            right_volume=50.0,
        )

    def update(
        self,
        speed_ratio: float,
        acceleration_ratio: float,
        stereo_ratio_left: float = 0.5,
    ) -> None:
        """Update the engine sound to reflect the current vehicle state.

        Args:
            speed_ratio (float): Normalized speed in [0.0, 1.0] driving the
                background pitch and volume of the engine.
            acceleration_ratio (float): Normalized acceleration in [0.0, 1.0]
                adding an extra volume boost on top of the background sound.
            stereo_ratio_left (float): Left-channel ratio in [0.0, 1.0]; the
                right channel uses ``1.0 - stereo_ratio_left``.
        """
        if self._sound_manager is None or self._sound_id is None:
            return

        speed_ratio = _clamp_unit(speed_ratio)
        acceleration_ratio = _clamp_unit(acceleration_ratio)
        stereo_ratio_left = _clamp_unit(stereo_ratio_left)

        pitch = self._min_pitch + speed_ratio * (self._max_pitch - self._min_pitch)
        volume = (
            self._idle_volume
            + speed_ratio * (self._max_volume - self._idle_volume)
            + acceleration_ratio * self._acceleration_volume_boost
        )

        # The sound manager expects channel volumes on a 0-100 scale.
        left_volume = stereo_ratio_left * 100.0
        right_volume = (1.0 - stereo_ratio_left) * 100.0

        self._sound_manager.update_sound(
            self._sound_id,
            pitch=pitch,
            volume=volume,
            left_volume=left_volume,
            right_volume=right_volume,
        )

    def stop(self) -> None:
        """Stop the looping engine sound, if it is running."""
        if self._sound_manager is None or self._sound_id is None:
            return

        self._sound_manager.stop_sound(self._sound_id)
        self._sound_id = None
