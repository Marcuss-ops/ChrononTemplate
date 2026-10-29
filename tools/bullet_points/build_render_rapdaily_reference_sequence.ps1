param([switch]$BuildOnly)
$ErrorActionPreference = 'Stop'
$root = 'C:\Users\pater\Pyt'
$srcDir = Join-Path $root 'ChrononTemplate\tools\bullet_points'
$vcpkg = Join-Path $root 'Chronon3d\vcpkg_installed\win-release\x64-windows'
$msvc = 'C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat'
$source = Join-Path $srcDir 'render_rapdaily_reference_sequence.cpp'
$exe = Join-Path $srcDir 'render_rapdaily_reference_sequence.exe'
$env:PATH = (Join-Path $vcpkg 'bin') + ';' + $env:PATH
$outputDir = Join-Path $root 'ChrononTemplate\out\bullet_families\rapdaily_reference_rebuild'
$motionLibraryDir = Join-Path $root 'ChrononMotion3D\build\rapdaily-camera'
$sampleCsv = Join-Path $outputDir 'camera_samples.csv'
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
New-Item -ItemType Directory -Force -Path $motionLibraryDir | Out-Null
$linuxMotion = '/mnt/c/Users/pater/Pyt/ChrononMotion3D'
$linuxTemplate = '/mnt/c/Users/pater/Pyt/ChrononTemplate'
$linuxSampleCsv = '/mnt/c/Users/pater/Pyt/ChrononTemplate/out/bullet_families/rapdaily_reference_rebuild/camera_samples.csv'
$linuxMotionLibrary = '/mnt/c/Users/pater/Pyt/ChrononMotion3D/build/rapdaily-camera/chrononmotion-camera-lib.a'
$cameraBuild = @"
set -e
if [ ! -f '$linuxMotionLibrary' ]; then
  if [ ! -f /tmp/chrononmotion-agent-build/libchrononmotion.a ]; then
    cmake -S '$linuxMotion' -B /tmp/chrononmotion-agent-build -G Ninja -DCMAKE_BUILD_TYPE=Release -DCHRONONMOTION_BUILD_TESTS=OFF -DCHRONONMOTION_WERROR=OFF
    cmake --build /tmp/chrononmotion-agent-build --target chrononmotion -j 8
  fi
  cp /tmp/chrononmotion-agent-build/libchrononmotion.a '$linuxMotionLibrary'
fi
g++ -std=c++20 -O2 -I '$linuxMotion/include' '$linuxTemplate/tools/bullet_points/sample_rapdaily_camera.cpp' '$linuxMotionLibrary' -o /tmp/sample_rapdaily_camera
/tmp/sample_rapdaily_camera '$linuxSampleCsv'
"@
wsl.exe -d Ubuntu-24.04 -- bash -lc $cameraBuild
if ($LASTEXITCODE -ne 0) { throw 'ChrononMotion3D camera sampling failed.' }
$cmdFile = Join-Path $srcDir 'build_render_rapdaily_reference_sequence.cmd'
$body = @"
@echo off
call "$msvc"
if errorlevel 1 exit /b 1
cl.exe /nologo /std:c++20 /EHsc /O2 /I"$(Join-Path $vcpkg 'include')" "$source" /Fe:"$exe" /link /LIBPATH:"$(Join-Path $vcpkg 'lib')" blend2d.lib
if errorlevel 1 exit /b 1
"@
$body += "`r`n"
if (-not $BuildOnly) { $body += "`"$exe`"`r`nexit /b %errorlevel%`r`n" }
[System.IO.File]::WriteAllText($cmdFile, $body)
cmd.exe /c $cmdFile
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
