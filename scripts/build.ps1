$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$env:UV_CACHE_DIR = Join-Path $ProjectRoot ".uv-cache"

uv run pyinstaller `
    --noconfirm `
    --clean `
    --onefile `
    --console `
    --name md `
    --specpath build `
    --paths src `
    src/md_webdav/__main__.py

Write-Host ""
Write-Host "Build complete: $ProjectRoot\dist\md.exe"

