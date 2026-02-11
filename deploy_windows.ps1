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
        "Success" { Write-Host "[+] $Message" -ForegroundColor Green }
        "Error" { Write-Host "[-] $Message" -ForegroundColor Red }
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

# Find Python in PATH or common locations
function Find-Python {
    Write-Status "Searching for Python installation..." "Info"
    
    # Search common installation paths first (more reliable)
    $searchPaths = @(
        "C:\Python312\python.exe",
        "C:\Python311\python.exe",
        "C:\Python310\python.exe",
        "C:\Python39\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
        "$env:ProgramFiles\Python312\python.exe",
        "$env:ProgramFiles\Python311\python.exe",
        "$env:ProgramFiles\Python310\python.exe"
    )
    
    # Check each common path
    foreach ($path in $searchPaths) {
        if (Test-Path $path) {
            Write-Status "Found Python at: $path" "Success"
            return $path
        }
    }
    
    # Try python command from PATH (but skip Windows Store stub)
    try {
        $pythonPath = (Get-Command python -ErrorAction Stop).Source
        
        # Skip Windows Store stub
        if ($pythonPath -notmatch "WindowsApps" -and $pythonPath -notmatch "Microsoft Store") {
            Write-Status "Found Python at: $pythonPath" "Success"
            return $pythonPath
        }
    } catch {
        # Continue to next attempt
    }
    
    # Try python3 command
    try {
        $pythonPath = (Get-Command python3 -ErrorAction Stop).Source
        
        # Skip Windows Store stub
        if ($pythonPath -notmatch "WindowsApps" -and $pythonPath -notmatch "Microsoft Store") {
            Write-Status "Found Python3 at: $pythonPath" "Success"
            return $pythonPath
        }
    } catch {
        # Continue - no python3 found
    }
    
    return $null
}

# Create virtual environment
function Create-VirtualEnvironment {
    param([string]$PythonExe, [string]$VenvPath)
    
    Write-Status "Creating Python virtual environment..." "Info"
    
    if (Test-Path $VenvPath) {
        Write-Status "Virtual environment already exists at $VenvPath" "Warning"
        return $true
    }
    
    try {
        & $PythonExe -m venv $VenvPath
        Write-Status "Virtual environment created successfully" "Success"
        return $true
    }
    catch {
        Write-Status "Failed to create virtual environment: $_" "Error"
        return $false
    }
}

# Install dependencies
function Install-Dependencies {
    param([string]$VenvPath, [string]$RequirementsFile)
    
    Write-Status "Installing dependencies..." "Info"
    
    $pipExe = Join-Path $VenvPath "Scripts\pip.exe"
    
    if (-not (Test-Path $pipExe)) {
        Write-Status "Pip not found at $pipExe" "Error"
        return $false
    }
    
    try {
        Write-Status "Upgrading pip..." "Info"
        & $pipExe install --upgrade pip --quiet
        Write-Status "Pip upgraded" "Success"
        
        Write-Status "Installing requirements from $RequirementsFile..." "Info"
        $activity = "Installing Python packages"
        
        # Count total requirements
        $totalPackages = @(Get-Content $RequirementsFile | Where-Object {$_ -notmatch "^#" -and $_ -notmatch "^\s*$"}).Count
        Write-Progress -Activity $activity -Status "Starting installation..." -PercentComplete 10
        
        & $pipExe install -r $RequirementsFile --quiet
        
        Write-Progress -Activity $activity -Status "Installation complete" -PercentComplete 100
        Write-Progress -Activity $activity -Completed
        
        Write-Status "Dependencies installed successfully ($totalPackages packages)" "Success"
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
    
    $pythonExe = Join-Path $VenvPath "Scripts\python.exe"
    
    try {
        Write-Status "Running migrations..." "Info"
        & $pythonExe manage.py migrate --run-syncdb
        
        Write-Status "Creating default days..." "Info"
        $initScript = @'
from data.models import Day

days_data = [
    {"name": "จันทร์", "name_eng": "Monday"},
    {"name": "อังคาร", "name_eng": "Tuesday"},
    {"name": "พุธ", "name_eng": "Wednesday"},
    {"name": "พฤหัสบดี", "name_eng": "Thursday"},
    {"name": "ศุกร์", "name_eng": "Friday"},
    {"name": "เสาร์", "name_eng": "Saturday"},
    {"name": "อาทิตย์", "name_eng": "Sunday"},
]

for day_data in days_data:
    Day.objects.get_or_create(**day_data)

print("Database initialized successfully")
'@
        
        $initScript | & $pythonExe manage.py shell
        
        Write-Status "Database initialized successfully" "Success"
        return $true
    }
    catch {
        Write-Status "Failed to initialize database: $_" "Error"
        return $false
    }
}

# Main installation flow
function Main {
    Write-Status "Starting deployment..." "Info"
    Write-Host ""
    
    # Check administrator privileges
    Test-Administrator
    
    # Find Python
    $pythonExe = Find-Python
    if (-not $pythonExe) {
        Write-Status "Python not found in common locations" "Error"
        Write-Status "Searching PATH environment variable..." "Info"
        
        # Try to find Python in PATH directories
        $pathDirs = $env:PATH -split ';'
        foreach ($dir in $pathDirs) {
            $py = Join-Path $dir "python.exe"
            if (Test-Path $py) {
                # Test if it's not the Windows Store stub
                try {
                    $version = & $py --version 2>&1
                    if ($version -notmatch "not found" -and $version -notmatch "Microsoft Store") {
                        Write-Status "Found Python in PATH: $py" "Success"
                        $pythonExe = $py
                        break
                    }
                } catch {
                    # Skip this path, it's not a real Python
                }
            }
        }
    }
    
    if (-not $pythonExe) {
        Write-Status "Python not found anywhere!" "Error"
        Write-Status "Please install Python 3.10+ from: https://www.python.org/" "Error"
        Write-Status "Make sure to check 'Add Python to PATH' during installation" "Error"
        exit 1
    }
    
    # Verify Python version
    Write-Status "Verifying Python installation..." "Info"
    try {
        $versionOutput = & $pythonExe --version 2>&1
        
        # Check if output looks valid
        if ($versionOutput -match "^Python") {
            Write-Status "Python version: $versionOutput" "Success"
        } else {
            Write-Status "Warning: Could not verify Python version, but found executable" "Warning"
        }
    }
    catch {
        Write-Status "Error: Python executable not working: $_" "Error"
        exit 1
    }
    
    # Create installation directory
    if (-not (Test-Path $InstallPath)) {
        Write-Status "Creating installation directory..." "Info"
        New-Item -ItemType Directory -Path $InstallPath | Out-Null
    }
    
    # Copy project files (if running from source directory)
    if ($scriptPath -ne $InstallPath) {
        Write-Status "Copying project files to $InstallPath..." "Info"
        
        # Read .gitignore patterns
        $gitignorePath = Join-Path $scriptPath ".gitignore"
        $ignorePatterns = @()
        
        if (Test-Path $gitignorePath) {
            $ignorePatterns = @(Get-Content $gitignorePath | Where-Object {
                $_ -and $_ -notmatch "^#" -and $_ -notmatch "^\s*$"
            })
            Write-Status "Loaded $($ignorePatterns.Count) patterns from .gitignore" "Info"
        }
        
        # Use Robocopy for faster file copying with exclusions
        $excludeDirs = @()
        $excludeFiles = @()
        
        # Parse .gitignore patterns for Robocopy
        foreach ($pattern in $ignorePatterns) {
            $pattern = $pattern.Trim()
            
            if ($pattern.EndsWith('/')) {
                # Directory pattern
                $dirname = $pattern.TrimEnd('/')
                if ($dirname -notmatch '\*') {
                    $excludeDirs += $dirname
                }
            } elseif ($pattern -match '^\*\.') {
                # File extension pattern like *.pyc
                $excludeFiles += $pattern
            } elseif ($pattern -notmatch '/' -and $pattern -notmatch '\*') {
                # Specific filename or directory
                $excludeDirs += $pattern
                $excludeFiles += $pattern
            }
        }
        
        # Add common exclusions
        $excludeDirs += "\.git", "\.venv", "__pycache__", "logs"
        
        # Build Robocopy command
        $xcopyArgs = @(
            "/E",           # Copy subdirectories including empty ones
            "/I",           # If destination doesn't exist, create it
            "/Y",           # Overwrite without prompting
            "/EXCLUDE:$($excludeFiles -join ';')" # Exclude file patterns
        )
        
        # Add directory exclusions
        foreach ($dir in $excludeDirs) {
            $xcopyArgs += "/EXCLUDE:$dir"
        }
        
        try {
            Write-Progress -Activity "Copying files" -Status "Using robocopy for fast copy..." -PercentComplete 50
            
            # Use Robocopy which is faster and better for large directory structures
            & robocopy $scriptPath $InstallPath /E /I /Y /XF "*.pyc" /XD "__pycache__" ".venv" ".git" "logs" "db.sqlite3" | Out-Null
            
            # Copy .env file separately (it's in .gitignore so robocopy excludes it)
            $envFile = Join-Path $scriptPath ".env"
            if (Test-Path $envFile) {
                Write-Status "Copying .env file..." "Info"
                Copy-Item -Path $envFile -Destination (Join-Path $InstallPath ".env") -Force -ErrorAction SilentlyContinue
                Write-Status ".env file copied" "Success"
            } else {
                Write-Status "Warning: .env file not found in source directory" "Warning"
            }
            
            Write-Progress -Activity "Copying files" -Completed
            Write-Status "Project files copied successfully" "Success"
        }
        catch {
            Write-Status "Note: Robocopy not available, using standard copy..." "Warning"
            try {
                & xcopy "$scriptPath" "$InstallPath" /E /I /Y /EXCLUDE:".venv;__pycache__;.git;logs;db.sqlite3" | Out-Null
                Write-Status "Project files copied successfully" "Success"
            }
            catch {
                Write-Status "Could not copy files: $_" "Error"
                return $false
            }
        }
    }
    
    # Create virtual environment
    $venvPath = Join-Path $InstallPath ".venv"
    
    # Remove old .venv if it was copied (venv is not portable)
    if (Test-Path $venvPath) {
        Write-Status "Removing non-portable virtual environment from copy..." "Info"
        Remove-Item -Path $venvPath -Recurse -Force -ErrorAction SilentlyContinue
    }
    
    if (-not (Create-VirtualEnvironment $pythonExe $venvPath)) {
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
    Write-Host "Note: WiFi and AP mode features are not supported on Windows." -ForegroundColor Yellow
    Write-Host "Core scheduling and audio playback features will work normally." -ForegroundColor Yellow
}

# Run main installation
Main
