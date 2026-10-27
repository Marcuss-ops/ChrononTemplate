@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
cl.exe /nologo /std:c++17 /EHsc /O2 /I"C:\Users\pater\Pyt\ChrononTemplate\include" "C:\Users\pater\Pyt\ChrononTemplate\tools\vector_diagram\test_topological_morpher.cpp" /Fe:"C:\Users\pater\Pyt\ChrononTemplate\tools\vector_diagram\test_topological_morpher.exe"
"C:\Users\pater\Pyt\ChrononTemplate\tools\vector_diagram\test_topological_morpher.exe"
