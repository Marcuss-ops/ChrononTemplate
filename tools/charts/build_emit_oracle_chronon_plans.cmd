@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
cl.exe /nologo /std:c++20 /EHsc /O2 /utf-8 /I"C:\Users\pater\Pyt\Chronon3d\vcpkg_installed\win-release\x64-windows\include" "C:\Users\pater\Pyt\ChrononTemplate\tools\charts\emit_oracle_chronon_plans.cpp" /Fe:"C:\Users\pater\Pyt\ChrononTemplate\tools\charts\emit_oracle_chronon_plans.exe"
if errorlevel 1 exit /b 1
"C:\Users\pater\Pyt\ChrononTemplate\tools\charts\emit_oracle_chronon_plans.exe" "C:\Users\pater\Pyt\ChrononTemplate\out\charts\oracle_deal_chronon\plans"
exit /b %errorlevel%
