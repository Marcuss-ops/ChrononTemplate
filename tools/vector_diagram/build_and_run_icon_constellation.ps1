# build_and_run_icon_constellation.ps1
$ErrorActionPreference = "Stop"

$MSVC_ENV = "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
$VCPKG_INC = "C:\Users\pater\Pyt\Chronon3d\vcpkg_installed\win-release\x64-windows\include"
$VCPKG_LIB = "C:\Users\pater\Pyt\Chronon3d\vcpkg_installed\win-release\x64-windows\lib"
$VCPKG_BIN = "C:\Users\pater\Pyt\Chronon3d\vcpkg_installed\win-release\x64-windows\bin"

$SRC_DIR = "C:\Users\pater\Pyt\ChrononTemplate\tools\vector_diagram"
$OUT_DIR = "C:\Users\pater\Pyt\ChrononTemplate\out\svg_parity"

if (-not (Test-Path $OUT_DIR)) {
    New-Item -ItemType Directory -Force -Path $OUT_DIR | Out-Null
}

$env:PATH = "$VCPKG_BIN;$env:PATH"

Write-Host "=== 1. Compiling & Running Icon Constellation Plan Emitter ===" -ForegroundColor Cyan
$cmd_emit = @"
call "$MSVC_ENV"
cl.exe /nologo /std:c++17 /EHsc /O2 "$SRC_DIR\emit_icon_constellation_plan.cpp" /Fe:"$SRC_DIR\emit_icon_constellation_plan.exe"
"$SRC_DIR\emit_icon_constellation_plan.exe"
"@
$cmd_emit | cmd.exe

Write-Host "=== 2. Compiling 2.5D Icon Constellation Blend2D Renderer ===" -ForegroundColor Cyan
$cmd_render = @"
call "$MSVC_ENV"
cl.exe /nologo /std:c++17 /EHsc /O2 /I"$VCPKG_INC" "$SRC_DIR\render_icon_constellation_blend2d.cpp" /Fe:"$SRC_DIR\render_icon_constellation_blend2d.exe" /link /LIBPATH:"$VCPKG_LIB" blend2d.lib
"@
$cmd_render | cmd.exe

Write-Host "=== 3. Rendering 360 Frames (60 FPS) with Blend2D ===" -ForegroundColor Cyan
& "$SRC_DIR\render_icon_constellation_blend2d.exe"

Write-Host "=== 4. Encoding H.264 MP4 with FFmpeg ===" -ForegroundColor Cyan
$FRAMES_PATTERN = "$OUT_DIR\icon_constellation_frames\frame_%04d.png"
$MP4_PATH = "$OUT_DIR\icon_constellation_25d.mp4"

& ffmpeg.exe -y -framerate 60 -i $FRAMES_PATTERN -c:v libx264 -pix_fmt yuv420p -crf 17 -movflags +faststart $MP4_PATH

Write-Host "=== 5. Video Inspection (ffprobe) ===" -ForegroundColor Green
& ffprobe.exe -v error -show_entries format=duration,size,bit_rate -show_entries stream=width,height,r_frame_rate,nb_frames -of default=noprint_wrappers=1 $MP4_PATH

Write-Host "Icon Constellation animation rendered successfully!" -ForegroundColor Green
