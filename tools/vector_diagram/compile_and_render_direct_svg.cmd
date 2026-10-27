@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"

echo === 1. Compiling and Running Native C++ SVG Parser Unit Tests ===
cl.exe /nologo /std:c++17 /EHsc /O2 /I"C:\Users\pater\Pyt\ChrononTemplate\include" /I"C:\Users\pater\Pyt\Chronon3d\vcpkg_installed\win-release\x64-windows\include" "C:\Users\pater\Pyt\ChrononTemplate\tools\vector_diagram\test_native_svg_parser.cpp" /Fe:"C:\Users\pater\Pyt\ChrononTemplate\tools\vector_diagram\test_native_svg_parser.exe" /link /LIBPATH:"C:\Users\pater\Pyt\Chronon3d\vcpkg_installed\win-release\x64-windows\lib" blend2d.lib
if errorlevel 1 exit /b 1
"C:\Users\pater\Pyt\ChrononTemplate\tools\vector_diagram\test_native_svg_parser.exe"
if errorlevel 1 exit /b 1

echo === 2. Compiling Native C++ Direct SVG Morph Renderer ===
cl.exe /nologo /std:c++17 /EHsc /O2 /I"C:\Users\pater\Pyt\ChrononTemplate\include" /I"C:\Users\pater\Pyt\Chronon3d\vcpkg_installed\win-release\x64-windows\include" "C:\Users\pater\Pyt\ChrononTemplate\tools\vector_diagram\render_svg_direct_morph_blend2d.cpp" /Fe:"C:\Users\pater\Pyt\ChrononTemplate\tools\vector_diagram\render_svg_direct_morph_blend2d.exe" /link /LIBPATH:"C:\Users\pater\Pyt\Chronon3d\vcpkg_installed\win-release\x64-windows\lib" blend2d.lib
if errorlevel 1 exit /b 1

echo === 3. Running Native C++ Direct SVG Morph Renderer ===
"C:\Users\pater\Pyt\ChrononTemplate\tools\vector_diagram\render_svg_direct_morph_blend2d.exe"
if errorlevel 1 exit /b 1