param([Parameter(ValueFromRemainingArguments = $true)][string[]]$GeneratorArgs)

$src = "C:\Users\pater\Pyt\ChrononTemplate\tools\youtuber_style"
$inc = "C:\Users\pater\Pyt\Chronon3d\vcpkg_installed\win-release\x64-windows\include"
$lib = "C:\Users\pater\Pyt\Chronon3d\vcpkg_installed\win-release\x64-windows\lib"
$env:PATH = "C:\Users\pater\Pyt\Chronon3d\vcpkg_installed\win-release\x64-windows\bin;" + $env:PATH
$vcvars = "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"

$unit = Join-Path $src "text_kinetic_showcase.cpp"
$exe = [System.IO.Path]::ChangeExtension($unit, ".exe")

cmd /c "call `"$vcvars`" && cl /nologo /std:c++17 /EHsc /O2 /I `"$inc`" `"$unit`" /Fe:`"$exe`" /link /LIBPATH:`"$lib`" blend2d.lib"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Set-Location "C:\Users\pater\Pyt\ChrononTemplate"
& $exe @GeneratorArgs
exit $LASTEXITCODE
