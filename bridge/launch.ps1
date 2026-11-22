# Launch ROBO Pro Coding with the DevTools bridge enabled.
#
# Two gotchas this script handles:
#   1. `ELECTRON_RUN_AS_NODE=1` on the machine makes the .exe behave like node,
#      so every argument is parsed as a JS entry point and the app dies instantly.
#   2. The app has a single-instance lock; a dedicated `--user-data-dir` keeps the
#      bridge instance independent from the one you use by hand.
#
# Usage:
#   .\launch.ps1                     # port 9334, profile in %TEMP%\ftg-bridge
#   .\launch.ps1 -Port 9335
#   .\launch.ps1 -Profile C:\tmp\prof -Port 9334
param(
    [int]$Port = 9334,
    [string]$Profile = "",
    [string]$AppExe = ""
)

$ErrorActionPreference = "Stop"

function Find-AppExe {
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\ROBOProCoding-zh\app\ROBO Pro Coding.exe",
        "$env:LOCALAPPDATA\Programs\ROBO Pro Coding\ROBO Pro Coding.exe",
        "$env:ProgramFiles\ROBO Pro Coding\ROBO Pro Coding.exe",
        "${env:ProgramFiles(x86)}\ROBO Pro Coding\ROBO Pro Coding.exe"
    )
    foreach ($path in $candidates) {
        if (Test-Path $path) { return $path }
    }
    throw "ROBO Pro Coding not found. Pass -AppExe 'C:\path\to\ROBO Pro Coding.exe'."
}

if (-not $AppExe) { $AppExe = Find-AppExe }
if (-not $Profile) { $Profile = Join-Path $env:TEMP "ftg-bridge" }
New-Item -ItemType Directory -Force -Path $Profile | Out-Null

Write-Host "app     : $AppExe"
Write-Host "profile : $Profile"
Write-Host "port    : $Port"

# cmd clears ELECTRON_RUN_AS_NODE for the child process only.
$command = 'set ELECTRON_RUN_AS_NODE=&& start "" "' + $AppExe + '" --user-data-dir="' + $Profile + '" --remote-debugging-port=' + $Port
cmd /c $command

$deadline = (Get-Date).AddSeconds(30)
while ((Get-Date) -lt $deadline) {
    try {
        $version = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/json/version" -TimeoutSec 2
        Write-Host "bridge ready: $($version.Browser)"
        Write-Host "targets     : http://127.0.0.1:$Port/json/list"
        exit 0
    } catch {
        Start-Sleep -Milliseconds 700
    }
}

throw "bridge did not come up on port $Port (check the app window for errors)"
