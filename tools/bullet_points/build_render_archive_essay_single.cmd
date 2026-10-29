@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
cl.exe /nologo /std:c++17 /EHsc /O2 /I"C:\Users\pater\Pyt\Chronon3d\vcpkg_installed\win-release\x64-windows\include" "C:\Users\pater\Pyt\ChrononTemplate\tools\bullet_points\render_archive_essay_single.cpp" /Fe:"C:\Users\pater\Pyt\ChrononTemplate\tools\bullet_points\render_archive_essay_single.exe" /link /LIBPATH:"C:\Users\pater\Pyt\Chronon3d\vcpkg_installed\win-release\x64-windows\lib" blend2d.lib
if errorlevel 1 exit /b 1
"C:\Users\pater\Pyt\ChrononTemplate\tools\bullet_points\render_archive_essay_single.exe"
exit /b %errorlevel%
