$env:OLLAMA_LLM_LIBRARY = "cpu"
$env:OLLAMA_NUM_THREADS = "8"
$env:OLLAMA_MAX_LOADED_MODELS = "1"
$env:CUDA_VISIBLE_DEVICES = ""
$env:OLLAMA_NUM_GPU = "0"
$env:OLLAMA_HOST = "127.0.0.1:11434"

$ollamaExe = if ($env:OLLAMA_EXE) { $env:OLLAMA_EXE }
             elseif (Get-Command ollama -ErrorAction SilentlyContinue) { (Get-Command ollama).Source }
             else { Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe" }

Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))
& $ollamaExe serve
