@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
echo === blend2d.dll dependents ===
dumpbin /dependents "C:\Users\pater\Pyt\chronons\ChrononTemplate\tools\web_yt_elegant\blend2d.dll" | findstr /i ".dll"
echo === done ===
