# Build and run all SVG Parity Animations in native C++/Blend2D and encode to MP4
$ErrorActionPreference = "Stop"

$root = "C:\Users\pater\Pyt"
$inc = "$root\Chronon3d\vcpkg_installed\win-release\x64-windows\include"
$lib = "$root\Chronon3d\vcpkg_installed\win-release\x64-windows\lib"
$bin = "$root\Chronon3d\vcpkg_installed\win-release\x64-windows\bin"
$env:PATH = "$bin;" + $env:PATH
$cl = "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"

$toolsDir = "$root\ChrononTemplate\tools\vector_diagram"
$outDir = "$root\ChrononTemplate\out\svg_parity"
New-Item -ItemType Directory -Force -Path "$outDir\anim1_frames" | Out-Null
New-Item -ItemType Directory -Force -Path "$outDir\anim2_frames" | Out-Null

Write-Host "=== 1. Compiling Animation 1 (Van -> Thermo -> Mountain) ===" -ForegroundColor Cyan
$a1Src = "$toolsDir\render_anim1_van_mountain_blend2d.cpp"
$a1Exe = "$toolsDir\render_anim1_van_mountain_blend2d.exe"
cmd /c "call `"$cl`" && cl /std:c++17 /EHsc /O2 /I `"$inc`" `"$a1Src`" /link /LIBPATH:`"$lib`" blend2d.lib /out:`"$a1Exe`""
if ($LASTEXITCODE -eq 0) {
    Write-Host ">>> Running Animation 1 Renderer..." -ForegroundColor Green
    & $a1Exe "$outDir\anim1_frames"
    Write-Host ">>> Encoding Animation 1 to MP4..." -ForegroundColor Yellow
    ffmpeg -y -framerate 30 -i "$outDir\anim1_frames\frame_%04d.png" -c:v libx264 -pix_fmt yuv420p "$outDir\animation_1_van_mountain.mp4"
}

Write-Host "`n=== 2. Compiling Animation 2 (2.5D Neon Essay Dolly Out) ===" -ForegroundColor Cyan
$a2Src = "$toolsDir\render_anim2_neon_essay_blend2d.cpp"
$a2Exe = "$toolsDir\render_anim2_neon_essay_blend2d.exe"
cmd /c "call `"$cl`" && cl /std:c++17 /EHsc /O2 /I `"$inc`" `"$a2Src`" /link /LIBPATH:`"$lib`" blend2d.lib /out:`"$a2Exe`""
if ($LASTEXITCODE -eq 0) {
    Write-Host ">>> Running Animation 2 Renderer..." -ForegroundColor Green
    & $a2Exe "$outDir\anim2_frames"
    Write-Host ">>> Encoding Animation 2 to MP4..." -ForegroundColor Yellow
    ffmpeg -y -framerate 30 -i "$outDir\anim2_frames\frame_%04d.png" -c:v libx264 -pix_fmt yuv420p "$outDir\animation_2_neon_essay_25d.mp4"
}

Write-Host "`nAll animations successfully rendered and encoded!" -ForegroundColor Green
