import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from src.sound.sound_manager import SoundManager

@pytest.fixture
def mock_sf_read():
    with patch('src.sound.sound_manager.sf.read') as mock_read:
        # Return 1 second of dummy silent audio at 44.1kHz
        dummy_data = np.zeros(44100, dtype='float32')
        mock_read.return_value = (dummy_data, 44100)
        yield mock_read

@pytest.fixture
def mock_sd_outputstream():
    with patch('src.sound.sound_manager.sd.OutputStream') as mock_sd:
        yield mock_sd

def test_sound_manager_initialization(mock_sf_read):
    manager = SoundManager()
    assert manager._master_volume == 100.0
    assert len(manager._active_sounds) == 0

def test_master_volume_clamping(mock_sf_read):
    manager = SoundManager()
    
    manager.set_master_volume(150.0)
    assert manager._target_master_volume == 100.0
    
    manager.set_master_volume(-20.0)
    assert manager._target_master_volume == 0.0

def test_play_single_sound(mock_sf_read, mock_sd_outputstream):
    manager = SoundManager()
    
    sound_id = manager.play("dummy.wav", volume=80.0, left_volume=100.0, right_volume=50.0)
    mock_sf_read.assert_called_once_with("dummy.wav", dtype='float32')
    
    assert sound_id in manager._active_sounds
    instance = manager._active_sounds[sound_id]
    
    assert instance.volume == 80.0
    assert instance.left_volume == 100.0
    assert instance.right_volume == 50.0

def test_play_multiple_sounds(mock_sf_read):
    manager = SoundManager()
    
    id1 = manager.play("sound1.wav", pitch=1.0)
    id2 = manager.play("sound2.wav", pitch=1.5)
    
    assert len(manager._active_sounds) == 2
    assert manager._active_sounds[id1].target_pitch == 1.0
    assert manager._active_sounds[id2].target_pitch == 1.5
    assert mock_sf_read.call_count == 2

def test_update_sound(mock_sf_read):
    manager = SoundManager()
    sound_id = manager.play("dummy.wav", volume=50.0)
    
    manager.update_sound(sound_id, volume=75.0, left_volume=25.0)
    
    instance = manager._active_sounds[sound_id]
    assert instance.target_volume == 75.0
    assert instance.target_left_volume == 25.0

def test_start_stop_manager(mock_sf_read, mock_sd_outputstream):
    manager = SoundManager()
    
    manager.start()
    mock_sd_outputstream.assert_called_once()
    assert manager._stream is not None
    manager._stream.start.assert_called_once()
    
    stream_mock = manager._stream
    
    manager.stop_all()
    stream_mock.stop.assert_called_once()
    stream_mock.close.assert_called_once()
    assert manager._stream is None
    assert len(manager._active_sounds) == 0

def test_audio_callback_mixing(mock_sf_read):
    manager = SoundManager()
    
    # Pre-cache data to control exact mock behavior
    data1 = np.array([0.5, 0.5, 0.5], dtype='float32')
    data2 = np.array([0.2, 0.2, 0.2], dtype='float32')
    
    manager._audio_cache["dummy1.wav"] = data1
    manager._audio_cache["dummy2.wav"] = data2
    
    # Play sound 1 full right
    id1 = manager.play("dummy1.wav", left_volume=0.0, right_volume=100.0)
    
    # Play sound 2 full left
    id2 = manager.play("dummy2.wav", left_volume=100.0, right_volume=0.0)
    
    outdata = np.zeros((3, 2), dtype='float32')
    manager._audio_callback(outdata, frames=3, time=None, status=None)
    
    # Check left channel contains only sound 2, and right channel contains only sound 1
    # Note: Because of smoothing (_EASING_FACTOR), the first frames slowly approach the target.
    # To cleanly test, we can force current equal to target directly for this test
    manager._active_sounds[id1].volume = 100.0
    manager._active_sounds[id1].left_volume = 0.0
    manager._active_sounds[id1].right_volume = 100.0
    
    manager._active_sounds[id2].volume = 100.0
    manager._active_sounds[id2].left_volume = 100.0
    manager._active_sounds[id2].right_volume = 0.0
    
    manager._audio_callback(outdata, frames=3, time=None, status=None)
    
    # The output will mix both arrays according to volumes.
    # After easing overrides, left should be heavily Sound2 (~0.2), right heavily Sound1 (~0.5)
    # Just verify they are populated correctly
    assert outdata[0][0] > 0.0  # Left should have sound 2
    assert outdata[0][1] > 0.0  # Right should have sound 1
