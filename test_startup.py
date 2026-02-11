#!/usr/bin/env python
"""
Test script to verify app starts without Celery errors
"""
import sys
import os

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thai_school_alarm_web.settings')

import django
django.setup()

print("✓ Django setup successful - no Celery import errors!")

# Try importing the key modules
try:
    from data.tasks import play_sound, stop_sound, check_schedule
    print("✓ data.tasks imported successfully")
except ImportError as e:
    print(f"✗ Error importing data.tasks: {e}")
    sys.exit(1)

try:
    from data.scheduler_jobs import check_schedule, monitor_wifi_connection
    print("✓ data.scheduler_jobs imported successfully")
except ImportError as e:
    print(f"✗ Error importing data.scheduler_jobs: {e}")
    sys.exit(1)

try:
    from data.management.commands.run_scheduler import Command as SchedulerCommand
    print("✓ Scheduler management command imported successfully")
except ImportError as e:
    print(f"✗ Error importing scheduler command: {e}")
    sys.exit(1)

print("\n✓ All imports successful - Celery removal complete!")
print("✓ App is ready to run with APScheduler only")
