param(
  [switch]$SkipNpmInstall,
  [switch]$SkipMarketplace,
  [switch]$SkipReset,
  [switch]$SkipLaunch,
  [switch]$InstallAutostart
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$PluginScript = Join-Path $RepoRoot "plugins/codex-tomogatchi/scripts/tomogatchi.py"

function Invoke-Python {
  param([string[]]$Arguments)
  if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 @Arguments
    return
  }
  if (Get-Command python3 -ErrorAction SilentlyContinue) {
    & python3 @Arguments
    return
  }
  if (Get-Command python -ErrorAction SilentlyContinue) {
    & python @Arguments
    return
  }
  throw "Python 3 was not found. Install Python 3 and rerun setup."
}

function Invoke-Optional {
  param(
    [scriptblock]$Command,
    [string]$Warning
  )
  try {
    & $Command
  } catch {
    Write-Warning "$Warning $($_.Exception.Message)"
  }
}

Write-Host "Codex Tomogatchi setup"
Write-Host "Repo: $RepoRoot"

if (-not (Test-Path $PluginScript)) {
  throw "Tomogatchi CLI not found at $PluginScript"
}

Push-Location $RepoRoot
try {
  if (-not $SkipNpmInstall) {
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
      throw "npm was not found. Install Node.js LTS and rerun setup."
    }
    npm install
  }

  Invoke-Python @($PluginScript, "settings", "--init")
  Invoke-Python @($PluginScript, "install")

  if (-not $SkipReset) {
    Invoke-Python @($PluginScript, "reset", "--confirm", "--from-now")
  }

  if (-not $SkipMarketplace -and (Get-Command codex -ErrorAction SilentlyContinue)) {
    Invoke-Optional -Warning "Could not register the local Codex plugin marketplace:" -Command {
      codex plugin marketplace add "$RepoRoot"
    }
  }

  if (-not $SkipLaunch) {
    $Launcher = Join-Path $PSScriptRoot "start-overlay.ps1"
    Start-Process `
      -FilePath "powershell.exe" `
      -ArgumentList "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$Launcher`"" `
      -WorkingDirectory $RepoRoot `
      -WindowStyle Hidden
  }

  if ($InstallAutostart) {
    & (Join-Path $PSScriptRoot "install-autostart.ps1")
  }
} finally {
  Pop-Location
}

Write-Host "Setup complete."
Invoke-Python @($PluginScript, "settings")
