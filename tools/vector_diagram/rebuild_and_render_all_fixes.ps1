# rebuild_and_render_all_fixes.ps1
$ErrorActionPreference = "Stop"

$MSVC_ENV = "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
$VCPKG_INC = "C:\Users\pater\Pyt\Chronon3d\vcpkg_installed\win-release\x64-windows\include"
$VCPKG_LIB = "C:\Users\pater\Pyt\Chronon3d\vcpkg_installed\win-release\x64-windows\lib"
$VCPKG_BIN = "C:\Users\pater\Pyt\Chronon3d\vcpkg_installed\win-release\x64-windows\bin"

$SRC_DIR = "C:\Users\pater\Pyt\ChrononTemplate\tools\vector_diagram"
$INC_DIR = "C:\Users\pater\Pyt\ChrononTemplate\include"
$OUT_DIR = "C:\Users\pater\Pyt\ChrononTemplate\out\svg_parity"

$env:PATH = "$VCPKG_BIN;$env:PATH"

$batchContent = @"
@echo off
call "$MSVC_ENV"

echo === 1. Compiling Showcase 2 (Primitives, Pivot, Inner Glow, Radial Sun, Mountain) ===
cl.exe /nologo /std:c++17 /EHsc /O2 /I"$VCPKG_INC" "$SRC_DIR\render_primitives_scaling_showcase_blend2d.cpp" /Fe:"$SRC_DIR\render_primitives_scaling_showcase_blend2d.exe" /link /LIBPATH:"$VCPKG_LIB" blend2d.lib
if errorlevel 1 exit /b 1

echo === 2. Rendering Showcase 2 Frames ===
"$SRC_DIR\render_primitives_scaling_showcase_blend2d.exe" "$OUT_DIR\showcase_frames"
if errorlevel 1 exit /b 1

echo === 3. Compiling Showcase 1 (Node Graph & Transparent Icons) ===
cl.exe /nologo /std:c++17 /EHsc /O2 /I"$VCPKG_INC" "$SRC_DIR\render_icon_constellation_blend2d.cpp" /Fe:"$SRC_DIR\render_icon_constellation_blend2d.exe" /link /LIBPATH:"$VCPKG_LIB" blend2d.lib
if errorlevel 1 exit /b 1

echo === 4. Rendering Showcase 1 Frames ===
"$SRC_DIR\render_icon_constellation_blend2d.exe"
if errorlevel 1 exit /b 1
"@

$batchFile = "$SRC_DIR\run_all_fixes.cmd"
[System.IO.File]::WriteAllText($batchFile, $batchContent)

cmd.exe /c $batchFile

Write-Host "=== 5. Encoding Primitives Showcase Video (primitives_scaling_showcase.mp4) ===" -ForegroundColor Cyan
& ffmpeg.exe -y -framerate 60 -i "$OUT_DIR\showcase_frames\frame_%04d.png" -c:v libx264 -pix_fmt yuv420p -crf 17 -movflags +faststart "$OUT_DIR\primitives_scaling_showcase.mp4"

Write-Host "=== 6. Encoding Icon Constellation Video (icon_constellation_25d.mp4) ===" -ForegroundColor Cyan
& ffmpeg.exe -y -framerate 60 -i "$OUT_DIR\icon_constellation_frames\frame_%04d.png" -c:v libx264 -pix_fmt yuv420p -crf 17 -movflags +faststart "$OUT_DIR\icon_constellation_25d.mp4"

Write-Host "=== 7. Verifying Deliverables (ffprobe) ===" -ForegroundColor Green
& ffprobe.exe -v error -show_entries format=duration,size,bit_rate -show_entries stream=width,height,r_frame_rate,nb_frames -of default=noprint_wrappers=1 "$OUT_DIR\primitives_scaling_showcase.mp4"
& ffprobe.exe -v error -show_entries format=duration,size,bit_rate -show_entries stream=width,height,r_frame_rate,nb_frames -of default=noprint_wrappers=1 "$OUT_DIR\icon_constellation_25d.mp4"

Write-Host "All fixes compiled, rendered, and encoded successfully!" -ForegroundColor Green
