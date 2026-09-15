# =============================================================================
#  AI VIDEO FACTORY — Arranque rápido de todas las instancias locales
# =============================================================================
#  Levanta, en orden, los servicios que necesita la fábrica local de video:
#
#   1. Docker Desktop          (Postgres + pgvector + n8n)
#   2. Ollama                  (LLM + embeddings, en CPU por bug CUDA)
#   3. VoiceStudio             (TTS natural en GPU, backend en :3900)
#
#  Uso:
#   .\scripts\start_all.ps1              # arranca todo y hace healthcheck
#   .\scripts\start_all.ps1 -NoWait      # arranca todo y sale sin esperar
#   .\scripts\start_all.ps1 -SkipDocker  # omite Docker Desktop
#
#  El script es idempotente: no relanza un servicio que ya está arriba.
# =============================================================================

[CmdletBinding()]
param(
    [switch]$NoWait,
    [switch]$SkipDocker,
    [int]$TimeoutSec = 180
)

$ErrorActionPreference = "Continue"
$root = "F:\__AGENCIA_AIMA\D_OLLAMA_VIDEO"

$ollamaExe    = "C:\Users\mauri\AppData\Local\Programs\Ollama\ollama.exe"
$dockerExe    = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
$vsExe        = "C:\Users\mauri\AppData\Local\VoiceStudio (Current User)\omnivoice-studio.exe"

function Test-Http($url, $sec = 4) {
    try {
        $r = Invoke-WebRequest -Uri $url -TimeoutSec $sec -UseBasicParsing
        return $r.StatusCode -eq 200
    } catch { return $false }
}

function Write-Step($msg) {
    Write-Host "`n==> $msg" -ForegroundColor Cyan
}

Write-Host "======================================================" -ForegroundColor Magenta
Write-Host "  AI VIDEO FACTORY — ARRANQUE RÁPIDO" -ForegroundColor Magenta
Write-Host "======================================================" -ForegroundColor Magenta

# ── 1. Docker Desktop ─────────────────────────────────────────────────────
if (-not $SkipDocker) {
    Write-Step "Docker Desktop"
    if (Test-Http "http://127.0.0.1:5678" 2) {
        Write-Host "   ya está corriendo (n8n responde)." -ForegroundColor Green
    } else {
        if (-not (Test-Path $dockerExe)) {
            Write-Host "   Docker Desktop no encontrado en $dockerExe" -ForegroundColor Yellow
        } else {
            Write-Host "   arrancando Docker Desktop..." -ForegroundColor Yellow
            Start-Process -FilePath $dockerExe
            Write-Host "   esperando a que el daemon esté listo..." -ForegroundColor Yellow
            $deadline = (Get-Date).AddSeconds($TimeoutSec)
            $ready = $false
            while ((Get-Date) -lt $deadline -and -not $ready) {
                Start-Sleep -Seconds 3
                docker info *> $null
                if ($LASTEXITCODE -eq 0) { $ready = $true }
            }
            if ($ready) {
                Write-Host "   Docker listo." -ForegroundColor Green
                # Levantar el contenedor de Postgres+pgvector si existe en compose
                $compose = "$root\docker-compose.yml"
                if (Test-Path $compose) {
                    Write-Host "   levantando contenedores (docker compose up -d)..." -ForegroundColor Yellow
                    docker compose -f $compose up -d 2>&1 | Out-Null
                }
            } else {
                Write-Host "   Docker no quedó listo en ${TimeoutSec}s." -ForegroundColor Red
            }
        }
    }
} else {
    Write-Step "Docker Desktop (omitido con -SkipDocker)"
}

# ── 2. Ollama (CPU) ────────────────────────────────────────────────────────
Write-Step "Ollama (CPU)"
if (Test-Http "http://127.0.0.1:11434/api/version" 3) {
    Write-Host "   ya está corriendo." -ForegroundColor Green
} else {
    if (Test-Path $ollamaExe) {
        $env:OLLAMA_LLM_LIBRARY = "cpu"
        $env:CUDA_VISIBLE_DEVICES = ""
        $env:OLLAMA_HOST = "127.0.0.1:11434"
        Write-Host "   arrancando Ollama en CPU (sin GPU)..." -ForegroundColor Yellow
        Start-Process -FilePath $ollamaExe -ArgumentList "serve" -WindowStyle Hidden
        $deadline = (Get-Date).AddSeconds(60)
        while ((Get-Date) -lt $deadline -and -not (Test-Http "http://127.0.0.1:11434/api/version" 2)) {
            Start-Sleep -Seconds 2
        }
        if (Test-Http "http://127.0.0.1:11434/api/version" 2) {
            Write-Host "   Ollama listo." -ForegroundColor Green
        } else {
            Write-Host "   Ollama no respondió a tiempo." -ForegroundColor Red
        }
    } else {
        Write-Host "   Ollama no encontrado en $ollamaExe" -ForegroundColor Red
    }
}

# ── 3. VoiceStudio (TTS en GPU) ────────────────────────────────────────────
Write-Step "VoiceStudio (TTS)"
if (Test-Http "http://127.0.0.1:3900/.well-known/voicestudio-speech" 3) {
    Write-Host "   ya está corriendo." -ForegroundColor Green
} else {
    if (Test-Path $vsExe) {
        Write-Host "   arrancando VoiceStudio..." -ForegroundColor Yellow
        Start-Process -FilePath $vsExe
        $deadline = (Get-Date).AddSeconds($TimeoutSec)
        while ((Get-Date) -lt $deadline -and -not (Test-Http "http://127.0.0.1:3900/.well-known/voicestudio-speech" 3)) {
            Start-Sleep -Seconds 3
        }
        if (Test-Http "http://127.0.0.1:3900/.well-known/voicestudio-speech" 3) {
            Write-Host "   VoiceStudio listo." -ForegroundColor Green
        } else {
            Write-Host "   VoiceStudio no respondió a tiempo (revisa la ventana de setup)." -ForegroundColor Red
        }
    } else {
        Write-Host "   VoiceStudio no encontrado en $vsExe" -ForegroundColor Red
    }
}

# ── Resumen ────────────────────────────────────────────────────────────────
Write-Host "`n======================================================" -ForegroundColor Magenta
Write-Host "  RESUMEN DE SERVICIOS" -ForegroundColor Magenta
Write-Host "======================================================" -ForegroundColor Magenta
foreach ($svc in @(
    @{ n = "Ollama (LLM/embeddings)"; u = "http://127.0.0.1:11434/api/version" },
    @{ n = "VoiceStudio (TTS)";       u = "http://127.0.0.1:3900/.well-known/voicestudio-speech" },
    @{ n = "n8n (orquestador)";       u = "http://127.0.0.1:5678" }
)) {
    $ok = Test-Http $svc.u 4
    $color = if ($ok) { "Green" } else { "Red" }
    $tag = if ($ok) { "OK " } else { "OFF" }
    Write-Host "   [$tag] $($svc.n)" -ForegroundColor $color
}
Write-Host "======================================================" -ForegroundColor Magenta

if ($NoWait) { exit 0 }
Write-Host "`nServicios arrancados. Ejecuta .\scripts\healthcheck.ps1 para validación completa." -ForegroundColor Yellow
