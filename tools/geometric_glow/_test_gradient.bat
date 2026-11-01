@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
set PATH=C:\Users\pater\dev\projects\Chronon3d\vcpkg_installed\win-release\vcpkg\pkgs\blend2d_x64-windows-release\bin;C:\Users\pater\dev\projects\Chronon3d\vcpkg_installed\win-release\vcpkg\pkgs\asmjit_x64-windows-release\bin;%PATH%
cd /d C:\Users\pater\Pyt\chronons\ChrononTemplate\tools\geometric_glow
cl /nologo /std:c++17 /EHsc /O2 /I C:\Users\pater\dev\projects\Chronon3d\vcpkg_installed\win-release\vcpkg\pkgs\blend2d_x64-windows-release\include _test_gradient.cpp /link /LIBPATH:C:\Users\pater\dev\projects\Chronon3d\vcpkg_installed\win-release\vcpkg\pkgs\blend2d_x64-windows-release\lib blend2d.lib /out:_test_gradient.exe
if errorlevel 1 exit /b 1
_test_gradient.exe
echo EXITCODE=%ERRORLEVEL%