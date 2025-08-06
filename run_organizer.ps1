# STL Auto Organizer - PowerShell Script
# This script provides easy execution of the file organizer

param(
    [string]$Directory = "",
    [switch]$DryRun = $false,
    [switch]$Live = $false,
    [switch]$Help = $false
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "     STL Auto Organizer for Manyfold" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Python not found"
    }
    Write-Host "Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.7+ and try again" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Starting organizer..." -ForegroundColor Green
Write-Host ""

# Build command arguments
$arguments = @()

if ($Help) {
    $arguments += "--help"
} elseif ($Directory -ne "") {
    $arguments += "--directory", "`"$Directory`""
    if ($DryRun -or -not $Live) {
        $arguments += "--dry-run"
        Write-Host "Running in DRY-RUN mode on directory: $Directory" -ForegroundColor Yellow
    } else {
        Write-Host "Running in LIVE mode on directory: $Directory" -ForegroundColor Red
    }
} else {
    if ($Live) {
        Write-Host "Running in LIVE mode on current directory" -ForegroundColor Red
    } else {
        $arguments += "--dry-run"
        Write-Host "Running in DRY-RUN mode on current directory" -ForegroundColor Yellow
        Write-Host "To apply changes, use -Live parameter" -ForegroundColor Yellow
    }
}

Write-Host ""

# Execute the Python script
try {
    if ($arguments.Count -gt 0) {
        & python file_organizer.py @arguments
    } else {
        & python file_organizer.py
    }
} catch {
    Write-Host "Error executing script: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Operation completed." -ForegroundColor Green
Read-Host "Press Enter to exit"
