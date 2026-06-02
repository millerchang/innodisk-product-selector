# serve.ps1
# Copies latest spec_matrix.json and launches the web app using Python's built-in HTTP server.
# Open http://localhost:3000/standalone.html in your browser.

$python = "C:\Users\miller_chang\AppData\Local\Programs\Python\Python311\python.exe"
if (-not (Test-Path $python)) {
    $python = (Get-Command python -ErrorAction SilentlyContinue)?.Source
}
if (-not $python) { Write-Host "[ERROR] Python not found." -ForegroundColor Red; exit 1 }

# Refresh data
& powershell -File "$PSScriptRoot\copy_data.ps1"

# Launch server
$url = "http://localhost:3000/standalone.html"
Write-Host ""
Write-Host "  Starting Innodisk Product Selector..." -ForegroundColor Cyan
Write-Host "  Open: $url" -ForegroundColor Green
Write-Host "  Press Ctrl+C to stop." -ForegroundColor Gray
Write-Host ""

Start-Process $url  # auto-open in browser

Set-Location $PSScriptRoot
& $python -m http.server 3000
