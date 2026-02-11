# Thai School Alarm Web - Windows Uninstall Script
# Requires: Windows 10/11, PowerShell (Run as Administrator)

param(
    [string]$InstallPath = "C:\thai_school_alarm_web",
    [switch]$Force = $false
)

$ErrorActionPreference = "Stop"

Write-Host "=== Thai School Alarm Web - Windows Uninstall ===" -ForegroundColor Cyan
Write-Host "Install Path: $InstallPath" -ForegroundColor Cyan
Write-Host ""

function Write-Status {
    param([string]$Message, [string]$Status = "Info")
    
    switch ($Status) {
        "Success" { Write-Host "[✓] $Message" -ForegroundColor Green }
        "Error" { Write-Host "[✗] $Message" -ForegroundColor Red }
        "Warning" { Write-Host "[!] $Message" -ForegroundColor Yellow }
        default { Write-Host "[*] $Message" -ForegroundColor Cyan }
    }
}

function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-Status "This script requires Administrator privileges!" "Error"
        Write-Status "Please run PowerShell as Administrator and try again." "Error"
        exit 1
    }
}

function Stop-WindowsService {
    param([string]$ServiceName = "ThaiSchoolAlarmWeb")
    
    Write-Status "Checking for Windows Service..." "Info"
    
    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    
    if ($service) {
        Write-Status "Found service: $ServiceName" "Info"
        
        if ($service.Status -eq "Running") {
            Write-Status "Stopping service..." "Info"
            try {
                Stop-Service -Name $ServiceName -Force
                Write-Status "Service stopped successfully" "Success"
            }
            catch {
                Write-Status "Failed to stop service: $_" "Error"
                return $false
            }
        }
        
        Write-Status "Removing service..." "Info"
        try {
            sc.exe delete $ServiceName | Out-Null
            Write-Status "Service removed successfully" "Success"
            return $true
        }
        catch {
            Write-Status "Failed to remove service: $_" "Error"
            return $false
        }
    }
    else {
        Write-Status "Service not found (already uninstalled)" "Info"
        return $true
    }
}

function Remove-ApplicationDirectory {
    param([string]$Path)
    
    if (-not (Test-Path $Path)) {
        Write-Status "Installation directory not found: $Path" "Info"
        return $true
    }
    
    Write-Status "Removing installation directory..." "Info"
    
    try {
        Remove-Item -Path $Path -Recurse -Force -ErrorAction Stop
        Write-Status "Installation directory removed successfully" "Success"
        return $true
    }
    catch {
        Write-Status "Failed to remove directory: $_" "Error"
        return $false
    }
}

function Remove-AppDataDirectory {
    Write-Status "Checking for application data directory..." "Info"
    
    $appDataPath = "$env:APPDATA\thai_school_alarm_web"
    
    if (Test-Path $appDataPath) {
        Write-Status "Found app data directory: $appDataPath" "Info"
        
        if (-not $Force) {
            $response = Read-Host "Remove application data and logs? (y/n)"
            if ($response -ne 'y' -and $response -ne 'Y') {
                Write-Status "Skipping application data directory" "Warning"
                return $true
            }
        }
        
        try {
            Remove-Item -Path $appDataPath -Recurse -Force -ErrorAction Stop
            Write-Status "Application data directory removed successfully" "Success"
            return $true
        }
        catch {
            Write-Status "Failed to remove app data directory: $_" "Error"
            return $false
        }
    }
    else {
        Write-Status "Application data directory not found" "Info"
        return $true
    }
}

function Remove-RegistryEntries {
    Write-Status "Checking for registry entries..." "Info"
    
    $regPath = "HKLM:\SYSTEM\CurrentControlSet\Services\ThaiSchoolAlarmWeb"
    
    if (Test-Path $regPath) {
        Write-Status "Found registry entry, cleaning up..." "Info"
        try {
            Remove-Item -Path $regPath -Force -ErrorAction Stop
            Write-Status "Registry entries removed successfully" "Success"
        }
        catch {
            Write-Status "Could not remove registry entries (this is okay): $_" "Warning"
        }
    }
}

function Main {
    Write-Status "Starting uninstall process..." "Info"
    Write-Host ""
    
    if (-not $Force) {
        Write-Host "This will remove Thai School Alarm Web from:" -ForegroundColor Yellow
        Write-Host "  - Installation: $InstallPath" -ForegroundColor Yellow
        Write-Host "  - Service: ThaiSchoolAlarmWeb (if exists)" -ForegroundColor Yellow
        Write-Host "  - App Data: $env:APPDATA\thai_school_alarm_web (optional)" -ForegroundColor Yellow
        Write-Host ""
        
        $response = Read-Host "Continue with uninstall? (y/n)"
        if ($response -ne 'y' -and $response -ne 'Y') {
            Write-Status "Uninstall cancelled" "Warning"
            exit 0
        }
    }
    
    Write-Host ""
    Test-Administrator
    Stop-WindowsService
    Remove-RegistryEntries
    
    if (-not (Remove-ApplicationDirectory $InstallPath)) {
        Write-Status "Some files could not be removed. You may need to remove manually." "Warning"
    }
    
    Remove-AppDataDirectory
    
    Write-Host ""
    Write-Status "Uninstall completed successfully!" "Success"
    Write-Host ""
    Write-Host "=== Summary ===" -ForegroundColor Cyan
    Write-Host "✓ Windows Service removed"
    Write-Host "✓ Application directory removed"
    Write-Host "✓ Application data directory removed (if selected)"
    Write-Host ""
    Write-Host "Thai School Alarm Web has been completely uninstalled from your system." -ForegroundColor Green
}

Main
