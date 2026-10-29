@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
cl /nologo /std:c++17 /EHsc /O2 /I "C:\Users\pater\Pyt\Chronon3d\vcpkg_installed\win-release\x64-windows\include" "%~dp0text_kinetic_showcase.cpp" /Fe:"%~dp0text_kinetic_showcase.exe" /link /LIBPATH:"C:\Users\pater\Pyt\Chronon3d\vcpkg_installed\win-release\x64-windows\lib" blend2d.lib
