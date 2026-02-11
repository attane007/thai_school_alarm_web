"""
Integration and Management Command Tests

Tests cover:
- End-to-end schedule execution flow
- Management command behavior
- Scheduler lifecycle
- Job execution tracking
"""

import time
from datetime import time as dt_time
from unittest.mock import patch, MagicMock
from io import StringIO

import pytest
from django.core.management import call_command
from freezegun import freeze_time

from data.management.commands.run_scheduler import Command
from data.models import Schedule, Utility
from data.scheduler_jobs import check_schedule


@pytest.mark.integration
@pytest.mark.django_db
class TestSchedulerIntegration:
    """Integration tests for scheduler functionality."""
    
    @freeze_time('2026-01-05 08:30:00', tz_offset=7)  # Monday 8:30
    def test_end_to_end_schedule_execution(self, test_schedule, test_audio_files, 
                                           mock_tell_time, clear_utility_state):
        """Test complete flow from schedule to audio playback."""
        with patch('data.scheduler_jobs.get_audio_player') as mock_get_player:
            mock_player = MagicMock()
            mock_get_player.return_value = mock_player
            
            # Execute check_schedule
            result = check_schedule()
            
            # Verify execution
            assert 'Executed 1 schedule' in result
            
            # Verify audio player was called with correct schedule
            mock_player.play_sequence.assert_called_once()
            call_args = mock_player.play_sequence.call_args
            schedule_id = call_args[1]['schedule_id']
            assert schedule_id == test_schedule.id
    
    @freeze_time('2026-01-05 08:30:00', tz_offset=7)
    def test_scheduler_restart_idempotency(self, test_schedule, mock_tell_time, 
                                          clear_utility_state):
        """Test that restarting scheduler near schedule time doesn't duplicate."""
        with patch('data.scheduler_jobs.get_audio_player') as mock_get_player:
            mock_player = MagicMock()
            mock_get_player.return_value = mock_player
            
            # First run (simulating initial scheduler)
            result1 = check_schedule()
            assert 'Executed 1 schedule' in result1
            
            # Second run (simulating restart in same minute)
            result2 = check_schedule()
            assert 'Already executed' in result2
            
            # Only one playback should happen
            assert mock_player.play_sequence.call_count == 1
    
    def test_multiple_schedules_same_time(self, test_day_monday, test_audio, 
                                         mock_tell_time, clear_utility_state):
        """Test handling multiple schedules at same time."""
        # Create 3 schedules at 10:00
        schedules = []
        for i in range(3):
            schedule = Schedule.objects.create(
                time=dt_time(10, 0),
                sound=test_audio,
                tell_time=False,
                enable_bell_sound=False
            )
            schedule.notification_days.add(test_day_monday)
            schedules.append(schedule)
        
        with freeze_time('2026-01-05 10:00:00', tz_offset=7):  # Monday 10:00
            with patch('data.scheduler_jobs.get_audio_player') as mock_get_player:
                mock_player = MagicMock()
                mock_get_player.return_value = mock_player
                
                result = check_schedule()
                
                # Should execute all 3 schedules
                assert 'Executed 3 schedule' in result
                assert mock_player.play_sequence.call_count == 3


@pytest.mark.integration
@pytest.mark.slow
class TestManagementCommand:
    """Test run_scheduler management command."""
    
    def test_command_initialization(self):
        """Test command initializes correctly."""
        cmd = Command()
        
        assert cmd.scheduler is None
        assert cmd.shutting_down is False
    
    def test_command_help_text(self):
        """Test command has proper help text."""
        cmd = Command()
        assert 'APScheduler' in cmd.help
    
    @patch('data.management.commands.run_scheduler.BackgroundScheduler')
    @patch('data.management.commands.run_scheduler.time.sleep')
    def test_command_starts_scheduler(self, mock_sleep, mock_scheduler_class):
        """Test command starts scheduler successfully."""
        # Mock scheduler
        mock_scheduler = MagicMock()
        mock_scheduler.running = True
        mock_scheduler_class.return_value = mock_scheduler
        
        # Mock sleep to exit immediately
        mock_sleep.side_effect = KeyboardInterrupt()
        
        cmd = Command()
        
        # Capture output
        out = StringIO()
        
        try:
            with patch('sys.stdout', out):
                cmd.handle(no_wifi_monitor=True)
        except (KeyboardInterrupt, SystemExit):
            pass
        
        # Verify scheduler was started
        mock_scheduler.start.assert_called_once()
        mock_scheduler.shutdown.assert_called_once()
    
    def test_command_no_wifi_monitor_option(self):
        """Test --no-wifi-monitor option is respected."""
        cmd = Command()
        
        # Create parser and add arguments
        parser = MagicMock()
        cmd.add_arguments(parser)
        
        # Verify argument was added
        parser.add_argument.assert_called_once()
        call_args = parser.add_argument.call_args
        assert '--no-wifi-monitor' in call_args[0]
    
    @patch('data.management.commands.run_scheduler.BackgroundScheduler')
    def test_command_adds_jobs(self, mock_scheduler_class):
        """Test command adds scheduled jobs."""
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler
        
        cmd = Command()
        cmd.scheduler = mock_scheduler
        
        # Add jobs (without WiFi monitoring)
        cmd._add_jobs(no_wifi_monitor=True)
        
        # Should add 2 jobs (check_schedule + sync_schedules)
        # WiFi monitoring disabled
        assert mock_scheduler.add_job.call_count == 2
    
    @patch('data.management.commands.run_scheduler.BackgroundScheduler')
    def test_command_adds_wifi_monitor_by_default(self, mock_scheduler_class):
        """Test command adds WiFi monitoring job by default."""
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler
        
        cmd = Command()
        cmd.scheduler = mock_scheduler
        
        # Add jobs (with WiFi monitoring)
        cmd._add_jobs(no_wifi_monitor=False)
        
        # Should add 3 jobs (check_schedule + monitor_wifi + sync_schedules)
        assert mock_scheduler.add_job.call_count == 3
    
    @patch('data.management.commands.run_scheduler.get_audio_player')
    @patch('data.management.commands.run_scheduler.BackgroundScheduler')
    def test_command_graceful_shutdown(self, mock_scheduler_class, mock_get_player):
        """Test command performs graceful shutdown."""
        mock_scheduler = MagicMock()
        mock_scheduler.running = True
        mock_scheduler_class.return_value = mock_scheduler
        
        mock_player = MagicMock()
        mock_get_player.return_value = mock_player
        
        cmd = Command()
        cmd.scheduler = mock_scheduler
        
        # Call shutdown
        cmd._shutdown()
        
        # Verify cleanup
        mock_player.stop.assert_called_once()
        mock_player.cleanup.assert_called_once()
        mock_scheduler.shutdown.assert_called_once_with(wait=True)
    
    def test_command_signal_handler(self):
        """Test signal handler sets shutting_down flag."""
        cmd = Command()
        assert cmd.shutting_down is False
        
        # Simulate signal
        cmd._signal_handler(2, None)  # SIGINT
        
        assert cmd.shutting_down is True


@pytest.mark.integration
@pytest.mark.django_db
class TestSchedulerLifecycle:
    """Test scheduler lifecycle operations."""
    
    @patch('data.management.commands.run_scheduler.BackgroundScheduler')
    def test_scheduler_creates_job_store(self, mock_scheduler_class):
        """Test scheduler configures Django job store."""
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler
        
        cmd = Command()
        scheduler = cmd._create_scheduler()
        
        # Verify job store was added
        mock_scheduler.add_jobstore.assert_called_once()
    
    @patch('data.management.commands.run_scheduler.BackgroundScheduler')
    def test_scheduler_registers_event_listeners(self, mock_scheduler_class):
        """Test scheduler registers event listeners."""
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler
        
        cmd = Command()
        scheduler = cmd._create_scheduler()
        
        # Verify event listeners were added (3 total)
        assert mock_scheduler.add_listener.call_count == 3
    
    def test_scheduler_timezone_configuration(self):
        """Test scheduler uses correct timezone."""
        cmd = Command()
        scheduler = cmd._create_scheduler()
        
        # Verify timezone
        assert str(scheduler.timezone) == 'Asia/Bangkok'


@pytest.mark.integration
@pytest.mark.django_db
class TestJobExecution:
    """Test job execution behavior."""
    
    @freeze_time('2026-01-05 08:30:00', tz_offset=7)
    def test_job_execution_logging(self, test_schedule, mock_tell_time, 
                                   clear_utility_state, caplog):
        """Test that job execution is properly logged."""
        import logging
        
        with caplog.at_level(logging.INFO):
            with patch('data.scheduler_jobs.get_audio_player') as mock_get_player:
                mock_player = MagicMock()
                mock_get_player.return_value = mock_player
                
                check_schedule()
        
        # Check logs contain execution info
        assert any('Checking schedules' in record.message for record in caplog.records)
        assert any('Played sound' in record.message for record in caplog.records)
    
    @freeze_time('2026-01-05 08:30:00', tz_offset=7)
    def test_job_execution_state_tracking(self, test_schedule, mock_tell_time, 
                                         clear_utility_state):
        """Test that job execution state is tracked."""
        with patch('data.scheduler_jobs.get_audio_player') as mock_get_player:
            mock_player = MagicMock()
            mock_get_player.return_value = mock_player
            
            # Execute
            check_schedule()
            
            # Check execution was recorded
            exec_record = Utility.objects.filter(name='last_execution_check_schedule').first()
            assert exec_record is not None
            
            # Verify timestamp is correct
            import json
            data = json.loads(exec_record.value)
            assert data['hour'] == 8
            assert data['minute'] == 30


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.slow
class TestSchedulerRecovery:
    """Test scheduler recovery scenarios."""
    
    @freeze_time('2026-01-05 08:30:00', tz_offset=7)
    def test_scheduler_restart_preserves_state(self, test_schedule, clear_utility_state):
        """Test that scheduler restart doesn't lose execution state."""
        with patch('data.scheduler_jobs.get_audio_player') as mock_get_player:
            mock_player = MagicMock()
            mock_get_player.return_value = mock_player
            
            # First scheduler instance executes
            check_schedule()
            first_call_count = mock_player.play_sequence.call_count
            
            # Simulate scheduler restart (but still in same minute)
            # Second instance should see execution already happened
            check_schedule()
            
            # Should not execute again
            assert mock_player.play_sequence.call_count == first_call_count
    
    @freeze_time('2026-01-05 08:30:00', tz_offset=7)
    def test_database_state_survives_restart(self, test_schedule, clear_utility_state):
        """Test that scheduler state in database survives process restart."""
        with patch('data.scheduler_jobs.get_audio_player') as mock_get_player:
            mock_player = MagicMock()
            mock_get_player.return_value = mock_player
            
            # Execute and mark
            check_schedule()
            
            # Simulate process restart - clear Python state but DB persists
            # Re-check execution record from database
            from data.scheduler_jobs import _already_executed_this_minute
            from datetime import datetime
            
            is_executed = _already_executed_this_minute(
                'check_schedule',
                datetime(2026, 1, 5, 8, 30, 0)
            )
            
            assert is_executed is True


@pytest.mark.integration
@pytest.mark.django_db
class TestErrorRecovery:
    """Test error recovery in scheduler."""
    
    def test_scheduler_continues_after_job_error(self, test_schedule):
        """Test that scheduler continues running after job error."""
        with patch('data.scheduler_jobs.Schedule.objects.filter') as mock_filter:
            # First call fails
            mock_filter.side_effect = [
                Exception("Database error"),
                Schedule.objects.none()  # Second call succeeds
            ]
            
            # First execution - error
            result1 = check_schedule()
            assert 'Error' in result1
            
            # Second execution - should still work
            result2 = check_schedule()
            # Should execute without crashing
            assert result2 is not None
