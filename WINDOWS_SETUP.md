# Thai School Alarm Web - Windows Setup Guide

This guide provides detailed instructions for installing and running Thai School Alarm Web on Windows 10/11.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation Methods](#installation-methods)
   - [Automated Installation (Recommended)](#automated-installation-recommended)
   - [Manual Installation](#manual-installation)
3. [Running the Application](#running-the-application)
4. [Windows Service Setup](#windows-service-setup)
5. [Troubleshooting](#troubleshooting)
6. [Feature Limitations on Windows](#feature-limitations-on-windows)
7. [Uninstallation](#uninstallation)

---

## System Requirements

### Minimum Requirements

- **OS**: Windows 10 (build 19041) or Windows 11
- **Python**: 3.10 or higher
- **RAM**: 2 GB minimum (4 GB recommended)
- **Disk Space**: 500 MB for installation
- **Administrator Access**: Required for Windows Service installation

### Recommended Setup

- Windows 11 latest build
- Python 3.12
- 4+ GB RAM
- SSD storage
- Run PowerShell as Administrator

### Optional

- **ffmpeg** for advanced audio playback options (recommended for A/V functionality)
  - Download: https://ffmpeg.org/download.html
  - Or install via: `choco install ffmpeg` (if using Chocolatey)

---

## Installation Methods

### Automated Installation (Recommended)

The easiest way to get started is using the provided PowerShell deployment script.

#### Step 1: Download and Extract

1. Download the Thai School Alarm Web project files
2. Extract to your desired location (e.g., `C:\thai_school_alarm_web` or `C:\Users\YourUsername\Documents\thai_school_alarm_web`)

#### Step 2: Install Python

If you don't have Python 3.10+ installed:

1. Visit https://www.python.org/downloads/
2. Download the latest Python 3.12 installer
3. **Important**: Check "Add Python to PATH" during installation
4. Complete the installation

#### Step 3: Run the Deployment Script

1. Open **PowerShell as Administrator**:
   - Right-click PowerShell → "Run as Administrator"
   - Or search for "PowerShell" in Start Menu, right-click, "Run as Administrator"

2. Navigate to the project directory:
   ```powershell
   cd "C:\thai_school_alarm_web"
   ```

3. Run the deployment script:
   ```powershell
   .\deploy_windows.ps1
   ```

4. The script will:
   - Check Python installation
   - Create a virtual environment
   - Install all dependencies
   - Initialize the database
   - Provide setup instructions

5. **First time setup only**: Create a superuser (admin account) for the web interface:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   python manage.py createsuperuser
   ```

---

### Manual Installation

If you prefer manual setup or the script encounters issues:

#### Step 1: Create Virtual Environment

```powershell
cd "C:\thai_school_alarm_web"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

#### Step 2: Install Dependencies

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 3: Initialize Database

```powershell
python manage.py migrate
python manage.py shell
```

In the Python shell:
```python
from data.models import Day

days_data = [
    {'name_thai': 'จันทร์', 'name_eng': 'Monday'},
    {'name_thai': 'อังคาร', 'name_eng': 'Tuesday'},
    {'name_thai': 'พุธ', 'name_eng': 'Wednesday'},
    {'name_thai': 'พฤหัสบดี', 'name_eng': 'Thursday'},
    {'name_thai': 'ศุกร์', 'name_eng': 'Friday'},
    {'name_thai': 'เสาร์', 'name_eng': 'Saturday'},
    {'name_thai': 'อาทิตย์', 'name_eng': 'Sunday'},
]

for day_data in days_data:
    Day.objects.get_or_create(**day_data)

print("Database initialized successfully")
exit()
```

#### Step 4: Create Superuser

```powershell
python manage.py createsuperuser
```

Follow the prompts to create an admin account.

---

## Running the Application

### Option 1: Development Server (Simple)

Perfect for testing and development:

```powershell
# Activate virtual environment (if not already activated)
.\.venv\Scripts\Activate.ps1

# Start Django server
python manage.py runserver 0.0.0.0:8000

# In another PowerShell window, start the scheduler
.\.venv\Scripts\Activate.ps1
python manage.py run_scheduler
```

Access the application at: **http://localhost:8000**

### Option 2: Windows Service (Recommended for Production)

Runs the scheduler automatically in the background:

#### Install the Service

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run the service installation script
cd scripts
python install_windows_service.py install
cd ..
```

#### Start the Service

```powershell
Start-Service -Name ThaiSchoolAlarmWeb
```

#### Check Service Status

```powershell
Get-Service -Name ThaiSchoolAlarmWeb
```

#### Stop the Service

```powershell
Stop-Service -Name ThaiSchoolAlarmWeb
```

#### View Service Logs

Logs are stored in: `%APPDATA%\Local\thai_school_alarm_web\logs\scheduler_service.log`

View recent logs:
```powershell
Get-Content "$env:APPDATA\Local\thai_school_alarm_web\logs\scheduler_service.log" -Tail 50
```

#### Uninstall the Service

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Remove service
cd scripts
python install_windows_service.py remove
cd ..
```

---

## Configuration

### Web Server Configuration

For **Development** (single user, testing):
```powershell
python manage.py runserver 0.0.0.0:8000
```

For **Production** (multiple users, stable):
- Install Gunicorn: `pip install gunicorn`
- Run: `gunicorn --bind 0.0.0.0:8000 --workers 4 thai_school_alarm_web.wsgi`

### Environment Configuration

Create a `.env` file in the project root (if not already created during setup):

```
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com
CSRF_TRUSTED_ORIGINS=http://localhost:8000,https://your-domain.com
```

### Accessing on Other Computers

To access from other machines on your network:

1. Find your computer's IP address:
   ```powershell
   ipconfig
   ```
   Look for "IPv4 Address" (usually starts with 192.168.x.x or 10.x.x.x)

2. From another computer, visit: `http://YOUR_IP:8000`

3. To allow external access through Cloudflare Tunnel (recommended for remote access):
   - Install Cloudflare Tunnel
   - Create a tunnel to `localhost:8000`
   - Update `CSRF_TRUSTED_ORIGINS` in `.env`

---

## Windows Service Setup (Detailed)

### Automatic Startup

The Windows Service is configured to start automatically when Windows boots. To verify:

```powershell
Get-Service -Name ThaiSchoolAlarmWeb | Select-Object Name, DisplayName, StartType
```

To change startup behavior:
```powershell
# Auto start (default)
Set-Service -Name ThaiSchoolAlarmWeb -StartupType Automatic

# Manual start (user-triggered)
Set-Service -Name ThaiSchoolAlarmWeb -StartupType Manual

# Disabled
Set-Service -Name ThaiSchoolAlarmWeb -StartupType Disabled
```

### Monitoring Service Health

Create a batch script to monitor and restart service if needed:

Create `check_service.bat`:
```batch
@echo off
setlocal enabledelayedexpansion

:loop
sc query ThaiSchoolAlarmWeb | find "RUNNING" >nul
if errorlevel 1 (
    echo Service not running, starting...
    net start ThaiSchoolAlarmWeb
)
timeout /t 300 /nobreak
goto loop
```

Run with Task Scheduler:
1. Open Task Scheduler
2. Create Basic Task
3. Set trigger to At system startup
4. Add action: Start `check_service.bat`

---

## Troubleshooting

### Issue: "Python not found" or "Python not in PATH"

**Solution 1**: Reinstall Python and ensure "Add Python to PATH" is checked

**Solution 2**: Manually add Python to PATH:
```powershell
# Find Python installation
python --version
# Get installation path
python -c "import sys; print(sys.executable)"

# Add to PATH (replace C:\Python312 with your path)
# Open Environment Variables (Settings > Environment Variables)
# Add the Python installation directory to the System PATH
```

### Issue: "Permission Denied" errors

**Solution**: Run PowerShell as Administrator

```powershell
# Check if running as admin
$isAdmin = ([Security.Principal.WindowsIdentity]::GetCurrent().Groups -match "S-1-5-32-544")
Write-Host "Is Admin: $isAdmin"
```

### Issue: Virtual Environment not activating

**Solution**: Check the path and use absolute path:

```powershell
& "C:\thai_school_alarm_web\.venv\Scripts\Activate.ps1"
```

Or disable execution policy temporarily:
```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
.\.venv\Scripts\Activate.ps1
```

### Issue: Port 8000 already in use

**Find process using port 8000**:
```powershell
netstat -ano | findstr :8000
# Get the PID and kill it
taskkill /PID <PID> /F
```

**Or use a different port**:
```powershell
python manage.py runserver 0.0.0.0:8001
```

### Issue: Database locked or corrupted

**Solution**: Reset the database:

```powershell
# Remove old database
Remove-Item db.sqlite3

# Recreate database
python manage.py migrate
python manage.py shell
# ... run the Day creation code from manual setup
```

### Issue: Service won't start

**Check service logs**:
```powershell
Get-Content "$env:APPDATA\Local\thai_school_alarm_web\logs\scheduler_service.log"
```

**Check Windows Event Viewer**:
1. Open Event Viewer (search in Start Menu)
2. Look in Windows Logs > System or Application
3. Search for "ThaiSchoolAlarmWeb"

### Issue: Scheduler not running scheduled tasks

**Verify scheduler is running**:
```powershell
# If using development server, you need TWO windows:
# Window 1: python manage.py runserver
# Window 2: python manage.py run_scheduler

# If using Windows Service:
Get-Service -Name ThaiSchoolAlarmWeb
```

---

## Feature Limitations on Windows

### Not Supported on Windows

❌ **WiFi Network Management**
- Cannot connect/disconnect from WiFi networks
- Cannot scan nearby networks
- Cannot configure network settings

❌ **Access Point (AP) Mode**
- Cannot broadcast as a WiFi hotspot
- This feature requires Linux-specific tools

❌ **System Integration**
- Cannot manage system daemons
- Limited system monitor functions

### Fully Supported on Windows

✅ **Alarm Scheduling**
- Create and manage schedules
- Enable/disable schedules
- Choose notification time windows

✅ **Audio Playback**
- Play bell sounds
- Play notification sounds
- Tell time feature (with Thai language)

✅ **Web Interface**
- Full web UI functionality
- Settings and configuration
- Schedule management
- Notification history

✅ **Database**
- SQLite database (included)
- User authentication
- Data persistence

---

## Uninstallation

### Complete Removal

```powershell
# 1. Stop the service (if installed)
Stop-Service -Name ThaiSchoolAlarmWeb

# 2. Remove the service
cd "C:\thai_school_alarm_web\scripts"
python install_windows_service.py remove
cd ..

# 3. Delete the installation directory
Remove-Item -Recurse -Force "C:\thai_school_alarm_web"

# 4. Optional: Remove from Programs and Features
# (The app is not installed via Windows installer, so no entry there)
```

### Keep Configuration

To preserve your schedules and settings:

```powershell
# Only delete non-essential files
Remove-Item -Recurse -Force "C:\thai_school_alarm_web\.venv"
Remove-Item -Recurse -Force "C:\thai_school_alarm_web\__pycache__"
Remove-Item "C:\thai_school_alarm_web\*.log"

# Keep these:
# - db.sqlite3 (contains all your schedules)
# - .env (your configuration)
# - audio/ (your audio files)
```

---

## Getting Help

### Debug Mode

Run with verbose logging:

```powershell
# Set debug environment variable
$env:DEBUG = "True"
python manage.py runserver 0.0.0.0:8000
```

Check logs in: `%APPDATA%\Local\thai_school_alarm_web\logs\`

### Common Log Files

- **Django**: `%APPDATA%\Local\thai_school_alarm_web\logs\django.log`
- **Scheduler**: `%APPDATA%\Local\thai_school_alarm_web\logs\scheduler_service.log`
- **Audio**: `%APPDATA%\Local\thai_school_alarm_web\logs\play_sound.log`

### Testing

Run the application in test mode:

```powershell
python manage.py test
```

---

## Advanced Topics

### Using a Network Database

Instead of SQLite, use a networked database:

#### PostgreSQL

```powershell
# Install pg driver
pip install psycopg2-binary

# Update .env
# DATABASE_URL=postgresql://user:password@localhost/thai_alarm

# Update settings.py to use DATABASE_URL
```

#### MySQL

```powershell
# Install MySQL driver
pip install mysqlclient

# Update .env
# DATABASE_URL=mysql://user:password@localhost/thai_alarm
```

### Using Gunicorn with Nginx (Windows with WSL2)

For a production-grade setup, use Windows Subsystem for Linux 2 (WSL2):

```powershell
# Install WSL2
wsl --install

# Inside WSL2, follow Linux installation instructions
# Then proxy requests from Windows to WSL2 via nginx
```

### Backup and Restore

**Backup your data**:
```powershell
# Backup database
Copy-Item db.sqlite3 "db.sqlite3.backup.$(Get-Date -Format 'yyyyMMdd')"

# Backup .env file
Copy-Item .env ".env.backup.$(Get-Date -Format 'yyyyMMdd')"

# Backup audio folder
Copy-Item -Recurse audio "audio.backup.$(Get-Date -Format 'yyyyMMdd')"
```

**Restore**:
```powershell
Copy-Item "db.sqlite3.backup.20231215" db.sqlite3
Copy-Item ".env.backup.20231215" .env
# Restart application
```

---

## System Monitoring

Monitor the application health:

```powershell
# Check memory usage
Get-Process ThaiSchoolAlarmWeb | Select-Object Name, WorkingSet

# Check CPU usage over time
Get-Counter -Counter "\Process(python)\% Processor Time" -SampleInterval 2 -MaxSamples 5

# Check database size
(Get-Item db.sqlite3).Length / 1MB  # in megabytes

# Check logs folder size
(Get-ChildItem "$env:APPDATA\Local\thai_school_alarm_web\logs" -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
```

---

## Version Updates

To update to a newer version:

```powershell
# 1. Stop the scheduler
Stop-Service -Name ThaiSchoolAlarmWeb

# 2. Backup your data
Copy-Item db.sqlite3 "db.sqlite3.backup.$(Get-Date -Format 'yyyyMMdd')"

# 3. Download new version and extract over existing (or to new directory)

# 4. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 5. Update dependencies
pip install -r requirements.txt

# 6. Run migrations
python manage.py migrate

# 7. Restart service
Start-Service -Name ThaiSchoolAlarmWeb
```

---

## Next Steps

After installation:

1. **Access the web interface**: http://localhost:8000
2. **Log in**: Use the superuser account created during setup
3. **Upload audio files**: Via the web interface in "Sound Settings"
4. **Create schedules**: Add alarm times and notification preferences
5. **Test playback**: Play sounds to verify audio is working
6. **Set to automatic**: Enable Windows Service for production use

---

## Support

For issues, feature requests, or contributions:
- Check the main [README.md](../readme.md)
- Review [MIGRATION_GUIDE.md](../MIGRATION_GUIDE.md) for version-specific information
- Check logs in: `%APPDATA%\Local\thai_school_alarm_web\logs\`

---

**Last Updated**: 2024-11-15  
**Windows Support**: Python 3.10+, Windows 10/11
