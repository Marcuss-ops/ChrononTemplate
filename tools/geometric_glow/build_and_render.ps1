# geometric_glow — compile with MSVC + Blend2D, render all 480 frames, encode MP4.
$srcDir = "C:\Users\pater\Pyt\chronons\ChrononTemplate\tools\geometric_glow"
$pkgs   = "C:\Users\pater\dev\projects\Chronon3d\vcpkg_installed\win-release\vcpkg\pkgs"
$inc1   = "$pkgs\blend2d_x64-windows-release\include"
$lib    = "$pkgs\blend2d_x64-windows-release\lib"
$env:PATH = "$pkgs\blend2d_x64-windows-release\bin;$pkgs\asmjit_x64-windows-release\bin;" + $env:PATH

$exe = Join-Path $srcDir "geometric_glow.exe"
$vcvars = "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"

Write-Host "=== Compiling geometric_glow ==="
$cmd = "call `"$vcvars`" && cl /std:c++17 /EHsc /O2 /I `"$inc1`" `"$srcDir\geometric_glow.cpp`" /link /LIBPATH:`"$lib`" blend2d.lib /out:`"$exe`""
cmd /c $cmd

if (-not (Test-Path $exe)) {
    Write-Host "Failed to compile geometric_glow" -ForegroundColor Red
    exit 1
}

Write-Host ">>> Rendering 480 frames (16 s @ 30 fps, 1280x720)..."
Push-Location $srcDir
& $exe (Join-Path $srcDir "out")
$renderExit = $LASTEXITCODE
Pop-Location
if ($renderExit -ne 0) { exit $renderExit }

# Encode MP4
$ffmpeg = "C:\Ffmpeg\ffmpeg.exe"
if (-not (Test-Path $ffmpeg)) { $ffmpeg = "ffmpeg" }
$outMp4 = Join-Path $srcDir "geometric_glow.mp4"
Write-Host ">>> Encoding $outMp4"
& $ffmpeg -y -framerate 30 -i (Join-Path $srcDir "out\frame_%04d.png") -c:v libx264 -pix_fmt yuv420p -crf 16 -movflags +faststart $outMp4
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Done: $outMp4" -ForegroundColor Green
