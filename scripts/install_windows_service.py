"""
Windows Service Wrapper for Thai School Alarm Web Scheduler

This script manages the installation and operation of the Thai School Alarm Web
scheduler as a Windows Service using pywin32.

Usage:
    python install_windows_service.py install    # Install as Windows Service
    python install_windows_service.py start      # Start the service
    python install_windows_service.py stop       # Stop the service
    python install_windows_service.py remove     # Uninstall the service
"""

import os
import sys
import logging
from pathlib import Path

try:
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager
    import socket
except ImportError:
    print("ERROR: pywin32 not installed. Run: pip install pywin32")
    sys.exit(1)

# Configure logging
log_dir = Path.home() / "AppData" / "Local" / "thai_school_alarm_web" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "scheduler_service.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Get the project root directory (parent of scripts directory)
PROJECT_ROOT = Path(__file__).parent.parent.absolute()


class ThaiSchoolAlarmSchedulerService(win32serviceutil.ServiceFramework):
    """Windows Service wrapper for the Thai School Alarm Web scheduler"""
    
    _svc_name_ = "ThaiSchoolAlarmWeb"
    _svc_display_name_ = "Thai School Alarm Web Scheduler"
    _svc_description_ = "Manages scheduling and audio playback for Thai School Alarm system"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.is_alive = True
        self.process = None
        
    def SvcStop(self):
        """Handle service stop request"""
        logger.info("Received SERVICE_CONTROL_STOP signal")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.is_alive = False
        
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception as e:
                logger.error(f"Error stopping scheduler process: {e}")
                if self.process:
                    self.process.kill()
        
        win32event.SetEvent(self.hWaitStop)
    
    def SvcStart(self):
        """Handle service start request"""
        logger.info("Thai School Alarm Web Scheduler service starting...")
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        self.main()
    
    def main(self):
        """Main service loop"""
        import subprocess
        
        try:
            # Activate virtual environment and run scheduler
            venv_python = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
            
            if not venv_python.exists():
                logger.error(f"Python executable not found at {venv_python}")
                return
            
            logger.info(f"Starting scheduler with: {venv_python}")
            
            # Run the scheduler management command
            self.process = subprocess.Popen(
                [
                    str(venv_python),
                    "manage.py",
                    "run_scheduler"
                ],
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            logger.info(f"Scheduler started with PID: {self.process.pid}")
            
            # Wait for process to complete
            while self.is_alive:
                return_code = self.process.poll()
                
                if return_code is not None:
                    stdout, stderr = self.process.communicate()
                    logger.error(f"Scheduler exited with code {return_code}")
                    
                    if stdout:
                        logger.info(f"stdout: {stdout}")
                    if stderr:
                        logger.error(f"stderr: {stderr}")
                    
                    break
                
                # Check every 5 seconds
                import time
                time.sleep(5)
                
        except Exception as e:
            logger.error(f"Service error: {e}", exc_info=True)
            servicemanager.LogErrorMsg(f"Thai School Alarm Web Error: {str(e)}")
        finally:
            if self.process:
                try:
                    self.process.terminate()
                except:
                    pass
            
            logger.info("Thai School Alarm Web Scheduler service stopped")


def handle_command(args):
    """Handle command-line arguments"""
    if len(args) > 1:
        command = args[1].lower()
        
        if command == 'install':
            logger.info("Installing Windows Service...")
            win32serviceutil.InstallService(
                ThaiSchoolAlarmSchedulerService,
                ThaiSchoolAlarmSchedulerService._svc_name_,
                displayName=ThaiSchoolAlarmSchedulerService._svc_display_name_,
                description=ThaiSchoolAlarmSchedulerService._svc_description_,
                startType=win32service.SERVICE_AUTO_START
            )
            logger.info("Service installed successfully")
            print("✓ Thai School Alarm Web Scheduler installed as Windows Service")
            print("  Start with: Start-Service -Name ThaiSchoolAlarmWeb")
            print("  Stop with: Stop-Service -Name ThaiSchoolAlarmWeb")
            return
            
        elif command == 'start':
            logger.info("Starting Windows Service...")
            win32serviceutil.StartService(ThaiSchoolAlarmSchedulerService._svc_name_)
            print("✓ Service started")
            return
            
        elif command == 'stop':
            logger.info("Stopping Windows Service...")
            win32serviceutil.StopService(ThaiSchoolAlarmSchedulerService._svc_name_)
            print("✓ Service stopped")
            return
            
        elif command == 'remove':
            logger.info("Removing Windows Service...")
            win32serviceutil.RemoveService(ThaiSchoolAlarmSchedulerService._svc_name_)
            logger.info("Service removed successfully")
            print("✓ Thai School Alarm Web Scheduler removed from Windows Service")
            return
    
    # Default: Run as service
    win32serviceutil.HandleCommandLine(ThaiSchoolAlarmSchedulerService)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] in ['install', 'start', 'stop', 'remove', 'update']:
        handle_command(sys.argv)
    else:
        win32serviceutil.HandleCommandLine(ThaiSchoolAlarmSchedulerService)
