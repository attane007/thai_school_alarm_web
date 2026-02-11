# Thai School Alarm Web - Uninstall Guide

This directory contains uninstall scripts for removing Thai School Alarm Web from both Windows and Linux/Raspberry Pi systems.

## Windows Uninstall

### Quick Uninstall (Interactive)
```powershell
# Run PowerShell as Administrator, then:
.\uninstall_windows.ps1
```

The script will:
- Ask for confirmation before proceeding
- Stop the Windows Service (if running)
- Remove the service from the system
- Delete the installation directory
- Optionally remove application data and logs from `%APPDATA%\thai_school_alarm_web`
- Clean up Windows Registry entries

### Force Uninstall (No Prompts)
```powershell
# Use the -Force parameter to skip all confirmation prompts
.\uninstall_windows.ps1 -Force
```

### Custom Installation Path
```powershell
# If installed to a non-default location:
.\uninstall_windows.ps1 -InstallPath "D:\my_app_folder"
```

## Linux / Raspberry Pi Uninstall

### Quick Uninstall (Interactive)
```bash
# Run with sudo:
sudo bash uninstall_linux.sh
```

Or make it executable first:
```bash
chmod +x uninstall_linux.sh
sudo ./uninstall_linux.sh
```

The script will:
- Ask for confirmation before proceeding
- Stop and disable systemd services
- Remove service files from `/etc/systemd/system/`
- Delete the installation directory
- Optionally remove:
  - Application logs from `/var/log/thai_school_alarm_web`
  - Database backups from `/var/backups/thai_school_alarm_web`
  - Cron jobs (if any)
  - Udev rules (if created)

### Custom Installation Path
```bash
# If installed to a non-default location:
sudo bash uninstall_linux.sh /path/to/installation
```

## What Gets Removed

### Both Platforms:
✓ Application executable files  
✓ Python virtual environment  
✓ Application services/daemons  
✓ Configuration files  

### Windows (Additional):
✓ Windows Service registration  
✓ Registry entries  
✓ Application data directory (optional)  
✓ Logs directory (optional)  

### Linux/RPi (Additional):
✓ Systemd service files  
✓ Application logs (optional)  
✓ Database backups (optional)  
✓ Cron jobs (if any)  
✓ Udev rules (if any)  

## What Gets Preserved (on request)

Both scripts offer optional preservation of:
- **Logs**: Useful for debugging if issues occurred
- **Backups**: Database backups (on Linux) if you want to restore data later

When prompted, press:
- `y` or `Y` to remove
- `n` or `N` to keep

## Troubleshooting

### Windows: "requires Administrator privileges"
- Right-click PowerShell → "Run as Administrator"
- Re-run the uninstall script

### Linux: "requires root privileges"
- Use `sudo bash uninstall_linux.sh`
- Not just `bash uninstall_linux.sh`

### Windows: "Service not found"
- This is normal if the service was never created or already removed
- The uninstall will continue with removing files

### Linux: Files still exist after uninstall
- Check file permissions: `ls -la /path/to/install`
- Run again with sudo: `sudo bash uninstall_linux.sh`
- Or manually remove: `sudo rm -rf /path/to/installation`

## Reinstalling After Uninstall

After uninstalling, you can reinstall at any time:

**Windows:**
```powershell
.\deploy_windows.ps1
```

**Linux/RPi:**
```bash
sudo bash deploy_linux.sh
```

## Need Help?

If uninstall fails or you have questions:
1. Check the error messages carefully
2. Ensure you have administrator/root privileges
3. Try the manual removal steps (see Troubleshooting)
4. Check the documentation in WINDOWS_SETUP.md or README.md
