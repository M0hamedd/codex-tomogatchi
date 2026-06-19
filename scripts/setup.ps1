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
$PythonCommand = $null

function Test-Python3 {
  param(
    [string]$Command,
    [string[]]$Prefix = @()
  )
  try {
    & $Command @Prefix -c "import sys; raise SystemExit(0 if sys.version_info[0] == 3 else 1)" *> $null
    return $LASTEXITCODE -eq 0
  } catch {
    return $false
  }
}

function Get-PythonCommand {
  if ($script:PythonCommand) {
    return $script:PythonCommand
  }

  $Candidates = @()
  if ($env:PYTHON) {
    $Candidates += [pscustomobject]@{ Command = $env:PYTHON; Prefix = @(); Label = '$env:PYTHON' }
  }
  $Candidates += [pscustomobject]@{ Command = "python"; Prefix = @(); Label = "python" }
  $Candidates += [pscustomobject]@{ Command = "python3"; Prefix = @(); Label = "python3" }
  $Candidates += [pscustomobject]@{ Command = "py"; Prefix = @("-3"); Label = "py -3" }

  foreach ($Candidate in $Candidates) {
    if ($Candidate.Label -ne '$env:PYTHON' -and -not (Get-Command $Candidate.Command -ErrorAction SilentlyContinue)) {
      continue
    }
    if (Test-Python3 -Command $Candidate.Command -Prefix $Candidate.Prefix) {
      $script:PythonCommand = $Candidate
      return $script:PythonCommand
    }
  }

  throw "Python 3 was not found. Install Python 3, or set PYTHON to a Python 3 executable, and rerun setup."
}

function Invoke-Python {
  param([string[]]$Arguments)
  $Python = Get-PythonCommand
  $AllArguments = @()
  $AllArguments += $Python.Prefix
  $AllArguments += $Arguments
  & $Python.Command @AllArguments
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

function Assert-NodeTooling {
  if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw "Node.js was not found. Install Node.js 22+ with npm 10+ and rerun setup."
  }
  $NodeRaw = (& node --version).Trim().TrimStart("v")
  $NodeMajor = [int]($NodeRaw.Split(".")[0])
  if ($NodeMajor -lt 22) {
    throw "Node.js 22+ is required. Found Node.js v$NodeRaw. Upgrade Node.js and rerun setup."
  }

  if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm was not found. Install Node.js 22+ with npm 10+ and rerun setup."
  }
  $NpmRaw = (& npm --version).Trim()
  $NpmMajor = [int]($NpmRaw.Split(".")[0])
  if ($NpmMajor -lt 10) {
    throw "npm 10+ is required. Found npm $NpmRaw. Upgrade Node.js/npm and rerun setup."
  }
}

Write-Host "Codex Tomogatchi setup"
Write-Host "Repo: $RepoRoot"

if (-not (Test-Path $PluginScript)) {
  throw "Tomogatchi CLI not found at $PluginScript"
}

Push-Location $RepoRoot
try {
  if (-not $SkipNpmInstall -or -not $SkipLaunch) {
    Assert-NodeTooling
  }

  if (-not $SkipNpmInstall) {
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

Write-Host ""
Write-Host "Setup complete. Running doctor..."
Invoke-Python @($PluginScript, "doctor")
Write-Host ""
if (-not $SkipLaunch) {
  Write-Host "Next: look for the Codex Tomogatchi overlay or tray icon."
} else {
  Write-Host "Next: run npm start from this repo to launch the overlay."
}
