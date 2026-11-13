# Install `webtu` as a command on Windows (PowerShell), in its own virtual
# environment. Run from the project folder:
#   powershell -ExecutionPolicy Bypass -File scripts\install.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\install.ps1 -Uninstall
param([switch]$Uninstall)
$ErrorActionPreference = "Stop"

$Here = Split-Path -Parent $PSScriptRoot
$Prefix = Join-Path $env:LOCALAPPDATA "webetu-resto"
$Bin = Join-Path $Prefix "bin"

if ($Uninstall) {
    Remove-Item -Recurse -Force $Prefix -ErrorAction SilentlyContinue
    Write-Host "webtu désinstallé. Ta configuration (dans %APPDATA%\webetu-resto) est conservée."
    exit 0
}

$python = $null
foreach ($candidate in @("py -3.13", "py -3.12", "py -3.11", "python3", "python")) {
    $parts = $candidate.Split(" ")
    $exe = Get-Command $parts[0] -ErrorAction SilentlyContinue
    if (-not $exe) { continue }
    $extra = $parts[1..($parts.Length - 1)]
    & $parts[0] @extra -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>$null
    if ($LASTEXITCODE -eq 0) { $python = $candidate; break }
}
if (-not $python) {
    throw "Python 3.11 ou plus récent est requis (https://www.python.org/downloads/)."
}

$parts = $python.Split(" ")
$extra = if ($parts.Length -gt 1) { $parts[1..($parts.Length - 1)] } else { @() }
New-Item -ItemType Directory -Force -Path $Prefix, $Bin | Out-Null
& $parts[0] @extra -m venv (Join-Path $Prefix "venv")
$venvPython = Join-Path $Prefix "venv\Scripts\python.exe"

Write-Host "==> Installation des dépendances..."
& $venvPython -m pip install --quiet --upgrade pip
& $venvPython -m pip install --quiet --upgrade $Here

# A small shim so `webtu` works from cmd.exe and PowerShell.
$shim = Join-Path $Bin "webtu.cmd"
Set-Content -Path $shim -Value "@echo off`r`n`"$Prefix\venv\Scripts\webtu.exe`" %*" -Encoding ASCII

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (($userPath -split ";") -notcontains $Bin) {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$Bin", "User")
    Write-Host "==> $Bin ajouté à ton PATH (rouvre le terminal)."
}
Write-Host "Prochaine étape : webtu setup"
