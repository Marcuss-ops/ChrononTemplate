# ChrononTemplate: Build and Render Retro Stat Fast Intro
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $RepoRoot

Write-Host "== Step 1: Compiling C++ test & emitter targets in WSL ==" -ForegroundColor Cyan
wsl cmake --build /mnt/c/Users/pater/Pyt/ChrononTemplate/build/codex-web --target chronontemplate_fast_intro_pack_test chronontemplate_emit_retro_stat_fast_intro -j4
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n== Step 2: Executing C++ Fast Intro unit tests ==" -ForegroundColor Cyan
wsl /mnt/c/Users/pater/Pyt/ChrononTemplate/build/codex-web/chronontemplate_fast_intro_pack_test
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n== Step 3: Emitting Chronon Render Plan ==" -ForegroundColor Cyan
wsl /mnt/c/Users/pater/Pyt/ChrononTemplate/build/codex-web/chronontemplate_emit_retro_stat_fast_intro /mnt/c/Users/pater/Pyt/ChrononTemplate/artifacts/retro_stat_fast_intro
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n== Step 4: Rendering High-Fidelity MP4 Video & Contact Sheet ==" -ForegroundColor Cyan
python tools/fast_intro/render_retro_stat_fast_intro.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n[SUCCESS] Completed full C++ build, test, emission, and high-fidelity video rendering!" -ForegroundColor Green
