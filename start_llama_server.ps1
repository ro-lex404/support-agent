# Finds the first .gguf model in models/ and launches llama-server
$model = Get-ChildItem -Path "models\*.gguf" | Select-Object -First 1

if (-not $model) {
    Write-Host "[Error] No .gguf model found in models/ folder!" -ForegroundColor Red
    Write-Host "Please place your downloaded model file in: $(Resolve-Path 'models')" -ForegroundColor Yellow
    exit 1
}

$server = "bin\llama-server.exe"
if (-not (Test-Path $server)) {
    Write-Host "[Error] $server not found!" -ForegroundColor Red
    Write-Host "Please extract the pre-built llama-bXXXX-bin-win-cpu-x64.zip into the 'bin' folder." -ForegroundColor Yellow
    exit 1
}

Write-Host "Starting llama-server with model: $($model.Name)" -ForegroundColor Green
Write-Host "Listening on http://localhost:8080/v1 (OpenAI-compatible)" -ForegroundColor Cyan
Write-Host "Direct Mode (Thinking disabled for instant tool calling)" -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop the server." -ForegroundColor Gray

& $server -m $model.FullName -c 2048 -t 2 -np 1 --reasoning off --port 8080
