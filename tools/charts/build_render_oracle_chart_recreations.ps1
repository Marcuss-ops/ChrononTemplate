$ErrorActionPreference = 'Stop'
$root = 'C:\Users\pater\Pyt'
$template = Join-Path $root 'ChrononTemplate'
$srcDir = Join-Path $template 'tools\charts'
$vcpkg = Join-Path $root 'Chronon3d\vcpkg_installed\win-release\x64-windows'
$msvc = 'C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat'
$source = Join-Path $srcDir 'render_oracle_chart_recreations.cpp'
$exe = Join-Path $srcDir 'render_oracle_chart_recreations.exe'
$env:PATH = (Join-Path $vcpkg 'bin') + ';' + $env:PATH
$cmdFile = Join-Path $srcDir 'build_render_oracle_chart_recreations.cmd'
$body = @"
@echo off
call "$msvc"
if errorlevel 1 exit /b 1
cl.exe /nologo /std:c++20 /EHsc /O2 /utf-8 /I"$(Join-Path $vcpkg 'include')" "$source" /Fe:"$exe" /link /LIBPATH:"$(Join-Path $vcpkg 'lib')" blend2d.lib
if errorlevel 1 exit /b 1
"$exe"
exit /b %errorlevel%
"@
[System.IO.File]::WriteAllText($cmdFile, $body + "`r`n")
cmd.exe /c $cmdFile
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
