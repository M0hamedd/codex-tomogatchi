param(
  [string]$TaskName = "CodexTomogatchiOverlay"
)

$ErrorActionPreference = "Stop"

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
  Write-Host "Autostart task not found: $TaskName"
  exit 0
}

try {
  Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
} catch {
  # The task may not be running; uninstall should still proceed.
}

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Host "Removed autostart task: $TaskName"
