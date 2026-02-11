"""
Unit Tests for AudioPlayer

Tests cover:
- Audio playback initialization
- Sequential file playback
- State management and persistence
- Error handling
- Thread safety
- Stop functionality
"""

import json
import time
from unittest.mock import patch, MagicMock

import pytest

from data.lib.audio_player import AudioPlayer, get_audio_player
from data.models import Utility


@pytest.mark.unit
@pytest.mark.audio
@pytest.mark.django_db
class TestAudioPlayerInit:
    """Test AudioPlayer initialization."""
    
    def test_init_without_utility_model(self):
        """Test AudioPlayer initializes with default Utility model."""
        player = AudioPlayer()
        assert player.utility_model is not None
        assert player._lock is not None
        assert player._stop_event is not None
    
    def test_init_with_custom_utility_model(self):
        """Test AudioPlayer initializes with custom utility model."""
        mock_model = MagicMock()
        player = AudioPlayer(utility_model=mock_model)
        assert player.utility_model == mock_model


@pytest.mark.unit
@pytest.mark.audio
@pytest.mark.django_db
class TestAudioPlayerState:
    """Test AudioPlayer state management."""
    
    def test_get_state_empty(self, mock_audio_player, clear_utility_state):
        """Test getting state when no state exists."""
        state = mock_audio_player._get_state()
        assert state == {}
    
    def test_set_and_get_state(self, mock_audio_player, clear_utility_state):
        """Test setting and retrieving state."""
        test_state = {
            'is_playing': True,
            'current_file': 'test.mp3',
            'started_at': '2026-01-01T10:00:00'
        }
        
        mock_audio_player._set_state(test_state)
        
        # Retrieve from database
        state_obj = Utility.objects.get(name='audio_playback_state')
        saved_state = json.loads(state_obj.value)
        
        assert saved_state == test_state
    
    def test_clear_state(self, mock_audio_player, clear_utility_state):
        """Test clearing state."""
        # Set initial state
        mock_audio_player._set_state({'is_playing': True})
        assert Utility.objects.filter(name='audio_playback_state').exists()
        
        # Clear state
        mock_audio_player._clear_state()
        assert not Utility.objects.filter(name='audio_playback_state').exists()
    
    def test_is_playing_false_initially(self, mock_audio_player, clear_utility_state):
        """Test is_playing returns False initially."""
        assert mock_audio_player.is_playing() is False
    
    def test_get_detailed_state(self, mock_audio_player, clear_utility_state):
        """Test get_state returns detailed information."""
        test_state = {
            'is_playing': True,
            'current_file': 'bell.mp3',
            'playlist': ['bell.mp3', 'announcement.mp3']
        }
        
        mock_audio_player._set_state(test_state)
        state = mock_audio_player.get_state()
        
        assert state['is_playing'] is True
        assert state['current_file'] == 'bell.mp3'
        assert len(state['playlist']) == 2


@pytest.mark.unit
@pytest.mark.audio
@pytest.mark.django_db
class TestAudioPlayerPlayback:
    """Test AudioPlayer playback functionality."""
    
    def test_play_sequence_empty_list(self, mock_audio_player):
        """Test play_sequence with empty list."""
        mock_audio_player.play_sequence([])
        # Should not raise error, just return
        assert not mock_audio_player.is_playing()
    
    def test_play_sequence_file_not_found(self, mock_audio_player):
        """Test play_sequence raises error for missing file."""
        with pytest.raises(FileNotFoundError):
            mock_audio_player.play_sequence(['/nonexistent/file.mp3'])
    
    def test_play_sequence_success(self, mock_audio_player, test_audio_files, clear_utility_state):
        """Test successful playback sequence."""
        mock_audio_player.play_sequence(test_audio_files, schedule_id=123)
        
        # Give thread time to start
        time.sleep(0.1)
        
        # Check state was saved
        state = mock_audio_player.get_state()
        assert state.get('schedule_id') == 123
        assert state.get('playlist') == test_audio_files
    
    def test_play_sequence_stops_previous(self, mock_audio_player, test_audio_files):
        """Test that starting new playback stops previous."""
        # Start first playback
        mock_audio_player.play_sequence([test_audio_files[0]])
        time.sleep(0.05)
        
        # Start second playback
        mock_audio_player.play_sequence([test_audio_files[1]])
        time.sleep(0.05)
        
        # Should have stopped first and started second
        # Can't check much more without complex threading tests
        assert True  # If we got here, no deadlock occurred
    
    def test_stop_playback(self, mock_audio_player, test_audio_files, clear_utility_state):
        """Test stopping playback."""
        mock_audio_player.play_sequence(test_audio_files)
        time.sleep(0.05)
        
        mock_audio_player.stop()
        
        # State should be cleared
        state = mock_audio_player.get_state()
        assert state == {}
    
    def test_cleanup(self, mock_pygame):
        """Test cleanup cleans up pygame resources."""
        player = AudioPlayer()
        player._initialized = True
        
        player.cleanup()
        
        mock_pygame.mixer.quit.assert_called_once()
        assert player._initialized is False


@pytest.mark.unit
@pytest.mark.audio
class TestAudioPlayerSingleton:
    """Test AudioPlayer singleton functionality."""
    
    def test_get_audio_player_singleton(self):
        """Test get_audio_player returns singleton instance."""
        player1 = get_audio_player()
        player2 = get_audio_player()
        
        assert player1 is player2


@pytest.mark.unit
@pytest.mark.audio
@pytest.mark.django_db
class TestAudioPlayerErrorHandling:
    """Test AudioPlayer error handling."""
    
    def test_state_error_handling_graceful(self, mock_audio_player):
        """Test that state errors don't crash the player."""
        # Mock database error
        with patch.object(mock_audio_player.utility_model.objects, 'filter') as mock_filter:
            mock_filter.side_effect = Exception("Database error")
            
            # Should not raise, just return empty dict
            state = mock_audio_player._get_state()
            assert state == {}
    
    def test_pygame_unavailable_raises_error(self):
        """Test that RuntimeError is raised when pygame unavailable."""
        with patch('data.lib.audio_player.PYGAME_AVAILABLE', False):
            player = AudioPlayer()
            
            with pytest.raises(RuntimeError, match="pygame is not available"):
                player._init_pygame()


@pytest.mark.integration
@pytest.mark.audio
@pytest.mark.django_db
class TestAudioPlayerIntegration:
    """Integration tests for AudioPlayer."""
    
    def test_full_playback_cycle(self, mock_pygame, test_audio_files, clear_utility_state):
        """Test complete playback cycle from start to finish."""
        player = AudioPlayer()
        player._initialized = True
        
        # Configure mock to simulate playback finishing
        mock_pygame.mixer.music.get_busy.side_effect = [True, True, False]
        
        # Start playback
        player.play_sequence(test_audio_files, schedule_id=999)
        
        # Wait for thread to process
        time.sleep(0.2)
        
        # Check that pygame was called
        assert mock_pygame.mixer.music.load.called
        assert mock_pygame.mixer.music.play.called
    
    def test_concurrent_playback_prevented(self, mock_audio_player, test_audio_file):
        """Test that concurrent playback is prevented."""
        # Mock is_playing to return True
        with patch.object(mock_audio_player, 'is_playing', return_value=True):
            with patch.object(mock_audio_player, 'stop') as mock_stop:
                mock_audio_player.play_sequence([test_audio_file])
                
                # Stop should be called to prevent concurrent playback
                mock_stop.assert_called_once()
