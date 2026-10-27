@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"

echo === 1. Compiling and Running Unit Tests ===
cl.exe /nologo /std:c++17 /EHsc /O2 /I"C:\Users\pater\Pyt\ChrononTemplate\include" "C:\Users\pater\Pyt\ChrononTemplate\tools\vector_diagram\test_topological_morpher.cpp" /Fe:"C:\Users\pater\Pyt\ChrononTemplate\tools\vector_diagram\test_topological_morpher.exe"
if errorlevel 1 exit /b 1
"C:\Users\pater\Pyt\ChrononTemplate\tools\vector_diagram\test_topological_morpher.exe"
if errorlevel 1 exit /b 1

echo === 2. Compiling and Emitting Plan ===
cl.exe /nologo /std:c++17 /EHsc /O2 "C:\Users\pater\Pyt\ChrononTemplate\tools\vector_diagram\emit_topological_morph_showcase_plan.cpp" /Fe:"C:\Users\pater\Pyt\ChrononTemplate\tools\vector_diagram\emit_topological_morph_showcase_plan.exe"
if errorlevel 1 exit /b 1
"C:\Users\pater\Pyt\ChrononTemplate\tools\vector_diagram\emit_topological_morph_showcase_plan.exe"
if errorlevel 1 exit /b 1

echo === 3. Compiling Blend2D Morph Renderer ===
cl.exe /nologo /std:c++17 /EHsc /O2 /I"C:\Users\pater\Pyt\ChrononTemplate\include" /I"C:\Users\pater\Pyt\Chronon3d\vcpkg_installed\win-release\x64-windows\include" "C:\Users\pater\Pyt\ChrononTemplate\tools\vector_diagram\render_topological_morph_blend2d.cpp" /Fe:"C:\Users\pater\Pyt\ChrononTemplate\tools\vector_diagram\render_topological_morph_blend2d.exe" /link /LIBPATH:"C:\Users\pater\Pyt\Chronon3d\vcpkg_installed\win-release\x64-windows\lib" blend2d.lib
if errorlevel 1 exit /b 1

echo === 4. Running Blend2D Morph Renderer ===
"C:\Users\pater\Pyt\ChrononTemplate\tools\vector_diagram\render_topological_morph_blend2d.exe"
if errorlevel 1 exit /b 1