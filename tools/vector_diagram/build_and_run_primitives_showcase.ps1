# Build and run the Primitives Scaling & Parity Showcase in ChrononTemplate
$ErrorActionPreference = "Stop"

$root = "C:\Users\pater\Pyt"
$inc = "$root\Chronon3d\vcpkg_installed\win-release\x64-windows\include"
$lib = "$root\Chronon3d\vcpkg_installed\win-release\x64-windows\lib"
$bin = "$root\Chronon3d\vcpkg_installed\win-release\x64-windows\bin"
$env:PATH = "$bin;" + $env:PATH
$cl = "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"

$toolsDir = "$root\ChrononTemplate\tools\vector_diagram"
$outDir = "$root\ChrononTemplate\out\svg_parity"
$framesDir = "$outDir\showcase_frames"
New-Item -ItemType Directory -Force -Path $framesDir | Out-Null

Write-Host "=== 1. Compiling Showcase Plan Emitter ===" -ForegroundColor Cyan
$emitterSrc = "$toolsDir\emit_primitives_scaling_showcase_plan.cpp"
$emitterExe = "$toolsDir\emit_primitives_scaling_showcase_plan.exe"
cmd /c "call `"$cl`" && cl /std:c++17 /EHsc /O2 /I `"$inc`" `"$emitterSrc`" /Fe:`"$emitterExe`""
if ($LASTEXITCODE -eq 0) {
    Write-Host ">>> Running Showcase Plan Emitter..." -ForegroundColor Green
    & $emitterExe $outDir
}

Write-Host "`n=== 2. Compiling Blend2D Showcase Renderer ===" -ForegroundColor Cyan
$renderSrc = "$toolsDir\render_primitives_scaling_showcase_blend2d.cpp"
$renderExe = "$toolsDir\render_primitives_scaling_showcase_blend2d.exe"
cmd /c "call `"$cl`" && cl /std:c++17 /EHsc /O2 /I `"$inc`" `"$renderSrc`" /link /LIBPATH:`"$lib`" blend2d.lib /out:`"$renderExe`""
if ($LASTEXITCODE -eq 0) {
    Write-Host ">>> Running Blend2D Showcase Renderer (360 frames @ 60fps)..." -ForegroundColor Green
    & $renderExe $framesDir
    
    Write-Host ">>> Encoding Showcase Video to MP4..." -ForegroundColor Yellow
    ffmpeg -y -framerate 60 -i "$framesDir\frame_%04d.png" -c:v libx264 -pix_fmt yuv420p "$outDir\primitives_scaling_showcase.mp4"
}

Write-Host "`nShowcase build, emission, and rendering completed successfully!" -ForegroundColor Green
