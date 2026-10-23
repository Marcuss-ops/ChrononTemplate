$src = "C:\Users\pater\dev\projects\ChrononTemplate\tools\youtuber_style"
$inc = "C:\Users\pater\Pyt\Chronon3d\vcpkg_installed\x64-windows\include"
$lib = "C:\Users\pater\Pyt\Chronon3d\vcpkg_installed\x64-windows\lib"
$env:PATH = "C:\Users\pater\Pyt\Chronon3d\vcpkg_installed\x64-windows\bin;" + $env:PATH
$cl = "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
$source = Join-Path $src "01_subject_floating_push.cpp"
$exe = Join-Path $src "01_subject_floating_push.exe"
cmd /c "call `"$cl`" && cl /std:c++17 /EHsc /O2 /I `"$inc`" `"$source`" /link /LIBPATH:`"$lib`" blend2d.lib /out:`"$exe`""
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $exe
exit $LASTEXITCODE
