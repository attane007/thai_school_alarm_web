"""
Unit Tests for Scheduler Jobs

Tests cover:
- check_schedule() function
- monitor_wifi_connection() function
- sync_schedules_to_apscheduler() function
- Idempotency checks
- State persistence
- Error handling
"""

import json
from datetime import datetime, time
from unittest.mock import patch, MagicMock, call

import pytest
from freezegun import freeze_time

from data.scheduler_jobs import (
    check_schedule,
    monitor_wifi_connection,
    sync_schedules_to_apscheduler,
    _build_sound_sequence,
    _already_executed_this_minute,
    _mark_executed,
    _get_wifi_down_count,
    _set_wifi_down_count
)
from data.models import Schedule, Utility


@pytest.mark.unit
@pytest.mark.django_db
class TestCheckSchedule:
    """Test check_schedule function."""
    
    @freeze_time('2026-01-05 08:30:00', tz_offset=7)  # Monday 8:30 Bangkok
    def test_check_schedule_finds_matching(self, test_schedule, mock_tell_time, clear_utility_state):
        """Test check_schedule finds and executes matching schedule."""
        with patch('data.scheduler_jobs.get_audio_player') as mock_get_player:
            mock_player = MagicMock()
            mock_get_player.return_value = mock_player
            
            result = check_schedule()
            
            # Should execute 1 schedule
            assert 'Executed 1 schedule' in result
            
            # Should call play_sequence
            assert mock_player.play_sequence.called
            call_args = mock_player.play_sequence.call_args
            sound_paths = call_args[0][0]
            assert len(sound_paths) > 0  # Should have sounds
    
    @freeze_time('2026-01-05 09:00:00', tz_offset=7)  # Monday 9:00 (no schedule)
    def test_check_schedule_no_matching(self, test_schedule):
        """Test check_schedule with no matching schedules."""
        result = check_schedule()
        
        assert 'No schedules at 09:00' in result
    
    @freeze_time('2026-01-06 08:30:00', tz_offset=7)  # Tuesday 8:30
    def test_check_schedule_wrong_day(self, test_schedule):
        """Test schedule not executed on wrong day of week."""
        # test_schedule is set for Monday only
        result = check_schedule()
        
        # Should find schedule but not execute (wrong day)
        assert 'Executed 0 schedule' in result
    
    @freeze_time('2026-01-05 08:30:00', tz_offset=7)
    def test_check_schedule_idempotency(self, test_schedule, mock_tell_time, clear_utility_state):
        """Test check_schedule prevents double execution."""
        with patch('data.scheduler_jobs.get_audio_player') as mock_get_player:
            mock_player = MagicMock()
            mock_get_player.return_value = mock_player
            
            # First execution
            result1 = check_schedule()
            assert 'Executed 1 schedule' in result1
            
            # Second execution (same minute)
            result2 = check_schedule()
            assert 'Already executed' in result2
            
            # Should only call play_sequence once
            assert mock_player.play_sequence.call_count == 1
    
    @freeze_time('2026-01-05 14:00:00', tz_offset=7)  # Monday 14:00
    def test_check_schedule_multiple_schedules(self, test_schedule, test_schedule_no_bell, 
                                               test_day_monday, mock_tell_time, clear_utility_state):
        """Test handling multiple schedules at same time."""
        # Create another schedule at 14:00
        from data.models import Schedule
        schedule2 = Schedule.objects.create(
            time=time(14, 0),
            tell_time=False,
            enable_bell_sound=False
        )
        schedule2.notification_days.add(test_day_monday)
        
        with patch('data.scheduler_jobs.get_audio_player') as mock_get_player:
            mock_player = MagicMock()
            mock_get_player.return_value = mock_player
            
            result = check_schedule()
            
            # Should execute both schedules
            assert 'Executed 2 schedule' in result
            assert mock_player.play_sequence.call_count == 2


@pytest.mark.unit
@pytest.mark.django_db
class TestBuildSoundSequence:
    """Test _build_sound_sequence helper function."""
    
    def test_build_sequence_with_all_options(self, test_schedule, mock_tell_time):
        """Test building sound sequence with all options enabled."""
        sound_paths = _build_sound_sequence(test_schedule, 8, 30)
        
        # Should have: bell_first + hour + minute + custom_sound + bell_last
        assert len(sound_paths) >= 3
        
        # Check tell_time was called
        mock_tell_time['tell_hour'].assert_called_once_with('08')
        mock_tell_time['tell_minute'].assert_called_once_with('30')
    
    def test_build_sequence_no_bell(self, test_schedule_no_bell):
        """Test building sound sequence without bell sounds."""
        with patch('data.scheduler_jobs.tell_hour') as mock_hour, \
             patch('data.scheduler_jobs.tell_minute') as mock_minute:
            
            mock_hour.return_value = []
            mock_minute.return_value = []
            
            sound_paths = _build_sound_sequence(test_schedule_no_bell, 14, 0)
            
            # Should only have custom sound (bell disabled, tell_time disabled)
            assert len(sound_paths) == 1
    
    def test_build_sequence_bell_only(self, test_schedule):
        """Test building sound sequence with bell and no time announcement."""
        test_schedule.tell_time = False
        test_schedule.sound = None
        test_schedule.save()
        
        sound_paths = _build_sound_sequence(test_schedule, 10, 0)
        
        # Should have bell_first + bell_last
        assert len(sound_paths) == 2


@pytest.mark.unit
@pytest.mark.django_db
class TestIdempotency:
    """Test idempotency helper functions."""
    
    def test_already_executed_false_initially(self, clear_utility_state):
        """Test _already_executed_this_minute returns False initially."""
        current_time = datetime(2026, 1, 5, 10, 30, 0)
        result = _already_executed_this_minute('test_job', current_time)
        
        assert result is False
    
    def test_mark_and_check_executed(self, clear_utility_state):
        """Test marking and checking execution."""
        current_time = datetime(2026, 1, 5, 10, 30, 0)
        
        # Mark as executed
        _mark_executed('test_job', current_time)
        
        # Check should return True
        result = _already_executed_this_minute('test_job', current_time)
        assert result is True
    
    def test_different_minute_returns_false(self, clear_utility_state):
        """Test that different minute returns False."""
        time1 = datetime(2026, 1, 5, 10, 30, 0)
        time2 = datetime(2026, 1, 5, 10, 31, 0)
        
        _mark_executed('test_job', time1)
        
        result = _already_executed_this_minute('test_job', time2)
        assert result is False


@pytest.mark.unit
@pytest.mark.django_db
@pytest.mark.wifi
class TestMonitorWiFiConnection:
    """Test monitor_wifi_connection function."""
    
    def test_wifi_monitoring_disabled(self, clear_utility_state):
        """Test that monitoring returns early when disabled."""
        Utility.objects.create(name='wifi_monitor_enabled', value='false')
        
        result = monitor_wifi_connection()
        
        assert 'disabled' in result.lower()
    
    def test_network_manager_unavailable(self, clear_utility_state):
        """Test handling when NetworkManager is not available."""
        with patch('data.scheduler_jobs.is_network_manager_available', return_value=False):
            result = monitor_wifi_connection()
            
            assert 'not available' in result.lower()
    
    def test_wifi_connection_ok(self, clear_utility_state):
        """Test normal WiFi connection monitoring."""
        with patch('data.scheduler_jobs.is_network_manager_available', return_value=True), \
             patch('data.scheduler_jobs.is_ap_mode_active', return_value=False), \
             patch('data.scheduler_jobs.check_wifi_connection', return_value=True), \
             patch('data.scheduler_jobs.check_internet_connectivity', return_value=True), \
             patch('data.scheduler_jobs.get_current_wifi', return_value={'ssid': 'TestNet'}):
            
            result = monitor_wifi_connection()
            
            assert 'OK' in result
            
            # Should save SSID
            ssid_obj = Utility.objects.filter(name='last_known_ssid').first()
            assert ssid_obj is not None
            assert ssid_obj.value == 'TestNet'
    
    def test_wifi_down_count_increments(self, clear_utility_state):
        """Test WiFi down count increments on failure."""
        with patch('data.scheduler_jobs.is_network_manager_available', return_value=True), \
             patch('data.scheduler_jobs.is_ap_mode_active', return_value=False), \
             patch('data.scheduler_jobs.check_wifi_connection', return_value=False), \
             patch('data.scheduler_jobs.check_internet_connectivity', return_value=False):
            
            # First failure
            result1 = monitor_wifi_connection()
            assert '1/3' in result1
            
            # Second failure
            result2 = monitor_wifi_connection()
            assert '2/3' in result2
            
            # Check count in database
            count = _get_wifi_down_count()
            assert count == 2
    
    def test_switch_to_ap_mode_after_3_failures(self, clear_utility_state):
        """Test switching to AP mode after 3 failures."""
        # Set initial count to 2
        _set_wifi_down_count(2)
        
        with patch('data.scheduler_jobs.is_network_manager_available', return_value=True), \
             patch('data.scheduler_jobs.is_ap_mode_active', return_value=False), \
             patch('data.scheduler_jobs.check_wifi_connection', return_value=False), \
             patch('data.scheduler_jobs.check_internet_connectivity', return_value=False), \
             patch('data.scheduler_jobs.start_ap_mode') as mock_start_ap:
            
            mock_start_ap.return_value = (True, 'Started', {'ssid': 'AP', 'password': '12345678'})
            
            result = monitor_wifi_connection()
            
            assert 'Switched to AP mode' in result
            mock_start_ap.assert_called_once()
            
            # Check fallback state saved
            fallback = Utility.objects.filter(name='in_fallback_mode').first()
            assert fallback is not None
            assert fallback.value == 'true'
    
    def test_ap_mode_wifi_recovery(self, clear_utility_state):
        """Test WiFi recovery detection when in AP mode."""
        with patch('data.scheduler_jobs.is_network_manager_available', return_value=True), \
             patch('data.scheduler_jobs.is_ap_mode_active', return_value=True), \
             patch('data.scheduler_jobs.check_wifi_connection', return_value=True), \
             patch('data.scheduler_jobs.check_internet_connectivity', return_value=True):
            
            result = monitor_wifi_connection()
            
            # Should detect WiFi back and start waiting
            assert 'WiFi back' in result or 'waiting' in result.lower()
            
            # Should save timestamp
            timestamp = Utility.objects.filter(name='wifi_back_time').first()
            assert timestamp is not None
    
    def test_ap_mode_switch_back_after_5_minutes(self, clear_utility_state):
        """Test switching back to client mode after 5 minutes."""
        # Set wifi_back_time to 6 minutes ago
        past_time = datetime.now().timestamp() - 360  # 6 minutes
        Utility.objects.create(name='wifi_back_time', value=str(past_time))
        
        with patch('data.scheduler_jobs.is_network_manager_available', return_value=True), \
             patch('data.scheduler_jobs.is_ap_mode_active', return_value=True), \
             patch('data.scheduler_jobs.check_wifi_connection', return_value=True), \
             patch('data.scheduler_jobs.check_internet_connectivity', return_value=True), \
             patch('data.scheduler_jobs.stop_ap_mode') as mock_stop_ap:
            
            mock_stop_ap.return_value = (True, 'Stopped')
            
            result = monitor_wifi_connection()
            
            assert 'client mode' in result.lower()
            mock_stop_ap.assert_called_once()
            
            # State should be cleared
            assert not Utility.objects.filter(name='in_fallback_mode').exists()
            assert not Utility.objects.filter(name='wifi_back_time').exists()


@pytest.mark.unit
@pytest.mark.django_db
class TestWiFiStateHelpers:
    """Test WiFi state helper functions."""
    
    def test_get_wifi_down_count_default(self, clear_utility_state):
        """Test getting wifi down count returns 0 by default."""
        count = _get_wifi_down_count()
        assert count == 0
    
    def test_set_and_get_wifi_down_count(self, clear_utility_state):
        """Test setting and getting wifi down count."""
        _set_wifi_down_count(5)
        
        count = _get_wifi_down_count()
        assert count == 5
        
        # Check in database
        obj = Utility.objects.get(name='wifi_down_count')
        assert obj.value == '5'


@pytest.mark.integration
@pytest.mark.django_db
class TestSyncSchedulesToAPScheduler:
    """Test sync_schedules_to_apscheduler function."""
    
    def test_sync_with_no_schedules(self, test_scheduler):
        """Test syncing when no schedules exist."""
        stats = sync_schedules_to_apscheduler(test_scheduler)
        
        assert stats['created'] == 0
        assert stats['updated'] == 0
        assert stats['removed'] == 0
    
    def test_sync_with_existing_schedules(self, test_scheduler, test_schedule, 
                                         test_schedule_no_bell):
        """Test syncing with existing schedules."""
        stats = sync_schedules_to_apscheduler(test_scheduler)
        
        # Note: Current implementation doesn't create per-schedule jobs
        # Instead, check_schedule queries database every minute
        # This is a design decision for simplicity
        
        assert stats.get('errors', 0) == 0
    
    def test_sync_error_handling(self, test_schedule):
        """Test sync handles errors gracefully."""
        # Mock scheduler that raises errors
        mock_scheduler = MagicMock()
        mock_scheduler.get_job.side_effect = Exception("Test error")
        mock_scheduler.get_jobs.return_value = []
        
        stats = sync_schedules_to_apscheduler(mock_scheduler)
        
        # Should handle errors and return stats
        assert 'errors' in stats


@pytest.mark.unit
@pytest.mark.django_db
class TestErrorHandling:
    """Test error handling in scheduler jobs."""
    
    def test_check_schedule_handles_exceptions(self, test_schedule):
        """Test check_schedule handles exceptions gracefully."""
        with patch('data.scheduler_jobs.Schedule.objects.filter') as mock_filter:
            mock_filter.side_effect = Exception("Database error")
            
            result = check_schedule()
            
            # Should return error message, not raise
            assert 'Error' in result
    
    def test_monitor_wifi_handles_exceptions(self):
        """Test monitor_wifi handles exceptions gracefully."""
        with patch('data.scheduler_jobs.is_network_manager_available') as mock_nm:
            mock_nm.side_effect = Exception("Network error")
            
            result = monitor_wifi_connection()
            
            # Should return error message, not raise
            assert 'Error' in result
