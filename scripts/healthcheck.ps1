[CmdletBinding()]
param()

$ErrorActionPreference = "Continue"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$py = $env:VIDEO_FACTORY_PYTHON
if (-not $py) {
    $venvPy = Join-Path $root ".venv\Scripts\python.exe"
    if (Test-Path $venvPy) { $py = $venvPy } else { $py = "python" }
}
$results = @()

function Test-Service {
    param($name, $scriptBlock)
    $sw = [Diagnostics.Stopwatch]::StartNew()
    try {
        $result = & $scriptBlock
        $sw.Stop()
        $status = if ($result) { "PASS" } else { "FAIL" }
    } catch {
        $sw.Stop()
        $result = $_.ToString()
        $status = "FAIL"
    }
    $script:results += @{
        name = $name
        status = $status
        duration_ms = $sw.ElapsedMilliseconds
        result = $result
    }
    Write-Host "[$status] $name" -ForegroundColor $(if($status -eq "PASS"){"Green"}else{"Red"})
}

Write-Host "=== AI VIDEO FACTORY HEALTHCHECK ===" -ForegroundColor Cyan

Test-Service "Ollama API" {
    try {
        $r = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/version" -TimeoutSec 5
        return $r.version
    } catch { return $null }
}

Test-Service "nomic-embed-text" {
    try {
        $r = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 5
        $models = $r.models | ForEach-Object { $_.name }
        return ($models -join ",") -match "nomic-embed-text"
    } catch { return $null }
}

Test-Service "qwen3.5:4b" {
    try {
        $r = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 5
        $models = $r.models | ForEach-Object { $_.name }
        return ($models -join ",") -match "qwen3.5"
    } catch { return $null }
}

Test-Service "Postgres Docker" {
    $out = & docker ps --filter "name=video-factory-db" --format "{{.Names}}" 2>$null
    return ($out -match "video-factory-db")
}

Test-Service "pgvector extension" {
    $dbUrl = if ($env:SUPABASE_DB_URL) { $env:SUPABASE_DB_URL } else { 'postgresql://postgres:postgres@127.0.0.1:54322/video_factory' }
    $script = @"
import psycopg2, os
try:
    conn = psycopg2.connect(os.environ.get('SUPABASE_DB_URL', '$dbUrl'))
    cur = conn.cursor()
    cur.execute("SELECT extname FROM pg_extension WHERE extname='vector';")
    r = cur.fetchone()
    cur.close()
    conn.close()
    print('OK' if r else 'FAIL')
except Exception as e:
    print(f'FAIL: {e}')
"@
    $scriptPath = Join-Path $env:TEMP "check_pgvector.py"
    Set-Content -Path $scriptPath -Value $script -Encoding UTF8
    & $py $scriptPath 2>$null
    return $LASTEXITCODE -eq 0
}

Test-Service "n8n" {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:5678" -TimeoutSec 5 -UseBasicParsing
        return $r.StatusCode -eq 200
    } catch { return $null }
}

Test-Service "FFmpeg" {
    try {
        $v = & ffmpeg -version 2>$null
        return $v[0]
    } catch { return $null }
}

Test-Service "ffprobe" {
    try {
        $v = & ffprobe -version 2>$null
        return $v[0]
    } catch { return $null }
}

Test-Service "Python venv" {
    try {
        $v = & $py --version
        return $v
    } catch { return $null }
}

Test-Service "psycopg2" {
    try {
        & $py -c "import psycopg2; print(psycopg2.__version__)"
        return $LASTEXITCODE -eq 0
    } catch { return $null }
}

Test-Service "Pillow" {
    try {
        & $py -c "from PIL import Image; print(Image.__version__)"
        return $LASTEXITCODE -eq 0
    } catch { return $null }
}

$passCount = ($results | Where-Object { $_.status -eq "PASS" }).Count
$failCount = ($results | Where-Object { $_.status -eq "FAIL" }).Count
$total = $results.Count

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Healthcheck: $passCount / $total PASS" -ForegroundColor $(if($failCount -eq 0){"Green"}else{"Red"})
if ($failCount -eq 0) {
    Write-Host "  SYSTEM READY" -ForegroundColor Green
} else {
    Write-Host "  $failCount servicios requieren atenciÃ³n" -ForegroundColor Red
}
Write-Host "========================================" -ForegroundColor Cyan

$reportPath = Join-Path $root "data\logs\healthcheck_$(Get-Date -Format 'yyyyMMdd-HHmmss').json"
$reportDir = Split-Path $reportPath -Parent
if (-not (Test-Path $reportDir)) { New-Item -ItemType Directory -Path $reportDir -Force | Out-Null }
@{ timestamp = (Get-Date).ToString("o"); results = $results; pass = $passCount; fail = $failCount } | ConvertTo-Json -Depth 5 | Set-Content -Path $reportPath -Encoding UTF8

if ($failCount -gt 0) { exit 1 } else { exit 0 }
