[CmdletBinding()]
param(
    [string]$OutputFile = ""
)

$ErrorActionPreference = "Continue"

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "   AI VIDEO FACTORY - PREFLIGHT HARDWARE & ENV" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
if (-not $OutputFile) {
    $OutputFile = Join-Path $PSScriptRoot "..\data\logs\preflight_$timestamp.json"
}

$os = Get-CimInstance Win32_OperatingSystem
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$ram = Get-CimInstance Win32_ComputerSystem
$disks = Get-PSDrive -PSProvider FileSystem | Select-Object Name, @{N="Used_GB";E={[math]::round($_.Used/1GB,2)}}, @{N="Free_GB";E={[math]::round($_.Free/1GB,2)}}, Root

# GPU info
$gpuRaw = & nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader,nounits 2>$null
$gpuList = @()
if ($gpuRaw) {
    foreach ($line in $gpuRaw) {
        $parts = $line.Split(',')
        if ($parts.Count -ge 3) {
            $gpuList += @{
                Name = $parts[0].Trim()
                VRAM_MB = [int]$parts[1].Trim()
                DriverVersion = $parts[2].Trim()
            }
        }
    }
}

# Tools checks
$tools = @{}
@('ollama', 'ffmpeg', 'ffprobe', 'python', 'docker', 'git', 'supabase', 'node', 'npx') | ForEach-Object {
    $cmd = Get-Command $_ -ErrorAction SilentlyContinue
    $tools[$_] = if ($cmd) { $cmd.Source } else { $null }
}

# Versions
$versions = @{}
if ($tools['ollama']) {
    try {
        $v = Invoke-RestMethod -Uri "http://localhost:11434/api/version" -TimeoutSec 3
        $versions['ollama_api'] = $v.version
    } catch {
        $versions['ollama_api'] = "Offline/Unreachable"
    }
}
if ($tools['ffmpeg']) {
    $v = & ffmpeg -version 2>$null | Select-Object -First 1
    $versions['ffmpeg'] = $v
}
if ($tools['python']) {
    $v = & python --version 2>$null
    $versions['python'] = $v
}
if ($tools['docker']) {
    $v = & docker --version 2>$null
    $versions['docker'] = $v
}

$report = [PSCustomObject]@{
    timestamp = $timestamp
    os = @{
        caption = $os.Caption
        version = $os.Version
        arch = $os.OSArchitecture
    }
    cpu = @{
        name = $cpu.Name
        cores = $cpu.NumberOfCores
        logical_processors = $cpu.NumberOfLogicalProcessors
    }
    ram_gb = [math]::round($ram.TotalPhysicalMemory/1GB, 2)
    gpus = $gpuList
    disks = $disks
    tools = $tools
    versions = $versions
}

$jsonOutput = $report | ConvertTo-Json -Depth 6
$reportDir = Split-Path $OutputFile -Parent
if (-not (Test-Path $reportDir)) {
    New-Item -ItemType Directory -Path $reportDir -Force | Out-Null
}
$jsonOutput | Set-Content -Path $OutputFile -Encoding UTF8

Write-Host "`nPreflight completado con éxito." -ForegroundColor Green
Write-Host "Reporte guardado en: $OutputFile" -ForegroundColor Yellow
$report | Format-List
