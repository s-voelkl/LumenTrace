import os
import numpy as np
import scipy.io.wavfile as wavfile

def generate_engine_sound(filename="assets/sound/base_engine.wav", duration=2.0, sample_rate=44100):
    """
    Generates a synthetic, loopable motor engine sound and saves it as a WAV file.
    Creates a basic low-frequency rumble using sine/sawtooth approximations and noise.
    """
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    # Time array
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    
    # Base frequency for idle engine (Hz)
    freq = 60.0
    
    # Mix of low-frequency waves (approximation of cylinder firing)
    # Using np.sign(np.sin(...)) for a rough square/pulse wave sound
    pulse = 0.5 * np.sign(np.sin(2 * np.pi * freq * t))
    sine = 0.3 * np.sin(2 * np.pi * freq * 2 * t)
    
    # Motor usually has some mechanical noise
    noise = 0.15 * np.random.normal(size=t.shape)
    
    # Combine signals
    wave = pulse + sine + noise
    
    # Soft clipping to make it sound more distorted/mechanical
    wave = np.tanh(wave * 2.0)
    
    # Normalize to 16-bit PCM range
    wave_normalized = np.int16(wave / np.max(np.abs(wave)) * 32767)
    
    # Save to disk
    wavfile.write(filename, sample_rate, wave_normalized)
    print(f"Syntethic engine sound generated and saved to: {filename}")

if __name__ == "__main__":
    generate_engine_sound()
