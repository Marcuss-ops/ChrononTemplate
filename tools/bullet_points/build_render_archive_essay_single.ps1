param([switch]$BuildOnly)
$ErrorActionPreference = 'Stop'
$root = 'C:\Users\pater\Pyt'
$srcDir = Join-Path $root 'ChrononTemplate\tools\bullet_points'
$vcpkg = Join-Path $root 'Chronon3d\vcpkg_installed\win-release\x64-windows'
$msvc = 'C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat'
$source = Join-Path $srcDir 'render_archive_essay_single.cpp'
$exe = Join-Path $srcDir 'render_archive_essay_single.exe'
$env:PATH = (Join-Path $vcpkg 'bin') + ';' + $env:PATH
$cmdFile = Join-Path $srcDir 'build_render_archive_essay_single.cmd'
$body = @"
@echo off
call "$msvc"
if errorlevel 1 exit /b 1
cl.exe /nologo /std:c++17 /EHsc /O2 /I"$(Join-Path $vcpkg 'include')" "$source" /Fe:"$exe" /link /LIBPATH:"$(Join-Path $vcpkg 'lib')" blend2d.lib
if errorlevel 1 exit /b 1
"@
$body += "`r`n"
if (-not $BuildOnly) { $body += "`"$exe`"`r`nexit /b %errorlevel%`r`n" }
[System.IO.File]::WriteAllText($cmdFile, $body)
cmd.exe /c $cmdFile
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
