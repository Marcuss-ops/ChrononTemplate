@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"

echo === 1. Compiling Showcase 2 (Primitives, Pivot, Inner Glow, Radial Sun, Mountain) ===
cl.exe /nologo /std:c++17 /EHsc /O2 /I"C:\Users\pater\Pyt\Chronon3d\vcpkg_installed\win-release\x64-windows\include" "C:\Users\pater\Pyt\ChrononTemplate\tools\vector_diagram\render_primitives_scaling_showcase_blend2d.cpp" /Fe:"C:\Users\pater\Pyt\ChrononTemplate\tools\vector_diagram\render_primitives_scaling_showcase_blend2d.exe" /link /LIBPATH:"C:\Users\pater\Pyt\Chronon3d\vcpkg_installed\win-release\x64-windows\lib" blend2d.lib
if errorlevel 1 exit /b 1

echo === 2. Rendering Showcase 2 Frames ===
"C:\Users\pater\Pyt\ChrononTemplate\tools\vector_diagram\render_primitives_scaling_showcase_blend2d.exe" "C:\Users\pater\Pyt\ChrononTemplate\out\svg_parity\showcase_frames"
if errorlevel 1 exit /b 1

echo === 3. Compiling Showcase 1 (Node Graph & Transparent Icons) ===
cl.exe /nologo /std:c++17 /EHsc /O2 /I"C:\Users\pater\Pyt\Chronon3d\vcpkg_installed\win-release\x64-windows\include" "C:\Users\pater\Pyt\ChrononTemplate\tools\vector_diagram\render_icon_constellation_blend2d.cpp" /Fe:"C:\Users\pater\Pyt\ChrononTemplate\tools\vector_diagram\render_icon_constellation_blend2d.exe" /link /LIBPATH:"C:\Users\pater\Pyt\Chronon3d\vcpkg_installed\win-release\x64-windows\lib" blend2d.lib
if errorlevel 1 exit /b 1

echo === 4. Rendering Showcase 1 Frames ===
"C:\Users\pater\Pyt\ChrononTemplate\tools\vector_diagram\render_icon_constellation_blend2d.exe"
if errorlevel 1 exit /b 1