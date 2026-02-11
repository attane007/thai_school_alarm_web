"""
Django Management Command: run_scheduler

This command starts the APScheduler-based scheduler for the school alarm system.
It replaces the Celery worker + beat processes with a single scheduler process.

Usage:
    python manage.py run_scheduler

The scheduler will:
- Check for scheduled alarms every minute
- Monitor WiFi connection every minute
- Sync schedules from database every 5 minutes
- Handle graceful shutdown on SIGINT/SIGTERM
"""

import logging
import signal
import sys
import time
from datetime import datetime

from django.core.management.base import BaseCommand
from django.conf import settings

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED
from django_apscheduler.jobstores import DjangoJobStore

from data.scheduler_jobs import check_schedule, monitor_wifi_connection, sync_schedules_to_apscheduler
from data.lib.audio_player import get_audio_player

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run APScheduler for school alarm scheduling'
    
    def __init__(self):
        super().__init__()
        self.scheduler = None
        self.shutting_down = False
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--no-wifi-monitor',
            action='store_true',
            help='Disable WiFi monitoring (useful for development/testing)',
        )
    
    def handle(self, *args, **options):
        """Main entry point for the management command."""
        
        # Setup logging
        self._setup_logging()
        
        logger.info("=" * 70)
        logger.info("Thai School Alarm Scheduler - Starting...")
        logger.info("=" * 70)
        
        # Create scheduler
        self.scheduler = self._create_scheduler()
        
        # Register signal handlers for graceful shutdown
        self._register_signal_handlers()
        
        # Add scheduled jobs
        self._add_jobs(no_wifi_monitor=options.get('no_wifi_monitor', False))
        
        # Start scheduler
        try:
            logger.info("Starting APScheduler...")
            self.scheduler.start()
            logger.info("✓ Scheduler started successfully")
            
            # Print scheduled jobs
            self._print_scheduled_jobs()
            
            logger.info("Scheduler is now running. Press Ctrl+C to stop.")
            logger.info("-" * 70)
            
            # Keep the main thread alive
            try:
                while not self.shutting_down:
                    time.sleep(1)
            except (KeyboardInterrupt, SystemExit):
                pass
            
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}", exc_info=True)
            sys.exit(1)
        
        finally:
            self._shutdown()
    
    def _setup_logging(self):
        """Configure logging for scheduler."""
        # This is already configured in Django settings, but we can enhance it here
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Set apscheduler logger level
        logging.getLogger('apscheduler').setLevel(logging.INFO)
        logging.getLogger('django_apscheduler').setLevel(logging.INFO)
    
    def _create_scheduler(self) -> BackgroundScheduler:
        """
        Create and configure APScheduler instance.
        
        Returns:
            Configured BackgroundScheduler instance
        """
        scheduler = BackgroundScheduler(
            timezone='Asia/Bangkok',
            job_defaults={
                'coalesce': True,  # Combine missed runs into one
                'max_instances': 1,  # Only one instance of each job at a time
                'misfire_grace_time': 60  # Allow 60 seconds grace for misfires
            }
        )
        
        # Add Django database job store
        scheduler.add_jobstore(DjangoJobStore(), 'default')
        
        # Add event listeners
        scheduler.add_listener(
            self._job_executed_listener,
            EVENT_JOB_EXECUTED
        )
        scheduler.add_listener(
            self._job_error_listener,
            EVENT_JOB_ERROR
        )
        scheduler.add_listener(
            self._job_missed_listener,
            EVENT_JOB_MISSED
        )
        
        return scheduler
    
    def _add_jobs(self, no_wifi_monitor=False):
        """
        Add scheduled jobs to the scheduler.
        
        Args:
            no_wifi_monitor: If True, skip adding WiFi monitoring job
        """
        logger.info("Adding scheduled jobs...")
        
        # Job 1: Check schedules every minute
        self.scheduler.add_job(
            check_schedule,
            trigger=CronTrigger(minute='*', timezone='Asia/Bangkok'),
            id='check_schedule',
            name='Check School Alarm Schedules',
            replace_existing=True,
            max_instances=1,
            coalesce=True
        )
        logger.info("✓ Added job: check_schedule (every minute)")
        
        # Job 2: Monitor WiFi connection every minute (if not disabled)
        if not no_wifi_monitor:
            self.scheduler.add_job(
                monitor_wifi_connection,
                trigger=CronTrigger(minute='*', timezone='Asia/Bangkok'),
                id='monitor_wifi',
                name='Monitor WiFi Connection',
                replace_existing=True,
                max_instances=1,
                coalesce=True
            )
            logger.info("✓ Added job: monitor_wifi (every minute)")
        else:
            logger.info("⊝ Skipped WiFi monitoring (--no-wifi-monitor)")
        
        # Job 3: Sync schedules from database every 5 minutes
        self.scheduler.add_job(
            lambda: sync_schedules_to_apscheduler(self.scheduler),
            trigger=CronTrigger(minute='*/5', timezone='Asia/Bangkok'),
            id='sync_schedules',
            name='Sync Schedules from Database',
            replace_existing=True,
            max_instances=1,
            coalesce=True
        )
        logger.info("✓ Added job: sync_schedules (every 5 minutes)")
    
    def _print_scheduled_jobs(self):
        """Print list of scheduled jobs."""
        jobs = self.scheduler.get_jobs()
        logger.info(f"\nScheduled Jobs ({len(jobs)} total):")
        logger.info("-" * 70)
        for job in jobs:
            logger.info(f"  • {job.name} (ID: {job.id})")
            logger.info(f"    Next run: {job.next_run_time}")
        logger.info("-" * 70)
    
    def _register_signal_handlers(self):
        """Register signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        logger.info("✓ Registered signal handlers (SIGINT, SIGTERM)")
    
    def _signal_handler(self, signum, frame):
        """
        Handle shutdown signals.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_name = 'SIGINT' if signum == signal.SIGINT else 'SIGTERM'
        logger.info(f"\n{signal_name} received - initiating graceful shutdown...")
        self.shutting_down = True
    
    def _shutdown(self):
        """Perform graceful shutdown."""
        logger.info("=" * 70)
        logger.info("Shutting down scheduler...")
        logger.info("=" * 70)
        
        # Stop any playing audio
        try:
            logger.info("Stopping audio playback...")
            player = get_audio_player()
            player.stop()
            player.cleanup()
            logger.info("✓ Audio stopped")
        except Exception as e:
            logger.error(f"Error stopping audio: {e}")
        
        # Shutdown scheduler
        if self.scheduler and self.scheduler.running:
            try:
                logger.info("Shutting down APScheduler...")
                self.scheduler.shutdown(wait=True)
                logger.info("✓ Scheduler shut down successfully")
            except Exception as e:
                logger.error(f"Error shutting down scheduler: {e}")
        
        logger.info("=" * 70)
        logger.info("Scheduler stopped. Goodbye!")
        logger.info("=" * 70)
    
    # Event Listeners
    
    def _job_executed_listener(self, event):
        """Log when a job executes successfully."""
        logger.debug(f"Job '{event.job_id}' executed successfully")
    
    def _job_error_listener(self, event):
        """Log when a job encounters an error."""
        logger.error(
            f"Job '{event.job_id}' raised an exception: {event.exception}",
            exc_info=True
        )
    
    def _job_missed_listener(self, event):
        """Log when a job misses its scheduled run time."""
        logger.warning(
            f"Job '{event.job_id}' missed its scheduled run time "
            f"(scheduled: {event.scheduled_run_time})"
        )
