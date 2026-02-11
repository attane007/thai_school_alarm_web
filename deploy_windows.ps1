# Thai School Alarm Web - Windows Deployment Script
# Requires: Windows 10/11, Python 3.10+, PowerShell (Run as Administrator)

param(
    [string]$PythonVersion = "3.10",
    [string]$InstallPath = "C:\thai_school_alarm_web",
    [switch]$SkipPythonCheck = $false,
    [switch]$CreateService = $false
)

$ErrorActionPreference = "Stop"
$scriptPath = Split-Path -Parent -Path $MyInvocation.MyCommand.Definition

Write-Host "=== Thai School Alarm Web - Windows Deployment ===" -ForegroundColor Cyan
Write-Host "Install Path: $InstallPath" -ForegroundColor Cyan

# Function to write colored output
function Write-Status {
    param([string]$Message, [string]$Status = "Info")
    
    switch ($Status) {
        "Success" { Write-Host "[✓] $Message" -ForegroundColor Green }
        "Error" { Write-Host "[✗] $Message" -ForegroundColor Red }
        "Warning" { Write-Host "[!] $Message" -ForegroundColor Yellow }
        default { Write-Host "[*] $Message" -ForegroundColor Cyan }
    }
}

# Check if running as Administrator
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-Status "This script requires Administrator privileges!" "Error"
        Write-Status "Please run PowerShell as Administrator and try again." "Error"
        exit 1
    }
}

# Check Python installation
function Test-PythonInstallation {
    param([string]$MinVersion = "3.10")
    
    Write-Status "Checking Python installation..." "Info"
    
    try {
        $pythonVersion = python --version 2>&1
        Write-Status "Found: $pythonVersion" "Success"
        
        # Extract version number
        if ($pythonVersion -match "Python (\d+\.\d+)") {
            $version = [version]$matches[1]
            $minVer = [version]$MinVersion
            
            if ($version -ge $minVer) {
                return $true
            } else {
                Write-Status "Python $MinVersion or higher required. Found: $pythonVersion" "Error"
                return $false
            }
        }
    }
    catch {
        Write-Status "Python not found or not in PATH" "Error"
        return $false
    }
}

# Create virtual environment
function Create-VirtualEnvironment {
    param([string]$VenvPath)
    
    Write-Status "Creating Python virtual environment..." "Info"
    
    if (Test-Path $VenvPath) {
        Write-Status "Virtual environment already exists at $VenvPath" "Warning"
        return $true
    }
    
    try {
        python -m venv $VenvPath
        Write-Status "Virtual environment created successfully" "Success"
        return $true
    }
    catch {
        Write-Status "Failed to create virtual environment: $_" "Error"
        return $false
    }
}

# Activate virtual environment and install dependencies
function Install-Dependencies {
    param(
        [string]$VenvPath,
        [string]$RequirementsFile
    )
    
    Write-Status "Installing dependencies..." "Info"
    
    # Source the activation script
    $activateScript = Join-Path $VenvPath "Scripts\Activate.ps1"
    
    if (-not (Test-Path $activateScript)) {
        Write-Status "Activation script not found at $activateScript" "Error"
        return $false
    }
    
    try {
        & $activateScript
        
        Write-Status "Upgrading pip..." "Info"
        python -m pip install --upgrade pip
        
        Write-Status "Installing requirements from $RequirementsFile..." "Info"
        pip install -r $RequirementsFile
        
        Write-Status "Dependencies installed successfully" "Success"
        return $true
    }
    catch {
        Write-Status "Failed to install dependencies: $_" "Error"
        return $false
    }
}

# Initialize database
function Initialize-Database {
    param([string]$VenvPath)
    
    Write-Status "Initializing database..." "Info"
    
    try {
        & (Join-Path $VenvPath "Scripts\Activate.ps1")
        
        Write-Status "Running migrations..." "Info"
        python manage.py migrate
        
        Write-Status "Creating default groups and permissions..." "Info"
        $initScript = @'
from django.contrib.auth.models import Group, Permission
from data.models import Day

# Create default days if not exist
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
'@

        $initScript | python manage.py shell
        
        Write-Status "Database initialized successfully" "Success"
        return $true
    }
    catch {
        Write-Status "Failed to initialize database: $_" "Error"
        return $false
    }
}

# Create Windows Service
function Install-WindowsService {
    param([string]$InstallDir)
    
    Write-Status "Installing Windows Service..." "Info"
    
    if (-not (Test-Administrator)) {
        Write-Status "Windows Service installation requires Administrator privileges" "Error"
        return $false
    }
    
    try {
        $pythonExe = Join-Path $InstallDir ".venv\Scripts\python.exe"
        $serviceScript = Join-Path $InstallDir "scripts\install_windows_service.py"
        
        if (-not (Test-Path $serviceScript)) {
            Write-Status "Service installation script not found at $serviceScript" "Warning"
            return $false
        }
        
        & $pythonExe $serviceScript
        
        Write-Status "Windows Service installed successfully" "Success"
        Write-Status "Start the service with: Start-Service -Name ThaiSchoolAlarmWeb" "Info"
        return $true
    }
    catch {
        Write-Status "Failed to install Windows Service: $_" "Error"
        return $false
    }
}

# Main installation flow
function Main {
    Write-Status "Starting deployment..." "Info"
    Write-Host ""
    
    # Check administrator privileges
    Test-Administrator
    
    # Check Python installation
    if (-not $SkipPythonCheck) {
        if (-not (Test-PythonInstallation $PythonVersion)) {
            Write-Status "Please install Python $PythonVersion or higher from https://www.python.org/" "Error"
            exit 1
        }
    }
    
    # Create installation directory
    if (-not (Test-Path $InstallPath)) {
        Write-Status "Creating installation directory..." "Info"
        New-Item -ItemType Directory -Path $InstallPath | Out-Null
    }
    
    # Copy project files (if running from source directory)
    if ($scriptPath -ne $InstallPath) {
        Write-Status "Copying project files to $InstallPath..." "Info"
        Copy-Item -Path "$scriptPath\*" -Destination $InstallPath -Recurse -Force
    }
    
    # Create virtual environment
    $venvPath = Join-Path $InstallPath ".venv"
    if (-not (Create-VirtualEnvironment $venvPath)) {
        exit 1
    }
    
    # Install dependencies
    $requirementsFile = Join-Path $InstallPath "requirements.txt"
    if (-not (Install-Dependencies $venvPath $requirementsFile)) {
        exit 1
    }
    
    # Initialize database
    Push-Location $InstallPath
    if (-not (Initialize-Database $venvPath)) {
        Pop-Location
        exit 1
    }
    Pop-Location
    
    # Create Windows Service (optional)
    if ($CreateService) {
        Install-WindowsService $InstallPath
    }
    
    Write-Host ""
    Write-Status "Deployment completed successfully!" "Success"
    Write-Host ""
    Write-Host "=== Next Steps ===" -ForegroundColor Cyan
    Write-Host "1. Start the application:"
    Write-Host "   cd $InstallPath"
    Write-Host "   .\.venv\Scripts\Activate.ps1"
    Write-Host "   python manage.py runserver 0.0.0.0:8000"
    Write-Host ""
    Write-Host "2. Access the web interface:"
    Write-Host "   http://localhost:8000"
    Write-Host ""
    if ($CreateService) {
        Write-Host "3. Start the service:"
        Write-Host "   Start-Service -Name ThaiSchoolAlarmWeb"
        Write-Host ""
    }
    Write-Host "Note: WiFi and AP mode features are not supported on Windows." -ForegroundColor Yellow
    Write-Host "Core scheduling and audio playback features will work normally." -ForegroundColor Yellow
}

# Run main installation
Main
