# copy_data.ps1
# Copies spec_matrix.json from the parser output folder into webapp/public/
# Run this before `npm run dev` or `npm run build`

$src = Join-Path $PSScriptRoot "..\output\spec_matrix.json"
$dst = Join-Path $PSScriptRoot "public\spec_matrix.json"

if (-not (Test-Path $src)) {
    Write-Host "[ERROR] Source not found: $src" -ForegroundColor Red
    Write-Host "        Run the parser pipeline first:" -ForegroundColor Yellow
    Write-Host "        python parser\pipeline.py --datasheets <path> --output output" -ForegroundColor Yellow
    exit 1
}

Copy-Item -Path $src -Destination $dst -Force
$size = [math]::Round((Get-Item $dst).Length / 1KB, 1)
Write-Host "[OK] Copied spec_matrix.json → public/ ($size KB)" -ForegroundColor Green
