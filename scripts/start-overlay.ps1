param(
  [switch]$StartMinimized
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
  throw "npm was not found. Install Node.js LTS before starting Codex Tomogatchi."
}

Push-Location $RepoRoot
try {
  if ($StartMinimized) {
    $env:CODEX_TOMOGATCHI_START_MINIMIZED = "1"
  }
  & npm.cmd start
} finally {
  Remove-Item Env:CODEX_TOMOGATCHI_START_MINIMIZED -ErrorAction SilentlyContinue
  Pop-Location
}
