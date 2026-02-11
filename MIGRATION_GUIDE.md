# Migration from Celery to APScheduler - Complete Guide

## Overview

Thai School Alarm Web has been successfully migrated from **Celery + RabbitMQ** to **APScheduler**. This eliminates the need for external message brokers and simplifies deployment significantly.

---

## What Changed?

### ✅ Removed
- ❌ Celery (task queue framework)
- ❌ RabbitMQ (message broker)
- ❌ Celery Beat (periodic task scheduler)
- ❌ `celery` Python package dependencies
- ❌ Celery worker and beat systemd services

### ✅ Added
- ✅ APScheduler (Python scheduling library)
- ✅ django-apscheduler (Django integration)
- ✅ pygame (cross-platform audio playback)
- ✅ New `AudioPlayer` class (`data/lib/audio_player.py`)
- ✅ New `scheduler_jobs.py` module with plain functions
- ✅ Management command: `python manage.py run_scheduler`
- ✅ Single scheduler systemd service
- ✅ Comprehensive test suite (pytest)

---

## Installation & Setup

### 1. Install Dependencies

```bash
# Navigate to project directory
cd /path/to/thai_school_alarm_web

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install new dependencies
pip install -r requirements.txt

# Run Django migrations for django-apscheduler
python manage.py migrate
```

### 2. Verify Installation

```bash
# Check that management command is available
python manage.py run_scheduler --help

# Run tests
pytest -v
```

---

## Running the Scheduler

### Development (Manual)

```bash
# Terminal 1: Run Django web server
python manage.py runserver

# Terminal 2: Run scheduler
python manage.py run_scheduler

# Optional: Disable WiFi monitoring for development
python manage.py run_scheduler --no-wifi-monitor
```

### Production (Linux with systemd)

```bash
# 1. Install the systemd service
sudo cp scripts/scheduler.service.template /etc/systemd/system/thai_school_alarm_scheduler.service

# 2. Edit the service file with your paths
sudo nano /etc/systemd/system/thai_school_alarm_scheduler.service

# Adjust these settings:
# - User=YOUR_USER
# - Group=YOUR_GROUP
# - WorkingDirectory=/YOUR/PROJECT/PATH
# - Environment="PATH=/YOUR/VENV/PATH/bin"
# - ExecStart=/YOUR/VENV/PATH/bin/python manage.py run_scheduler

# 3. Create log directory
sudo mkdir -p /var/log/thai_alarm
sudo chown YOUR_USER:YOUR_GROUP /var/log/thai_alarm

# 4. Reload systemd and start service
sudo systemctl daemon-reload
sudo systemctl enable thai_school_alarm_scheduler.service
sudo systemctl start thai_school_alarm_scheduler.service

# 5. Check status
sudo systemctl status thai_school_alarm_scheduler.service

# View logs
sudo journalctl -u thai_school_alarm_scheduler.service -f
# or
tail -f /var/log/thai_alarm/scheduler.log
```

### Production (Windows)

**Option 1: Task Scheduler**

1. Open Task Scheduler
2. Create Basic Task
3. Name: "Thai School Alarm Scheduler"
4. Trigger: When the computer starts
5. Action: Start a program
   - Program: `C:\path\to\venv\Scripts\python.exe`
   - Arguments: `manage.py run_scheduler`
   - Start in: `C:\path\to\thai_school_alarm_web`

**Option 2: NSSM (Non-Sucking Service Manager)**

```cmd
:: Download NSSM from https://nssm.cc/

:: Install service
nssm install ThaiSchoolAlarmScheduler "C:\path\to\venv\Scripts\python.exe" "manage.py run_scheduler"
nssm set ThaiSchoolAlarmScheduler AppDirectory "C:\path\to\thai_school_alarm_web"

:: Start service
nssm start ThaiSchoolAlarmScheduler

:: Check status
nssm status ThaiSchoolAlarmScheduler
```

---

## Testing

### Run All Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=data --cov-report=html

# View coverage report
# Open htmlcov/index.html in browser
```

### Run Specific Test Categories

```bash
# Unit tests only (fast)
pytest -v -m unit

# Integration tests only
pytest -v -m integration

# Audio tests
pytest -v -m audio

# WiFi tests
pytest -v -m wifi
```

### Manual Testing Checklist

- [ ] Create a test schedule 2 minutes in the future via web UI
- [ ] Verify scheduler logs show the schedule was detected
- [ ] Verify audio plays at the scheduled time
- [ ] Edit the schedule - verify it updates
- [ ] Delete the schedule - verify no audio plays
- [ ] Restart scheduler near schedule time - verify no duplicate playback
- [ ] Test WiFi monitoring (if enabled)
- [ ] Test graceful shutdown (Ctrl+C) - verify audio stops

---

## Troubleshooting

### Scheduler Not Starting

**Problem:** `python manage.py run_scheduler` fails

**Solutions:**
1. Check dependencies installed: `pip list | grep -i apscheduler`
2. Run migrations: `python manage.py migrate`
3. Check Django settings: `django_apscheduler` in `INSTALLED_APPS`
4. Check logs for errors

### Audio Not Playing

**Problem:** Schedules execute but no sound

**Solutions:**
1. Check pygame installed: `pip list | grep pygame`
2. Verify audio files exist: `ls -la audio/bell/`
3. Check audio player state: Check `Utility` model for `audio_playback_state`
4. Test pygame manually:
   ```python
   import pygame
   pygame.mixer.init()
   pygame.mixer.music.load('audio/bell/sound1/First.wav')
   pygame.mixer.music.play()
   ```

### Schedules Not Executing

**Problem:** Scheduler runs but schedules don't execute

**Solutions:**
1. Check timezone settings - must be `Asia/Bangkok`
2. Verify schedule has notification days selected
3. Check idempotency - look for `last_execution_check_schedule` in Utility model
4. Enable debug logging:
   ```python
   # In settings.py
   LOGGING = {
       'version': 1,
       'handlers': {
           'console': {
               'class': 'logging.StreamHandler',
           },
       },
       'loggers': {
           'data.scheduler_jobs': {
               'handlers': ['console'],
               'level': 'DEBUG',
           },
       },
   }
   ```

### Database Locked Errors

**Problem:** `database is locked` errors on SQLite

**Solutions:**
1. Ensure only one scheduler process runs
2. Consider PostgreSQL for production
3. Check file permissions on `db.sqlite3`

### WiFi Monitoring Issues

**Problem:** WiFi monitoring not working

**Solutions:**
1. Disable for testing: `python manage.py run_scheduler --no-wifi-monitor`
2. Check NetworkManager installed: `systemctl status NetworkManager`
3. Verify `wifi_monitor_enabled` in Utility model
4. Check user permissions for network operations

---

## Configuration

### APScheduler Settings

In `settings.py`:

```python
# APScheduler datetime format for display
APSCHEDULER_DATETIME_FORMAT = "N j, Y, f:s a"

# Job execution timeout
APSCHEDULER_RUN_NOW_TIMEOUT = 25  # seconds
```

### Scheduler Job Configuration

Jobs are configured in `data/management/commands/run_scheduler.py`:

- **check_schedule**: Runs every minute
- **monitor_wifi**: Runs every minute (optional)
- **sync_schedules**: Runs every 5 minutes

### Audio Player Configuration

Audio player settings in `data/lib/audio_player.py`:

- **Frequency**: 44100 Hz
- **Channels**: 2 (stereo)
- **Buffer size**: 512

---

## Migration Notes

### Behavioral Changes

1. **Concurrency**: Still limited to 1 instance per job (same as before)
2. **State persistence**: Now stored in Django database (Utility model)
3. **Logging**: Uses Python standard logging (no more `get_task_logger`)
4. **Graceful shutdown**: Improved - stops audio before exiting

### No Breaking Changes

- ✅ Schedule CRUD operations work the same
- ✅ Audio playback sequence unchanged
- ✅ WiFi monitoring logic preserved
- ✅ Time announcement (tell_time) works identically

### Performance Improvements

- ⚡ Faster startup (no broker connection)
- ⚡ Lower memory usage (no separate worker process)
- ⚡ Simpler deployment (one service instead of three)

---

## Monitoring

### Check Scheduler Status

```bash
# Linux (systemd)
sudo systemctl status thai_school_alarm_scheduler.service

# View recent logs
sudo journalctl -u thai_school_alarm_scheduler.service -n 50

# Follow logs in real-time
sudo journalctl -u thai_school_alarm_scheduler.service -f
```

### Important Log Messages

```
✓ Scheduler started successfully        # Startup OK
✓ Added job: check_schedule             # Job registered
Checking schedules at 2026-01-05 08:30  # Job running
✓ Played sound for schedule ID=123      # Audio played
Already executed this minute            # Idempotency protection
```

### Database State Inspection

```python
# Django shell
python manage.py shell

from data.models import Utility

# Check audio playback state
state = Utility.objects.filter(name='audio_playback_state').first()
if state:
    import json
    print(json.loads(state.value))

# Check last execution
exec_state = Utility.objects.filter(name='last_execution_check_schedule').first()
if exec_state:
    print(json.loads(exec_state.value))

# Check WiFi state
wifi_count = Utility.objects.filter(name='wifi_down_count').first()
if wifi_count:
    print(f"WiFi down count: {wifi_count.value}")
```

---

## Rollback (if needed)

If you need to rollback to Celery:

```bash
# 1. Restore old requirements.txt
git checkout HEAD~1 requirements.txt
pip install -r requirements.txt

# 2. Restore old files
git checkout HEAD~1 data/tasks.py
git checkout HEAD~1 thai_school_alarm_web/celery.py
git checkout HEAD~1 thai_school_alarm_web/__init__.py

# 3. Stop and disable scheduler service
sudo systemctl stop thai_school_alarm_scheduler.service
sudo systemctl disable thai_school_alarm_scheduler.service

# 4. Start Celery services
sudo systemctl start thai_school_alarm_celery.service
sudo systemctl start thai_school_alarm_beat.service

# 5. Revert migrations (optional)
python manage.py migrate django_apscheduler zero
```

---

## Support

### Common Commands Reference

```bash
# Start scheduler (development)
python manage.py run_scheduler

# Start scheduler without WiFi monitoring
python manage.py run_scheduler --no-wifi-monitor

# Run tests
pytest
pytest -v -m unit  # unit tests only

# Check service status (production)
sudo systemctl status thai_school_alarm_scheduler.service

# View logs
tail -f /var/log/thai_alarm/scheduler.log

# Restart scheduler
sudo systemctl restart thai_school_alarm_scheduler.service

# Stop scheduler
sudo systemctl stop thai_school_alarm_scheduler.service
```

### File Locations

- **Scheduler jobs**: `data/scheduler_jobs.py`
- **Audio player**: `data/lib/audio_player.py`
- **Management command**: `data/management/commands/run_scheduler.py`
- **Tests**: `data/tests/`
- **Service template**: `scripts/scheduler.service.template`
- **Configuration**: `thai_school_alarm_web/settings.py`

---

## Changelog

### v2.0.0 - APScheduler Migration (2026-02-11)

**Added:**
- APScheduler-based scheduling system
- Cross-platform audio player (pygame)
- Comprehensive test suite (pytest)
- Management command for scheduler
- Idempotency protection
- State persistence in database

**Removed:**
- Celery task queue
- RabbitMQ message broker
- Celery dependencies

**Changed:**
- Simplified deployment (3 services → 2 services)
- Improved graceful shutdown
- Enhanced error handling
- Better logging

---

## Additional Resources

- **APScheduler Documentation**: https://apscheduler.readthedocs.io/
- **Django-APScheduler**: https://github.com/jcass77/django-apscheduler
- **Pygame Documentation**: https://www.pygame.org/docs/
- **Pytest Documentation**: https://docs.pytest.org/

---

**Migration completed successfully! 🎉**

The system is now simpler, more maintainable, and easier to deploy while maintaining all existing functionality.
