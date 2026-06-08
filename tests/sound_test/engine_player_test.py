import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from src.sound.engine_player import EngineSoundPlayer

# Provide a mock soundfile read so we don't need a real WAV file for tests
@pytest.fixture
def mock_sf_read():
    with patch('src.sound.engine_player.sf.read') as mock_read:
        # Return 1 second of dummy silent audio at 44.1kHz
        dummy_data = np.zeros(44100, dtype='float32')
        mock_read.return_value = (dummy_data, 44100)
        yield mock_read

@pytest.fixture
def mock_sd_outputstream():
    with patch('src.sound.engine_player.sd.OutputStream') as mock_sd:
        yield mock_sd

def test_engine_player_initialization(mock_sf_read):
    player = EngineSoundPlayer("dummy.wav")
    assert player.speed == 0.0
    assert player.current_pitch == player.min_pitch
    assert player.target_pitch == player.min_pitch
    
    # Assert that sf.read was actually called
    mock_sf_read.assert_called_once_with("dummy.wav", dtype='float32')

def test_engine_player_set_speed(mock_sf_read):
    player = EngineSoundPlayer("dummy.wav", min_pitch=1.0, max_pitch=3.0)
    
    # Test min bound
    player.set_speed(0.0)
    assert player.speed == 0.0
    assert player.target_pitch == 1.0
    
    # Test max bound
    player.set_speed(1.0)
    assert player.speed == 1.0
    assert player.target_pitch == 3.0
    
    # Test midpoint
    player.set_speed(0.5)
    assert player.speed == 0.5
    assert player.target_pitch == 2.0
    
    # Test clamping
    player.set_speed(1.5) # Over max
    assert player.speed == 1.0
    
    player.set_speed(-0.5) # Under min
    assert player.speed == 0.0

def test_engine_player_start_stop(mock_sf_read, mock_sd_outputstream):
    player = EngineSoundPlayer("dummy.wav")
    
    player.start()
    mock_sd_outputstream.assert_called_once()
    assert player.stream is not None
    player.stream.start.assert_called_once()
    
    # Save a reference to the stream mock, because player.stop() sets it to None
    stream_mock = player.stream
    
    player.stop()
    stream_mock.stop.assert_called_once()
    stream_mock.close.assert_called_once()
    assert player.stream is None

def test_audio_callback_logic(mock_sf_read):
    player = EngineSoundPlayer("dummy.wav")
    
    # Prepare some simulated distinct data
    simulated_data = np.array([0.1, 0.2, 0.3, 0.4, 0.5], dtype='float32')
    player.data = simulated_data
    player.current_pitch = 1.0
    player.target_pitch = 1.0
    player.current_pan = 0.0
    player.target_pan = 0.0
    player.position = 0.0
    
    # Request 3 frames (2 channels for stereo)
    outdata = np.zeros((3, 2), dtype='float32')
    player._audio_callback(outdata, 3, None, None)
    
    # With pitch=1.0 and pan=0.0, both channels get the exact value
    assert outdata[0][0] == np.float32(0.1) # Left
    assert outdata[0][1] == np.float32(0.1) # Right
    assert outdata[1][0] == np.float32(0.2)
    assert outdata[1][1] == np.float32(0.2)
    assert outdata[2][0] == np.float32(0.3)
    assert outdata[2][1] == np.float32(0.3)
    
    # Position should have advanced
    assert player.position == 3.0
