[CmdletBinding()]
param(
    [string]$JobId = "e2e-001",
    [string]$Mode = "canned",
    [string]$OutputVideo = "",
    [string]$Gender = "female"
)

$ErrorActionPreference = "Continue"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$py = $env:VIDEO_FACTORY_PYTHON
if (-not $py) {
    $venvPy = Join-Path $root ".venv\Scripts\python.exe"
    if (Test-Path $venvPy) { $py = $venvPy } else { $py = "python" }
}
if (-not $OutputVideo) { $OutputVideo = Join-Path $root "data\renders\$JobId.mp4" }
$jobDir = Join-Path $root "data\jobs\$JobId"
$logDir = Join-Path $root "data\logs"

New-Item -ItemType Directory -Force -Path $jobDir | Out-Null
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$global:startTime = Get-Date
$results = @{}

function Log-Step {
    param($name, $status, $duration, $details = "")
    $entry = @{
        step = $name
        status = $status
        duration_sec = $duration
        details = $details
        timestamp = (Get-Date).ToString("o")
    }
    Write-Host "[$status] $name en $([math]::Round($duration, 1))s" -ForegroundColor $(if($status -eq "PASS"){"Green"}else{"Red"})
    return $entry
}

function Run-Step {
    param($name, $scriptBlock)
    Write-Host "`n=== $name ===" -ForegroundColor Cyan
    $sw = [Diagnostics.Stopwatch]::StartNew()
    try {
        & $scriptBlock
        $sw.Stop()
        $results[$name] = Log-Step $name "PASS" $sw.Elapsed.TotalSeconds
    } catch {
        $sw.Stop()
        $results[$name] = Log-Step $name "FAIL" $sw.Elapsed.TotalSeconds $_.ToString()
        Write-Host "ERROR: $_" -ForegroundColor Red
    }
}

Run-Step "1. RAG Ingest Demo Doc" {
    & $py "$root\scripts\rag_ingest.py" "$root\data\documents\demo_quiro.doc.md" --category quiromancia
}

Run-Step "2. RAG Query Test" {
    & $py "$root\scripts\rag_query.py" "línea del corazón marcada" --top-k 3
}

Run-Step "3. Generate Script" {
    & $py "$root\scripts\generate_script.py" --mode $Mode --output "$jobDir\script.json"
    if ($LASTEXITCODE -ne 0) { throw "Script generation failed" }
}

Run-Step "4. Build Storyboard" {
    & $py "$root\scripts\build_storyboard.py" --script "$jobDir\script.json" --output-dir $jobDir
    if ($LASTEXITCODE -ne 0) { throw "Storyboard failed" }
}

Run-Step "5. Generate TTS Audio" {
    & $py "$root\scripts\generate_tts.py" --storyboard "$jobDir\storyboard.json" --engine auto --gender $Gender
    if ($LASTEXITCODE -ne 0) { throw "TTS failed" }
}

Run-Step "6. Generate Images (V8 compositor)" {
    & $py "$root\scripts\v8\compositor.py" --storyboard "$jobDir\storyboard.json" --width 1280 --height 720
    if ($LASTEXITCODE -ne 0) { throw "Images failed" }
}

Run-Step "7. Generate Subtitles" {
    & $py "$root\scripts\generate_subtitles.py" --storyboard "$jobDir\storyboard.json" --voice "$jobDir\voice.json"
    if ($LASTEXITCODE -ne 0) { throw "Subtitles failed" }
}

Run-Step "8. Render Video" {
    & $py "$root\scripts\render_video.py" --manifest "$jobDir\manifest.json" --output $OutputVideo --burn-subtitles
    if ($LASTEXITCODE -ne 0) { throw "Render failed" }
}

Run-Step "9. Validate Video" {
    & $py "$root\scripts\validate_video.py" --video $OutputVideo --job-dir $jobDir
    if ($LASTEXITCODE -ne 0) { throw "Validation failed" }
}

Run-Step "10. Generate Short Version" {
    $shortOutput = $OutputVideo -replace '\.mp4$', '_short.mp4'
    & $py "$root\scripts\generate_short.py" --video $OutputVideo --output $shortOutput
    if ($LASTEXITCODE -ne 0) { throw "Short generation failed" }
}

$totalSec = (Get-Date) - $global:startTime | Select-Object -ExpandProperty TotalSeconds
$passCount = ($results.Values | Where-Object { $_.status -eq "PASS" }).Count
$failCount = ($results.Values | Where-Object { $_.status -eq "FAIL" }).Count

$summary = @{
    job_id = $JobId
    mode = $Mode
    total_duration_sec = $totalSec
    steps_total = $results.Count
    steps_passed = $passCount
    steps_failed = $failCount
    steps = $results
    status = if ($failCount -eq 0) { "PASS" } else { "FAIL" }
    started_at = $global:startTime.ToString("o")
    finished_at = (Get-Date).ToString("o")
}

$summaryPath = "$root\tests\reports\e2e_$JobId.json"
$summaryDir = Split-Path $summaryPath -Parent
if (-not (Test-Path $summaryDir)) { New-Item -ItemType Directory -Path $summaryDir -Force | Out-Null }
$summary | ConvertTo-Json -Depth 8 | Set-Content -Path $summaryPath -Encoding UTF8

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  E2E TEST RESUMEN" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Job ID: $JobId" -ForegroundColor White
Write-Host "  Modo: $Mode" -ForegroundColor White
Write-Host "  Pasos OK: $passCount / $($results.Count)" -ForegroundColor $(if($failCount -eq 0){"Green"}else{"Red"})
Write-Host "  Pasos FAIL: $failCount" -ForegroundColor $(if($failCount -eq 0){"Green"}else{"Red"})
Write-Host "  Tiempo total: $([math]::Round($totalSec, 1))s" -ForegroundColor White
Write-Host "  Status: $($summary.status)" -ForegroundColor $(if($failCount -eq 0){"Green"}else{"Red"})
Write-Host "  Reporte: $summaryPath" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan

if ($failCount -gt 0) { exit 1 } else { exit 0 }
