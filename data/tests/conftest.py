"""
Pytest fixtures and test configuration for Thai School Alarm Web

This module provides reusable test fixtures for:
- Django models (Schedule, Audio, Bell, Day, Utility)
- Mock audio player
- Mock WiFi/network components
- APScheduler instances for testing
- Time manipulation utilities
"""

import os
import json
from datetime import datetime, time
from unittest.mock import Mock, MagicMock, patch

import pytest
from django.utils import timezone
from freezegun import freeze_time

# Import Django models
from data.models import Schedule, Audio, Bell, Day, Utility


@pytest.fixture
def test_audio_file(tmp_path):
    """
    Create a temporary test audio file.
    
    Returns:
        Path to temporary MP3 file
    """
    audio_file = tmp_path / "test_sound.mp3"
    audio_file.write_bytes(b"fake mp3 content")
    return str(audio_file)


@pytest.fixture
def test_audio_files(tmp_path):
    """
    Create multiple temporary test audio files.
    
    Returns:
        List of paths to temporary audio files
    """
    files = []
    for i in range(3):
        audio_file = tmp_path / f"test_sound_{i}.mp3"
        audio_file.write_bytes(b"fake mp3 content")
        files.append(str(audio_file))
    return files


@pytest.fixture
@pytest.mark.django_db
def test_day_monday():
    """Create Monday Day object."""
    day, created = Day.objects.get_or_create(
        name='จันทร์',
        defaults={'name_eng': 'Monday'}
    )
    return day


@pytest.fixture
@pytest.mark.django_db
def test_day_tuesday():
    """Create Tuesday Day object."""
    day, created = Day.objects.get_or_create(
        name='อังคาร',
        defaults={'name_eng': 'Tuesday'}
    )
    return day


@pytest.fixture
@pytest.mark.django_db
def test_audio(test_audio_file):
    """
    Create test Audio object.
    
    Args:
        test_audio_file: Path to temporary audio file
        
    Returns:
        Audio model instance
    """
    audio = Audio.objects.create(
        name='Test Sound',
        path=test_audio_file
    )
    return audio


@pytest.fixture
@pytest.mark.django_db
def test_bell(test_audio_files):
    """
    Create test Bell object.
    
    Args:
        test_audio_files: List of temporary audio file paths
        
    Returns:
        Bell model instance
    """
    bell = Bell.objects.create(
        name='Test Bell',
        first=test_audio_files[0],
        last=test_audio_files[1],
        status=True
    )
    return bell


@pytest.fixture
@pytest.mark.django_db
def test_schedule(test_day_monday, test_audio, test_bell):
    """
    Create test Schedule object.
    
    Returns:
        Schedule model instance with Monday notification day
    """
    schedule = Schedule.objects.create(
        time=time(8, 30),  # 08:30
        sound=test_audio,
        bell_sound=test_bell,
        tell_time=True,
        enable_bell_sound=True
    )
    schedule.notification_days.add(test_day_monday)
    return schedule


@pytest.fixture
@pytest.mark.django_db
def test_schedule_no_bell(test_day_monday, test_audio):
    """
    Create test Schedule object without bell sounds.
    
    Returns:
        Schedule model instance
    """
    schedule = Schedule.objects.create(
        time=time(14, 0),  # 14:00
        sound=test_audio,
        bell_sound=None,
        tell_time=False,
        enable_bell_sound=False
    )
    schedule.notification_days.add(test_day_monday)
    return schedule


@pytest.fixture
def mock_pygame():
    """
    Mock pygame module for testing without audio output.
    
    Returns:
        Mock pygame instance
    """
    with patch('data.lib.audio_player.pygame') as mock_pg:
        mock_pg.mixer = MagicMock()
        mock_pg.mixer.init = MagicMock()
        mock_pg.mixer.quit = MagicMock()
        mock_pg.mixer.music = MagicMock()
        mock_pg.mixer.music.load = MagicMock()
        mock_pg.mixer.music.play = MagicMock()
        mock_pg.mixer.music.stop = MagicMock()
        mock_pg.mixer.music.get_busy = MagicMock(return_value=False)
        mock_pg.time = MagicMock()
        mock_pg.time.Clock = MagicMock()
        
        # Make pygame available
        with patch('data.lib.audio_player.PYGAME_AVAILABLE', True):
            yield mock_pg


@pytest.fixture
def mock_audio_player(mock_pygame):
    """
    Create mock AudioPlayer instance.
    
    Returns:
        Mock AudioPlayer
    """
    from data.lib.audio_player import AudioPlayer
    
    player = AudioPlayer()
    # Mock the _init_pygame to avoid actual initialization
    player._initialized = True
    
    return player


@pytest.fixture
def mock_wifi_manager():
    """
    Mock WiFi manager functions.
    
    Returns:
        Dict of mocked functions
    """
    with patch('data.scheduler_jobs.check_wifi_connection') as check_wifi, \
         patch('data.scheduler_jobs.check_internet_connectivity') as check_internet, \
         patch('data.scheduler_jobs.get_current_wifi') as get_wifi, \
         patch('data.scheduler_jobs.is_network_manager_available') as is_nm_available:
        
        # Default behavior - everything works
        check_wifi.return_value = True
        check_internet.return_value = True
        get_wifi.return_value = {'ssid': 'TestWiFi', 'signal': 80}
        is_nm_available.return_value = True
        
        yield {
            'check_wifi': check_wifi,
            'check_internet': check_internet,
            'get_wifi': get_wifi,
            'is_nm_available': is_nm_available
        }


@pytest.fixture
def mock_ap_manager():
    """
    Mock AP manager functions.
    
    Returns:
        Dict of mocked functions
    """
    with patch('data.scheduler_jobs.start_ap_mode') as start_ap, \
         patch('data.scheduler_jobs.stop_ap_mode') as stop_ap, \
         patch('data.scheduler_jobs.is_ap_mode_active') as is_ap_active:
        
        # Default behavior
        start_ap.return_value = (True, 'AP mode started', {'ssid': 'SchoolAP', 'password': 'test1234'})
        stop_ap.return_value = (True, 'AP mode stopped')
        is_ap_active.return_value = False
        
        yield {
            'start_ap': start_ap,
            'stop_ap': stop_ap,
            'is_ap_active': is_ap_active
        }


@pytest.fixture
def test_scheduler():
    """
    Create test APScheduler instance.
    
    Returns:
        BackgroundScheduler configured for testing
    """
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.jobstores.memory import MemoryJobStore
    
    scheduler = BackgroundScheduler(
        timezone='Asia/Bangkok',
        job_defaults={
            'coalesce': True,
            'max_instances': 1,
            'misfire_grace_time': 60
        }
    )
    
    # Use in-memory job store for testing
    scheduler.add_jobstore(MemoryJobStore(), 'default')
    
    yield scheduler
    
    # Cleanup
    if scheduler.running:
        scheduler.shutdown(wait=False)


@pytest.fixture
def frozen_time_monday_8_30():
    """
    Freeze time to Monday 8:30 AM Bangkok time.
    
    Yields:
        freezegun frozen_time context
    """
    # Monday, January 5, 2026, 08:30:00 Bangkok time
    frozen_time = freeze_time('2026-01-05 08:30:00', tz_offset=7)
    frozen_time.start()
    yield frozen_time
    frozen_time.stop()


@pytest.fixture
def frozen_time_tuesday_14_00():
    """
    Freeze time to Tuesday 14:00 Bangkok time.
    
    Yields:
        freezegun frozen_time context
    """
    # Tuesday, January 6, 2026, 14:00:00 Bangkok time
    frozen_time = freeze_time('2026-01-06 14:00:00', tz_offset=7)
    frozen_time.start()
    yield frozen_time
    frozen_time.stop()


@pytest.fixture
@pytest.mark.django_db
def clear_utility_state():
    """
    Clear all Utility model state before and after test.
    
    Useful for ensuring clean state between tests.
    """
    # Clear before test
    Utility.objects.all().delete()
    
    yield
    
    # Clear after test
    Utility.objects.all().delete()


@pytest.fixture
def mock_tell_time():
    """
    Mock time announcement functions.
    
    Returns:
        Dict of mocked functions
    """
    with patch('data.scheduler_jobs.tell_hour') as mock_hour, \
         patch('data.scheduler_jobs.tell_minute') as mock_minute:
        
        # Return fake audio paths
        mock_hour.return_value = ['audio/thai/เวลา/08.mp3']
        mock_minute.return_value = ['audio/thai/เวลา/30.mp3']
        
        yield {
            'tell_hour': mock_hour,
            'tell_minute': mock_minute
        }


# Auto-use fixture to ensure Django setup
@pytest.fixture(scope='session')
def django_db_setup():
    """Ensure Django is properly configured for tests."""
    import django
    from django.conf import settings
    
    if not settings.configured:
        django.setup()
