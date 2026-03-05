$ErrorActionPreference = "Stop"
$NetExecGitUrl = "git+https://github.com/Pennyw0rth/NetExec.git"

function Write-Step([string]$msg) {
    Write-Host "[*] $msg" -ForegroundColor Cyan
}

function Write-Ok([string]$msg) {
    Write-Host "[+] $msg" -ForegroundColor Green
}

function Write-WarnMsg([string]$msg) {
    Write-Host "[!] $msg" -ForegroundColor Yellow
}

Write-Step "Checking Python..."
try {
    python --version | Out-Null
} catch {
    Write-Host "[-] Python not found. Install Python 3 first: https://www.python.org/downloads/windows/" -ForegroundColor Red
    exit 1
}

Write-Step "Upgrading pip..."
python -m pip install --upgrade pip

Write-Step "Installing pipx (if needed)..."
python -m pip install --user pipx

Write-Step "Ensuring pipx path..."
try {
    python -m pipx ensurepath
} catch {
    Write-WarnMsg "pipx ensurepath failed. Continuing with direct path fallback."
}

$pipxExe = Join-Path $env:APPDATA "Python\Scripts\pipx.exe"
$userScripts = (python -c "import os,site; print(os.path.join(os.path.dirname(site.getusersitepackages()), 'Scripts'))").Trim()
$nxcFound = $false

if (Get-Command nxc -ErrorAction SilentlyContinue) {
    $nxcFound = $true
} else {
    Write-Step "Installing NetExec from GitHub using pipx..."
    if (Test-Path $pipxExe) {
        & $pipxExe install $NetExecGitUrl --force
    } else {
        Write-WarnMsg "pipx.exe not found in expected location, fallback to pip --user."
    }
}

if (-not (Get-Command nxc -ErrorAction SilentlyContinue)) {
    Write-Step "Fallback install from GitHub with pip --user..."
    python -m pip install --user $NetExecGitUrl
}

$altScripts = Join-Path $env:APPDATA "Python\Scripts"

if (-not (Get-Command nxc -ErrorAction SilentlyContinue)) {
    Write-WarnMsg "nxc still not found in current session PATH."
    Write-Step "Adding user Scripts path to USER PATH..."
    $currentUserPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($currentUserPath -notlike "*$userScripts*") {
        $newUserPath = if ([string]::IsNullOrEmpty($currentUserPath)) { $userScripts } else { "$currentUserPath;$userScripts" }
        [Environment]::SetEnvironmentVariable("Path", $newUserPath, "User")
        Write-Ok "Added to USER PATH: $userScripts"
    } else {
        Write-Ok "USER PATH already contains: $userScripts"
    }
    if ($env:Path -notlike "*$userScripts*") {
        $env:Path = "$env:Path;$userScripts"
    }
    Write-Host "If command is still not found, open a new terminal."
}

if (-not (Get-Command nxc -ErrorAction SilentlyContinue)) {
    Write-WarnMsg "nxc still not found. You can run directly:"
    Write-Host "  $userScripts\nxc.exe --version"
    Write-Host "Fallback paths:"
    Write-Host "  $altScripts"
}

if (Get-Command nxc -ErrorAction SilentlyContinue) {
    Write-Ok "nxc installed successfully."
    nxc --version
    exit 0
}

Write-Host "[-] Installation finished but nxc is still unavailable in this terminal." -ForegroundColor Red
Write-Host "Try opening a new terminal and run: nxc --version"
exit 1
