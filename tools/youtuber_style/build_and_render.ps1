$srcDir = "C:\Users\pater\dev\projects\ChrononTemplate\tools\youtuber_style"
$inc = "C:\Users\pater\Pyt\Chronon3d\vcpkg_installed\x64-windows\include"
$lib = "C:\Users\pater\Pyt\Chronon3d\vcpkg_installed\x64-windows\lib"
$env:PATH = "C:\Users\pater\Pyt\Chronon3d\vcpkg_installed\x64-windows\bin;" + $env:PATH

$files = Get-ChildItem -Path $srcDir -Filter "*.cpp" | Where-Object { $_.Name -match "^\d{2}_" } | Sort-Object Name

Write-Host "Found $($files.Count) C++ animation sources to compile and run..."

foreach ($f in $files) {
    $base = [System.IO.Path]::GetFileNameWithoutExtension($f.Name)
    $exe = Join-Path $srcDir "$base.exe"
    
    Write-Host "`n=== Compiling $base ==="
    cmd /c "call `"C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat`" && cl /std:c++17 /EHsc /O2 /I `"$inc`" `"$($f.FullName)`" /link /LIBPATH:`"$lib`" blend2d.lib /out:`"$exe`""
    
    if (Test-Path $exe) {
        Write-Host ">>> Executing $base.exe..."
        & $exe
    } else {
        Write-Host "Failed to compile $base" -ForegroundColor Red
    }
}

Write-Host "`nAll animations compiled and rendered!" -ForegroundColor Green
