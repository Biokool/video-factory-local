$env:OLLAMA_LLM_LIBRARY = "cpu"
$env:OLLAMA_NUM_THREADS = "8"
$env:OLLAMA_MAX_LOADED_MODELS = "1"
$env:CUDA_VISIBLE_DEVICES = ""
$env:OLLAMA_NUM_GPU = "0"
$env:OLLAMA_HOST = "127.0.0.1:11434"

Set-Location "F:\__AGENCIA_AIMA\D_OLLAMA_VIDEO"
& "C:\Users\mauri\AppData\Local\Programs\Ollama\ollama.exe" serve
