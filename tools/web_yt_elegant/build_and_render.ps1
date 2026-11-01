$srcDir = "C:\Users\pater\Pyt\chronons\ChrononTemplate\tools\web_yt_elegant"
$pkgs = "C:\Users\pater\dev\projects\Chronon3d\vcpkg_installed\win-release\vcpkg\pkgs"
$inc1 = "$pkgs\blend2d_x64-windows-release\include"
$inc2 = "$pkgs\nlohmann-json_x64-windows-release\include"
$lib  = "$pkgs\blend2d_x64-windows-release\lib"
$env:PATH = "$pkgs\blend2d_x64-windows-release\bin;" + $env:PATH

$exe = Join-Path $srcDir "web_yt_elegant.exe"
$vcvars = "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"

Write-Host "=== Compiling web_yt_elegant ==="
$cmd = "call `"$vcvars`" && cl /std:c++17 /EHsc /O2 /I `"$inc1`" /I `"$inc2`" `"$srcDir\web_yt_elegant.cpp`" /link /LIBPATH:`"$lib`" blend2d.lib /out:`"$exe`""
cmd /c $cmd

if (Test-Path $exe) {
    Write-Host ">>> Rendering all 15 web/elegant shots..."
    & $exe
} else {
    Write-Host "Failed to compile web_yt_elegant" -ForegroundColor Red
    exit 1
}
