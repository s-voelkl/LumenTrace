import os
import time
import pygame


class StereoAudioPlayer:
    """A professional audio player class for Raspberry Pi to handle stereo

    playback with independent volume control for left and right channels.
    """

    def __init__(self, frequency: int = 44100, size: int = -16, channels: int = 2):
        """Initializes the pygame mixer with standard hardware configurations.

        :param frequency: Audio playback frequency (default: 44100 Hz)
        :param size: Bit depth (default: -16 for 16-bit signed)
        :param channels: Number of audio channels (default: 2 for Stereo)
        """
        # Explicitly initialize the mixer with 2 channels for stereo support
        pygame.mixer.init(frequency=frequency, size=size, channels=channels)

    def play_stereo(
        self, file_path: str, left_vol: float, right_vol: float, loops: int = 0
    ):
        """Plays an MP3 file with individual volume control for left and right channels.

        :param file_path: Path to the target MP3 audio file
        :param left_vol: Volume level for the left channel (0.0 to 1.0)
        :param right_vol: Volume level for the right channel (0.0 to 1.0)
        :param loops: Number of loops, 0 plays once, -1 loops indefinitely
        """
        # Validate file existence before attempting to load
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"The audio file '{file_path}' was not found.")

        try:
            # Load MP3 file into a Sound object (supported natively in Pygame 2+)
            sound_effect = pygame.mixer.Sound(file_path)

            # Request an available playback channel from the mixer
            audio_channel = pygame.mixer.find_channel()

            if audio_channel is None:
                print("Error: No playback channels available.")
                return

            # Set independent volumes using a tuple: (left_channel, right_channel)
            audio_channel.set_volume(left_vol, right_vol)

            print(
                f"Starting playback: {file_path} [Left: {left_vol * 100}%, Right: {right_vol * 100}%]"
            )

            # Start playing the sound on the configured channel
            audio_channel.play(sound_effect, loops=loops)

            # Block execution gently until the audio finishes playing
            while audio_channel.get_busy():
                time.sleep(0.1)

        except pygame.error as e:
            print(f"An error occurred during Pygame playback: {e}")

    def cleanup(self):
        """Safely uninitializes the pygame mixer to release hardware resources."""
        pygame.mixer.quit()
        print("Pygame mixer uninitialized successfully.")


# ==========================================
# Execution Example
# ==========================================
if __name__ == "__main__":
    # Example file path (Replace this with your actual MP3 file path)
    AUDIO_FILE = "assets/sound/edited_car_audio.mp3"

    # Instantiate the player
    player = StereoAudioPlayer()

    try:
        # Example 1: Play sound ONLY on the Left channel
        print("\n--- Playing Left Channel Only ---")
        player.play_stereo(file_path=AUDIO_FILE, left_vol=1.0, right_vol=0.0)

        time.sleep(1)  # Short pause between tests

        # Example 2: Play sound ONLY on the Right channel
        print("\n--- Playing Right Channel Only ---")
        player.play_stereo(file_path=AUDIO_FILE, left_vol=0.0, right_vol=1.0)

        time.sleep(1)

        # Example 3: Play balanced Stereo sound
        print("\n--- Playing Full Stereo ---")
        player.play_stereo(file_path=AUDIO_FILE, left_vol=1.0, right_vol=1.0)

    except KeyboardInterrupt:
        print("\nPlayback interrupted by user.")
    except Exception as error:
        print(f"\nAn error occurred: {error}")
    finally:
        # Ensure resources are freed even if the script crashes
        player.cleanup()