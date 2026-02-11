"""
Platform abstraction helpers for cross-platform compatibility.
Provides utilities for Windows and Linux compatibility.
"""

import platform
import subprocess
import os
from pathlib import Path
from typing import Optional, Tuple


def is_windows() -> bool:
    """Check if running on Windows."""
    return platform.system() == "Windows"


def is_linux() -> bool:
    """Check if running on Linux."""
    return platform.system() == "Linux"


def is_raspberry_pi() -> bool:
    """Check if running on Raspberry Pi."""
    try:
        with open("/proc/device-tree/model", "r") as f:
            model = f.read().lower()
            return "raspberry pi" in model
    except (FileNotFoundError, IOError):
        return False


def get_app_data_dir() -> Path:
    """Get platform-appropriate app data directory."""
    if is_windows():
        base = Path(os.getenv("APPDATA", os.path.expanduser("~"))) / "thai_school_alarm_web"
    else:
        base = Path.home() / ".thai_school_alarm_web"
    
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_logs_dir() -> Path:
    """Get platform-appropriate logs directory."""
    if is_windows():
        logs_dir = get_app_data_dir() / "logs"
    else:
        logs_dir = Path("/var/log/thai_school_alarm_web")
    
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def get_temp_dir() -> Path:
    """Get platform-appropriate temp directory."""
    if is_windows():
        temp_dir = get_app_data_dir() / "temp"
    else:
        temp_dir = Path("/tmp/thai_school_alarm_web")
    
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def check_process_exists(pid: int) -> bool:
    """
    Check if a process with given PID exists.
    Cross-platform implementation.
    
    Args:
        pid: Process ID to check
        
    Returns:
        True if process exists, False otherwise
    """
    try:
        import psutil
        return psutil.pid_exists(pid)
    except ImportError:
        # Fallback if psutil not available
        if is_windows():
            try:
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return str(pid) in result.stdout
            except Exception:
                return False
        else:
            try:
                subprocess.run(
                    ["ps", "-p", str(pid)],
                    capture_output=True,
                    timeout=5,
                    check=True
                )
                return True
            except (subprocess.CalledProcessError, Exception):
                return False


def run_command(command: list, timeout: int = 30) -> Tuple[int, str, str]:
    """
    Run a command and return exit code, stdout, stderr.
    Cross-platform command execution with timeout.
    
    Args:
        command: List of command arguments
        timeout: Timeout in seconds
        
    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


def get_service_status(service_name: str) -> bool:
    """
    Get service running status.
    Cross-platform implementation.
    
    Args:
        service_name: Name of service to check
        
    Returns:
        True if service is running, False otherwise
    """
    if is_windows():
        try:
            import win32serviceutil
            return win32serviceutil.QueryServiceStatus(service_name)[1] == 4
        except Exception:
            return False
    else:
        try:
            result = subprocess.run(
                ["systemctl", "is-active", service_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False


def restart_service(service_name: str) -> bool:
    """
    Restart a service.
    Cross-platform implementation.
    
    Args:
        service_name: Name of service to restart
        
    Returns:
        True if restart was successful, False otherwise
    """
    if is_windows():
        try:
            import win32serviceutil
            win32serviceutil.RestartService(service_name, waitSecs=5)
            return True
        except Exception:
            return False
    else:
        try:
            subprocess.run(
                ["sudo", "systemctl", "restart", service_name],
                timeout=10,
                check=True
            )
            return True
        except Exception:
            return False


def get_script_path(filename: str) -> Path:
    """
    Get path to a script file.
    Returns appropriate path for platform.
    
    Args:
        filename: Name of script (without extension)
        
    Returns:
        Path to script file
    """
    script_dir = Path(__file__).parent.parent.parent / "scripts"
    
    if is_windows():
        return script_dir / f"{filename}.ps1"
    else:
        return script_dir / f"{filename}.sh"


def path_to_string(p: Path) -> str:
    """Convert Path to string with proper separators."""
    if is_windows():
        return str(p)
    else:
        return str(p)


__all__ = [
    "is_windows",
    "is_linux",
    "is_raspberry_pi",
    "get_app_data_dir",
    "get_logs_dir",
    "get_temp_dir",
    "check_process_exists",
    "run_command",
    "get_service_status",
    "restart_service",
    "get_script_path",
    "path_to_string",
]
