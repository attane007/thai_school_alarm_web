"""
Task functions for Thai School Alarm Web

This module provides helper functions for audio playback and scheduling.
Uses APScheduler for scheduling instead of Celery.
"""

import os
import logging
import subprocess
import signal
import threading

from data.lib.audio_player import get_audio_player

logger = logging.getLogger(__name__)

# Global state for audio playback
current_process = None
play_thread = None
stop_event = threading.Event()


def play_sound(sound_paths=None):
    """
    Play a sequence of audio files.
    
    Args:
        sound_paths: List of file paths to play in sequence
        
    Uses pygame mixer for cross-platform audio playback.
    Falls back to ffplay if available.
    """
    global current_process, play_thread, stop_event
    
    if sound_paths is None:
        sound_paths = []
    
    # If only 1 song, wrap it with bell sounds
    if not sound_paths:
        sound_paths = ['audio/bell/sound1/First.wav', 'audio/bell/sound2/First.wav', 'audio/bell/sound3/First.wav']
    elif len(sound_paths) == 1:
        sound_paths = ['audio/bell/sound1/First.wav', sound_paths[0], 'audio/bell/sound1/First.wav']
    
    def play_sequence():
        """Play audio files in sequence using pygame or ffplay"""
        global current_process, stop_event
        
        # Try using AudioPlayer first (pygame-based, platform-independent)
        try:
            player = get_audio_player()
            for path in sound_paths:
                if stop_event.is_set():
                    break
                    
                if os.path.exists(path):
                    logger.info(f"Playing: {path}")
                    player.play([path])
                    player.wait()
                else:
                    logger.warning(f"Audio file not found: {path}")
        except Exception as e:
            logger.error(f"Error with AudioPlayer: {e}")
            
            # Fallback to ffplay if available
            try:
                for path in sound_paths:
                    if stop_event.is_set():
                        break
                    
                    if not os.path.exists(path):
                        logger.warning(f"Audio file not found: {path}")
                        continue
                    
                    logger.info(f"Playing via ffplay: {path}")
                    command = ['ffplay', '-nodisp', '-autoexit', path]
                    
                    current_process = subprocess.Popen(
                        command,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
                    )
                    
                    current_process.wait()
            except FileNotFoundError:
                logger.error("ffplay not found and AudioPlayer unavailable")
            except Exception as e:
                logger.error(f"Error in fallback playback: {e}")
            finally:
                current_process = None
        
        stop_event.clear()
        logger.info("Finished playing all sounds")
    
    # Stop any existing playback
    stop_sound()
    stop_event.clear()
    
    # Start playback in background thread
    play_thread = threading.Thread(target=play_sequence, daemon=True)
    play_thread.start()
    logger.info("Started audio playback thread")


def stop_sound():
    """
    Stop any currently playing audio.
    
    Gracefully terminates the audio playback process.
    """
    global current_process, stop_event
    
    stop_event.set()
    
    if current_process and current_process.poll() is None:
        try:
            if os.name == 'nt':
                # Windows: use CTRL_BREAK_EVENT
                current_process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                # Unix: use SIGTERM
                current_process.terminate()
        except Exception:
            # Force kill if graceful termination fails
            try:
                current_process.kill()
            except Exception:
                pass
    
    current_process = None
    logger.info("Stopped audio playback")


# Import scheduler jobs for compatibility
from data.scheduler_jobs import (
    check_schedule,
    monitor_wifi_connection,
    sync_schedules_to_apscheduler
)

__all__ = [
    'play_sound',
    'stop_sound',
    'check_schedule',
    'monitor_wifi_connection',
    'sync_schedules_to_apscheduler'
]
