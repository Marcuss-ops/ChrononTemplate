# build_and_run_direct_svg_morph.ps1
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

echo === 1. Compiling and Running Native C++ SVG Parser Unit Tests ===
cl.exe /nologo /std:c++17 /EHsc /O2 /I"$INC_DIR" /I"$VCPKG_INC" "$SRC_DIR\test_native_svg_parser.cpp" /Fe:"$SRC_DIR\test_native_svg_parser.exe" /link /LIBPATH:"$VCPKG_LIB" blend2d.lib
if errorlevel 1 exit /b 1
"$SRC_DIR\test_native_svg_parser.exe"
if errorlevel 1 exit /b 1

echo === 2. Compiling Native C++ Direct SVG Morph Renderer ===
cl.exe /nologo /std:c++17 /EHsc /O2 /I"$INC_DIR" /I"$VCPKG_INC" "$SRC_DIR\render_svg_direct_morph_blend2d.cpp" /Fe:"$SRC_DIR\render_svg_direct_morph_blend2d.exe" /link /LIBPATH:"$VCPKG_LIB" blend2d.lib
if errorlevel 1 exit /b 1

echo === 3. Running Native C++ Direct SVG Morph Renderer ===
"$SRC_DIR\render_svg_direct_morph_blend2d.exe"
if errorlevel 1 exit /b 1
"@

$batchFile = "$SRC_DIR\compile_and_render_direct_svg.cmd"
[System.IO.File]::WriteAllText($batchFile, $batchContent)

cmd.exe /c $batchFile

Write-Host "=== 4. Encoding H.264 MP4 with FFmpeg ===" -ForegroundColor Cyan
$FRAMES_PATTERN = "$OUT_DIR\direct_svg_morph_frames\frame_%04d.png"
$MP4_PATH = "$OUT_DIR\direct_svg_morph_showcase.mp4"

& ffmpeg.exe -y -framerate 60 -i $FRAMES_PATTERN -c:v libx264 -pix_fmt yuv420p -crf 17 -movflags +faststart $MP4_PATH

Write-Host "=== 5. Video Inspection (ffprobe) ===" -ForegroundColor Green
& ffprobe.exe -v error -show_entries format=duration,size,bit_rate -show_entries stream=width,height,r_frame_rate,nb_frames -of default=noprint_wrappers=1 $MP4_PATH

Write-Host "Direct Native C++ SVG Morphing Showcase completed successfully!" -ForegroundColor Green
