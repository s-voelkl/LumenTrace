import os
import numpy as np
import sounddevice as sd
from pydub import AudioSegment


class StereoAudioController:
    """A professional controller to manage and play MP3 audio files on a

    Raspberry Pi with independent control over the left and right stereo
    channels.
    """

    def __init__(self, file_path: str):
        """Initializes the audio controller and loads the specified MP3 file.

        :param file_path: Path to the input MP3 audio file.
        :raises FileNotFoundError: If the specified file does not exist.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found at: {file_path}")

        self.file_path = file_path
        self.sample_rate = None
        self.audio_matrix = None

        # Load and process the audio file immediately upon initialization
        self._load_and_prepare_audio()

    def _load_and_prepare_audio(self) -> None:
        """Loads the MP3 file using pydub, ensures it is in stereo format, and

        converts the raw audio samples into a normalized NumPy matrix.
        """
        # Load MP3 file using pydub
        audio_segment = AudioSegment.from_mp3(self.file_path)
        self.sample_rate = audio_segment.frame_rate

        # Force the audio into stereo (2 channels) if it isn't already
        if audio_segment.channels != 2:
            audio_segment = audio_segment.set_channels(2)

        # Extract raw data as a NumPy array
        raw_samples = np.array(audio_segment.get_array_of_samples())

        # Pydub interleaves stereo samples (L, R, L, R...).
        # Reshape the 1D array into a 2D matrix (Frames x Channels).
        self.audio_matrix = raw_samples.reshape((-1, 2)).astype(np.float32)

        # Normalize the PCM data to a range of [-1.0, 1.0] based on bit depth
        bit_depth = audio_segment.sample_width * 8
        max_possible_value = 2 ** (bit_depth - 1)
        self.audio_matrix /= max_possible_value

    def play_with_independent_volume(
        self, left_volume: float, right_volume: float
    ) -> None:
        """Plays the audio track with individual volume multipliers for each

        channel.

        :param left_volume: Volume multiplier for the left channel (0.0 to 1.0+)
        :param right_volume: Volume multiplier for the right channel (0.0 to
            1.0+)
        """
        # Create a deep copy of the original audio data to prevent permanent modification
        playback_data = np.copy(self.audio_matrix)

        # Apply independent scaling to each channel
        # Column 0 represents the Left channel, Column 1 represents the Right channel
        playback_data[:, 0] *= left_volume
        playback_data[:, 1] *= right_volume

        # Send the modified matrix directly to the sound card
        try:
            sd.play(playback_data, self.sample_rate)
            sd.wait()  # Block execution until playback is complete
        except KeyboardInterrupt:
            sd.stop()  # Stop playback immediately if interrupted by user
            print("\nPlayback interrupted by user.")

    def play_mono_split(self, target_channel: str) -> None:
        """Plays the audio completely isolated on one chosen channel, muting the

        other entirely.

        :param target_channel: Direction to play, either 'left' or 'right'.
        """
        if target_channel.lower() == "left":
            self.play_with_independent_volume(left_volume=1.0, right_volume=0.0)
        elif target_channel.lower() == "right":
            self.play_with_independent_volume(left_volume=0.0, right_volume=1.0)
        else:
            raise ValueError("Target channel must be either 'left' or 'right'.")


# Example Usage
if __name__ == "__main__":
    # Path to your local MP3 file
    audio_file_path = "sample.mp3"

    try:
        # Initialize the controller
        print("Loading and processing audio file...")
        audio_player = StereoAudioController(audio_file_path)

        # Scenario 1: Play only on the Left channel
        print("Playing strictly on the LEFT channel...")
        audio_player.play_mono_split(target_channel="left")

        # Scenario 2: Play only on the Right channel
        print("Playing strictly on the RIGHT channel...")
        audio_player.play_mono_split(target_channel="right")

        # Scenario 3: Play both channels with asymmetric volume (Balance adjustment)
        print("Playing both channels (Left: 30% Volume, Right: 100% Volume)...")
        audio_player.play_with_independent_volume(
            left_volume=0.3, right_volume=1.0
        )

    except FileNotFoundError as e:
        print(f"Error: {e}. Please place a valid 'sample.mp3' in the directory.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")