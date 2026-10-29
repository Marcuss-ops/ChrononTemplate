@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
cl.exe /nologo /std:c++17 /EHsc /O2 /I"C:\Users\pater\Pyt\Chronon3d\vcpkg_installed\win-release\x64-windows\include" "C:\Users\pater\Pyt\ChrononTemplate\tools\bullet_points\render_rapdaily_boosie_title.cpp" /Fe:"C:\Users\pater\Pyt\ChrononTemplate\tools\bullet_points\render_rapdaily_boosie_title.exe" /link /LIBPATH:"C:\Users\pater\Pyt\Chronon3d\vcpkg_installed\win-release\x64-windows\lib" blend2d.lib
if errorlevel 1 exit /b 1
"C:\Users\pater\Pyt\ChrononTemplate\tools\bullet_points\render_rapdaily_boosie_title.exe"
exit /b %errorlevel%
