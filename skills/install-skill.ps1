# Install the bundled skill into an agent's global skill directory.
#
#   .\skills\install-skill.ps1                 # -> %USERPROFILE%\.claude\skills
#   .\skills\install-skill.ps1 -Dest D:\skills
#   .\skills\install-skill.ps1 -Project        # -> .\.claude\skills (this repo only)
param(
    [string]$Dest = "",
    [switch]$Project
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$skill = Join-Path $here "fischertechnik-ft"

if (-not (Test-Path (Join-Path $skill "SKILL.md"))) {
    throw "skill not found at $skill"
}

if ($Project) {
    $Dest = Join-Path (Get-Location) ".claude\skills"
}
if (-not $Dest) {
    $Dest = Join-Path $env:USERPROFILE ".claude\skills"
}

New-Item -ItemType Directory -Force -Path $Dest | Out-Null
$target = Join-Path $Dest "fischertechnik-ft"
if (Test-Path $target) { Remove-Item $target -Recurse -Force }
Copy-Item $skill $target -Recurse -Force

Write-Host "installed fischertechnik-ft -> $target"
Write-Host "restart or reload your agent so the skill catalog picks it up."
Get-ChildItem $target | Select-Object Name | Format-Table -AutoSize
