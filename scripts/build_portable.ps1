<#
.SYNOPSIS
    Build the CC-Gen-Ultimate portable single-file executable.
.DESCRIPTION
    Bundles the app into one self-contained exe: build\CC-Gen-Ultimate_<version>_portable.exe
    No installer is produced - the exe runs directly without installation.
    Note: the Explorer context-menu integration is installer-only (it needs registry
    entries), so the portable build does not include ccgen_shell.dll.
.NOTES
    Requirements: Python venv with pyinstaller>=6.17
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Configuration ─────────────────────────────────────────────────────────────

$Entry = "app.py"

# ── Helpers ───────────────────────────────────────────────────────────────────

function Write-Step([string]$Msg) {
    Write-Host ""
    Write-Host ">> $Msg" -ForegroundColor Cyan
}

function Fail([string]$Msg) {
    Write-Host ""
    Write-Host "ERROR: $Msg" -ForegroundColor Red
    exit 1
}

function Format-Elapsed([TimeSpan]$ts) {
    if ($ts.TotalMinutes -ge 1) { return "{0}m {1:D2}s" -f [int]$ts.Minutes, $ts.Seconds }
    return "{0}s" -f [int]$ts.TotalSeconds
}

# ── Working directory ─────────────────────────────────────────────────────────

$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = Split-Path -Parent $ScriptDir
$BuildStart  = Get-Date
Set-Location $ProjectRoot

# ── App metadata ──────────────────────────────────────────────────────────────

. "$ScriptDir\app_meta.ps1"
$Meta         = Get-AppMeta
$AppName      = $Meta.AppName
$Version      = $Meta.Version
$PortableName = "${AppName}_${Version}_portable"
$OutputExe    = "build\${PortableName}.exe"

# ── Virtual environment ───────────────────────────────────────────────────────

Write-Step "Activating virtual environment"

$VenvScripts = @(".venv\Scripts\Activate.ps1", "venv\Scripts\Activate.ps1")
$VenvFound   = $false
foreach ($v in $VenvScripts) {
    if (Test-Path $v) {
        . $v
        $VenvFound = $true
        Write-Host "   Activated: $v" -ForegroundColor DarkGray
        break
    }
}
if (-not $VenvFound) {
    Write-Host "   No venv found - using system Python" -ForegroundColor Yellow
}

# ── Prerequisites ─────────────────────────────────────────────────────────────

Write-Step "Checking prerequisites"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Fail "python not found in PATH"
}
if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Fail "pyinstaller not found. Install it with: pip install 'pyinstaller>=6.17'"
}

Write-Host "   Python      : $(python --version)"      -ForegroundColor DarkGray
Write-Host "   PyInstaller : $(pyinstaller --version)" -ForegroundColor DarkGray

# ── Clean ─────────────────────────────────────────────────────────────────────

Write-Step "Cleaning previous build artifacts"

foreach ($path in @("build\pyinstaller", "${PortableName}.spec", $OutputExe)) {
    if (Test-Path $path) {
        Remove-Item $path -Recurse -Force
        Write-Host "   Removed $path" -ForegroundColor DarkGray
    }
}

New-Item -ItemType Directory -Path "build" -Force | Out-Null

# ── PyInstaller ───────────────────────────────────────────────────────────────

Write-Step "Running PyInstaller  (this may take several minutes)"

$PyArgs = @(
    "--name",      $PortableName,
    "--windowed",
    "--onefile",
    "--icon",      "ccgen\assets\icons\CCGenUltimate.ico",
    "--add-data",  "$ProjectRoot\ccgen\qml;ccgen\qml",
    "--add-data",  "$ProjectRoot\ccgen\assets;ccgen\assets",
    # Non-code data files these packages read via relative paths at runtime -
    # PyInstaller only traces Python imports, so these need to be listed explicitly.
    "--collect-data", "indic_transliteration",
    "--collect-data", "faster_whisper",
    "--distpath",  "build",
    "--workpath",  "build\pyinstaller",
    "--specpath",  ".",
    "--noconfirm",
    "--clean",
    $Entry
)

pyinstaller @PyArgs

if ($LASTEXITCODE -ne 0) {
    Fail "PyInstaller failed (exit $LASTEXITCODE). Check output above."
}

if (-not (Test-Path $OutputExe)) {
    Fail "Expected portable executable not found: $OutputExe"
}

# ── Done ──────────────────────────────────────────────────────────────────────

$Mb = [math]::Round((Get-Item $OutputExe).Length / 1MB, 1)
Write-Host ""
Write-Host "Build complete in $(Format-Elapsed ((Get-Date) - $BuildStart))." -ForegroundColor Green
Write-Host "Portable  : $OutputExe  ($Mb MB)" -ForegroundColor Green
