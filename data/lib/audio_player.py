"""
Audio Player Module - Cross-platform audio playback with state management

This module provides a cross-platform audio player using pygame.
Playback state is persisted in the database via Utility model.
Designed to be thread-safe and testable.
"""

import os
import logging
import json
import threading
from typing import List, Optional, Dict, Any
from datetime import datetime

# Lazy import pygame to allow mocking in tests
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    logging.warning("pygame not available - audio playback disabled")

logger = logging.getLogger(__name__)


class AudioPlayer:
    """
    Cross-platform audio player with state management.
    
    Features:
    - Sequential audio file playback
    - Thread-safe operations
    - State persistence in database
    - Graceful error handling
    - Prevents concurrent playback
    """
    
    STATE_KEY = 'audio_playback_state'
    
    def __init__(self, utility_model=None):
        """
        Initialize audio player.
        
        Args:
            utility_model: Django Utility model class for state persistence
                          If None, will import from data.models
        """
        if utility_model is None:
            from data.models import Utility
            self.utility_model = Utility
        else:
            self.utility_model = utility_model
            
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._play_thread: Optional[threading.Thread] = None
        self._initialized = False
        
    def _init_pygame(self):
        """Initialize pygame mixer if not already initialized."""
        if not PYGAME_AVAILABLE:
            raise RuntimeError("pygame is not available")
            
        if not self._initialized:
            try:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
                self._initialized = True
                logger.info("pygame mixer initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize pygame mixer: {e}")
                raise
    
    def _get_state(self) -> Dict[str, Any]:
        """
        Get current playback state from database.
        
        Returns:
            Dict with state info (is_playing, current_file, started_at, etc.)
        """
        try:
            state_obj = self.utility_model.objects.filter(name=self.STATE_KEY).first()
            if state_obj:
                return json.loads(state_obj.value)
            return {}
        except Exception as e:
            logger.error(f"Error reading playback state: {e}")
            return {}
    
    def _set_state(self, state: Dict[str, Any]):
        """
        Save playback state to database.
        
        Args:
            state: Dictionary with state information
        """
        try:
            self.utility_model.objects.update_or_create(
                name=self.STATE_KEY,
                defaults={'value': json.dumps(state)}
            )
        except Exception as e:
            logger.error(f"Error saving playback state: {e}")
    
    def _clear_state(self):
        """Clear playback state from database."""
        try:
            self.utility_model.objects.filter(name=self.STATE_KEY).delete()
        except Exception as e:
            logger.error(f"Error clearing playback state: {e}")
    
    def is_playing(self) -> bool:
        """
        Check if audio is currently playing.
        
        Returns:
            True if audio is playing, False otherwise
        """
        with self._lock:
            # Check if thread is alive
            if self._play_thread and self._play_thread.is_alive():
                return True
            
            # Check database state as fallback
            state = self._get_state()
            return state.get('is_playing', False)
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get detailed playback state.
        
        Returns:
            Dictionary with: is_playing, current_file, started_at, playlist
        """
        return self._get_state()
    
    def play_sequence(self, sound_paths: List[str], schedule_id: Optional[int] = None):
        """
        Play a sequence of audio files.
        
        Args:
            sound_paths: List of audio file paths to play sequentially
            schedule_id: Optional schedule ID for tracking
            
        Raises:
            RuntimeError: If already playing or pygame unavailable
            FileNotFoundError: If any audio file doesn't exist
        """
        if not sound_paths:
            logger.warning("play_sequence called with empty sound_paths")
            return
        
        # Validate all files exist
        for path in sound_paths:
            if not os.path.exists(path):
                logger.error(f"Audio file not found: {path}")
                raise FileNotFoundError(f"Audio file not found: {path}")
        
        # Check if already playing
        if self.is_playing():
            logger.warning("Audio is already playing - stopping current playback")
            self.stop()
        
        # Start playback in background thread
        self._stop_event.clear()
        self._play_thread = threading.Thread(
            target=self._play_worker,
            args=(sound_paths, schedule_id),
            daemon=True,
            name="AudioPlayerThread"
        )
        self._play_thread.start()
        logger.info(f"Started audio playback thread for {len(sound_paths)} files")
    
    def _play_worker(self, sound_paths: List[str], schedule_id: Optional[int]):
        """
        Worker thread for playing audio sequence.
        
        Args:
            sound_paths: List of audio files to play
            schedule_id: Optional schedule ID
        """
        try:
            self._init_pygame()
            
            # Save initial state
            state = {
                'is_playing': True,
                'started_at': datetime.now().isoformat(),
                'schedule_id': schedule_id,
                'playlist': sound_paths,
                'current_index': 0
            }
            self._set_state(state)
            
            # Play each file sequentially
            for idx, path in enumerate(sound_paths):
                if self._stop_event.is_set():
                    logger.info("Playback stopped by user")
                    break
                
                # Update current file in state
                state['current_index'] = idx
                state['current_file'] = path
                self._set_state(state)
                
                try:
                    logger.info(f"Playing audio file [{idx+1}/{len(sound_paths)}]: {path}")
                    pygame.mixer.music.load(path)
                    pygame.mixer.music.play()
                    
                    # Wait for playback to finish
                    while pygame.mixer.music.get_busy():
                        if self._stop_event.is_set():
                            pygame.mixer.music.stop()
                            break
                        pygame.time.Clock().tick(10)  # Check 10 times per second
                    
                except Exception as e:
                    logger.error(f"Error playing file {path}: {e}")
                    # Continue to next file
            
            logger.info("Finished playing audio sequence")
            
        except Exception as e:
            logger.error(f"Error in audio playback worker: {e}")
        finally:
            # Clear state
            self._clear_state()
            self._stop_event.clear()
    
    def stop(self):
        """
        Stop current audio playback.
        
        This will gracefully stop the current playback and clean up resources.
        """
        with self._lock:
            logger.info("Stopping audio playback")
            self._stop_event.set()
            
            # Stop pygame mixer if playing
            if PYGAME_AVAILABLE and self._initialized:
                try:
                    pygame.mixer.music.stop()
                except Exception as e:
                    logger.error(f"Error stopping pygame mixer: {e}")
            
            # Wait for thread to finish (with timeout)
            if self._play_thread and self._play_thread.is_alive():
                self._play_thread.join(timeout=2.0)
                if self._play_thread.is_alive():
                    logger.warning("Audio thread did not stop within timeout")
            
            # Clear state
            self._clear_state()
            self._play_thread = None
    
    def cleanup(self):
        """
        Cleanup pygame resources.
        
        Call this when shutting down the application.
        """
        self.stop()
        if PYGAME_AVAILABLE and self._initialized:
            try:
                pygame.mixer.quit()
                self._initialized = False
                logger.info("pygame mixer cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up pygame mixer: {e}")


# Global singleton instance (optional - for convenience)
_player_instance: Optional[AudioPlayer] = None


def get_audio_player() -> AudioPlayer:
    """
    Get singleton audio player instance.
    
    Returns:
        AudioPlayer instance
    """
    global _player_instance
    if _player_instance is None:
        _player_instance = AudioPlayer()
    return _player_instance
