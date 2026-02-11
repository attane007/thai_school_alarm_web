# Thai School Alarm Web - Windows Quick Start

A 5-minute setup guide for Windows users.

## Prerequisites

- ✅ Windows 10 or 11
- ✅ Administrator access
- ✅ Python 3.10 or higher (not installed? [Download here](https://www.python.org/downloads/))

## Installation (5 minutes)

### Step 1: Get the Code (1 minute)

```powershell
# Extract the project files to your desired location
# Example: C:\thai_school_alarm_web
Set-Location "C:\thai_school_alarm_web"
```

### Step 2: Run Installation Script (3 minutes)

```powershell
# Open PowerShell as Administrator
# Press Windows Key, type "powershell", right-click "Windows PowerShell", select "Run as Administrator"

Set-Location "C:\thai_school_alarm_web"
.\deploy_windows.ps1
```

The script will:
- ✓ Verify Python installation
- ✓ Create virtual environment
- ✓ Install dependencies
- ✓ Set up database

### Step 3: Start the Application (1 minute)

#### For Testing/Development:

```powershell
cd "C:\thai_school_alarm_web"
.\.venv\Scripts\Activate.ps1
python manage.py run_scheduler
```

In a **new PowerShell window** (don't close the first one):
```powershell
cd "C:\thai_school_alarm_web"
.\.venv\Scripts\Activate.ps1
python manage.py runserver 0.0.0.0:8000
```

#### For Production (Automatic):

```powershell
cd "C:\thai_school_alarm_web\scripts"
python install_windows_service.py install
# Then start: Start-Service -Name ThaiSchoolAlarmWeb
```

### Step 4: Access the Application (1 minute)

Open your web browser and go to: **http://localhost:8000**

Default login:
- Username: `admin` (or whatever you set during setup)
- Password: (what you entered during setup)

## Usage

### Create a Schedule

1. Log into the web interface
2. Go to "Schedules" section
3. Click "Add Schedule"
4. Set:
   - **Time**: The alarm time (e.g., 8:30 AM)
   - **Days**: Which days to repeat
   - **Sound**: Select a sound file
   - **Options**: Tell time, bell sounds, etc.
5. Click Save

### Test Audio Playback

1. Go to "Sound Settings"
2. Select an audio file
3. Click "Play" to test

### Add Your Own Audio Files

1. Click "Upload Sound" in Sound Settings
2. Select .wav or .mp3 files
3. Files will be available in the schedule dropdown

## Stopping the Application

### Development Mode:
Press `Ctrl+C` in both PowerShell windows

### Windows Service:
```powershell
Stop-Service -Name ThaiSchoolAlarmWeb
```

## Common Issues

### "PowerShell script cannot be loaded"

Run this once in PowerShell (as Admin):
```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope CurrentUser
```

### "Port 8000 is already in use"

```powershell
python manage.py runserver 0.0.0.0:8001  # Use port 8001 instead
```

Then access: http://localhost:8001

### "Permission denied" or "Access is denied"

- Make sure PowerShell is running as Administrator
- Right-click PowerShell → "Run as Administrator"

## Advanced

- **Full Setup Guide**: Read [WINDOWS_SETUP.md](WINDOWS_SETUP.md)
- **Troubleshooting**: See WINDOWS_SETUP.md → Troubleshooting section
- **Linux/Raspberry Pi**: See [readme.md](readme.md)

## What's NOT Supported on Windows

❌ WiFi network switching  
❌ WiFi Access Point (AP) mode  
❌ System WiFi control  

✅ Everything else works perfectly!

## Next Steps

1. **Configure Schedules**: Set up your alarm times
2. **Add Audio**: Upload your bell sounds and audio files
3. **Test**: Verify audio playback works
4. **Set to Auto-Start**: Use Windows Service for production

---

**Need help?** Check [WINDOWS_SETUP.md](WINDOWS_SETUP.md) for detailed instructions.
