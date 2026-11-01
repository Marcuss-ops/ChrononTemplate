@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
set PATH=C:\Users\pater\dev\projects\Chronon3d\vcpkg_installed\win-release\vcpkg\pkgs\blend2d_x64-windows-release\bin;%PATH%
cd /d C:\Users\pater\Pyt\chronons\ChrononTemplate\tools\geometric_glow
echo --- where checks ---
where vcruntime140.dll 2>&1
where vcruntime140_1.dll 2>&1
where msvcp140.dll 2>&1
where blend2d.dll 2>&1
where ucrtbase.dll 2>&1
echo --- dumpbin exe ---
dumpbin /dependents geometric_glow.exe 2>&1 | findstr /i ".dll"
echo --- dumpbin blend2d.dll ---
dumpbin /dependents "C:\Users\pater\dev\projects\Chronon3d\vcpkg_installed\win-release\vcpkg\pkgs\blend2d_x64-windows-release\bin\blend2d.dll" 2>&1 | findstr /i ".dll"
echo --- dumpbin exe full ---
dumpbin /dependents geometric_glow.exe 2>&1
echo --- run ---
geometric_glow.exe out
echo EXITCODE=%ERRORLEVEL%
