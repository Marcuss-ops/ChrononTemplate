param([Parameter(Mandatory = $true)][ValidateRange(1, 20)][int]$Scene)
$src = "C:\Users\pater\dev\projects\ChrononTemplate\tools\youtuber_style"
$inc = "C:\Users\pater\Pyt\Chronon3d\vcpkg_installed\x64-windows\include"
$lib = "C:\Users\pater\Pyt\Chronon3d\vcpkg_installed\x64-windows\lib"
$env:PATH = "C:\Users\pater\Pyt\Chronon3d\vcpkg_installed\x64-windows\bin;" + $env:PATH
$cl = "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
$pattern = $Scene.ToString("00") + "_*.cpp"
$unit = Get-ChildItem -Path $src -Filter $pattern | Select-Object -First 1
if (-not $unit) { throw "No C++ scene unit found for scene $Scene" }
$exe = [System.IO.Path]::ChangeExtension($unit.FullName, ".exe")
cmd /c "call `"$cl`" && cl /std:c++17 /EHsc /O2 /I `"$inc`" `"$($unit.FullName)`" /link /LIBPATH:`"$lib`" blend2d.lib /out:`"$exe`""
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $exe
exit $LASTEXITCODE
