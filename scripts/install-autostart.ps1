param(
  [string]$TaskName = "CodexTomogatchiOverlay",
  [switch]$RunNow
)

$ErrorActionPreference = "Stop"

if (-not $IsWindows -and $PSVersionTable.PSEdition -eq "Core") {
  throw "Autostart installation is currently supported on Windows only."
}

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$Launcher = Join-Path $PSScriptRoot "start-overlay.ps1"

if (-not (Test-Path $Launcher)) {
  throw "Launcher script not found: $Launcher"
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
  throw "npm was not found. Install Node.js LTS before installing autostart."
}

$UserId = if ($env:USERDOMAIN) { "$env:USERDOMAIN\$env:USERNAME" } else { $env:USERNAME }
$ActionArguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$Launcher`" -StartMinimized"
$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $ActionArguments -WorkingDirectory $RepoRoot
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $UserId
$Principal = New-ScheduledTaskPrincipal -UserId $UserId -LogonType Interactive -RunLevel LeastPrivilege
$Settings = New-ScheduledTaskSettingsSet `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -MultipleInstances IgnoreNew `
  -StartWhenAvailable

Register-ScheduledTask `
  -TaskName $TaskName `
  -Action $Action `
  -Trigger $Trigger `
  -Principal $Principal `
  -Settings $Settings `
  -Description "Starts the Codex Tomogatchi overlay at user login." `
  -Force | Out-Null

Write-Host "Installed autostart task: $TaskName"
Write-Host "Launches: $Launcher -StartMinimized"

if ($RunNow) {
  Start-ScheduledTask -TaskName $TaskName
  Write-Host "Started autostart task now."
}
