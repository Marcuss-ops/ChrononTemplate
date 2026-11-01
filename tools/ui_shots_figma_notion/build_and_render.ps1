$srcDir = "C:\Users\pater\Pyt\chronons\ChrononTemplate\tools\ui_shots_figma_notion"
$vpk = "C:\Users\pater\Pyt\chronons\Chronon3d\build\chronon\rapdaily-release\vcpkg_installed\x64-windows-release"
$inc = "$vpk\include"
$lib = "$vpk\lib"
$env:PATH = "$vpk\bin;" + $env:PATH

$exe = Join-Path $srcDir "ui_shots_figma_notion.exe"
$vcvars = "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"

Write-Host "=== Compiling ui_shots_figma_notion ==="
$cmd = "call `"$vcvars`" && cl /std:c++17 /EHsc /O2 /I `"$inc`" `"$srcDir\ui_shots_figma_notion.cpp`" /link /LIBPATH:`"$lib`" blend2d.lib /out:`"$exe`""
cmd /c $cmd

if (Test-Path $exe) {
    Write-Host ">>> Rendering all 15 figma/notion shots..."
    & $exe
} else {
    Write-Host "Failed to compile ui_shots_figma_notion" -ForegroundColor Red
    exit 1
}
