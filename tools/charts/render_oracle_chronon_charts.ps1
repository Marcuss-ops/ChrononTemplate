param(
    [string]$ChrononCli = 'C:\Users\pater\Pyt\Chronon3d\build\chronon\rapdaily-release\apps\chronon3d_cli\Release\chronon3d_cli.exe'
)
$ErrorActionPreference = 'Stop'
$root = 'C:\Users\pater\Pyt'
$template = Join-Path $root 'ChrononTemplate'
$vcpkg = Join-Path $root 'Chronon3d\build\chronon\rapdaily-release\vcpkg_installed\x64-windows-release'
$msvc = 'C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat'
$source = Join-Path $template 'tools\charts\emit_oracle_chronon_plans.cpp'
$emitter = Join-Path $template 'tools\charts\emit_oracle_chronon_plans.exe'
$work = Join-Path $template 'out\charts\oracle_deal_chronon'
$plans = Join-Path $work 'plans'
$clips = Join-Path $work 'clips'
$rawDir = Join-Path $work 'raw'
$env:PATH = (Join-Path $vcpkg 'bin') + ';' + $env:PATH

$cmdFile = Join-Path $template 'tools\charts\build_emit_oracle_chronon_plans.cmd'
$cmd = @"
@echo off
call "$msvc"
if errorlevel 1 exit /b 1
cl.exe /nologo /std:c++20 /EHsc /O2 /utf-8 /I"$(Join-Path $vcpkg 'include')" "$source" /Fe:"$emitter"
if errorlevel 1 exit /b 1
"$emitter" "$plans"
exit /b %errorlevel%
"@
[System.IO.File]::WriteAllText($cmdFile, $cmd + "`r`n")
cmd.exe /c $cmdFile
if ($LASTEXITCODE -ne 0) { throw 'Chronon C++ RenderPlan generation failed.' }
if (-not (Test-Path -LiteralPath $ChrononCli -PathType Leaf)) { throw "Chronon3D CLI not found: $ChrononCli" }

New-Item -ItemType Directory -Force -Path $clips,$rawDir | Out-Null
$jobIds = @('oracle_deal_economics','oracle_j_curve_effect','oracle_profits_comparison')
foreach ($id in $jobIds) {
    $plan = Join-Path $plans ($id + '.plan.json')
    $raw = Join-Path $rawDir ($id + '.nv12')
    $segment = Join-Path $clips ($id + '.mp4')
    & $ChrononCli render --plan $plan --assets-root $template --backend software --profile production `
        --start-frame 0 --end-frame 89 --fps 30 --video-sink raw --pipe-pixfmt nv12 `
        --hardware none --log-level error --output $raw
    if ($LASTEXITCODE -ne 0) { throw "Chronon3D render failed: $id" }
    & ffmpeg.exe -y -v error -f rawvideo -pixel_format nv12 -video_size 1920x1080 -framerate 30 `
        -i $raw -frames:v 90 -c:v libx264 -preset fast -crf 17 -pix_fmt yuv420p $segment
    if ($LASTEXITCODE -ne 0) { throw "H.264 encode failed: $id" }
}

$concatList = Join-Path $work 'chronon_concat.txt'
$concatText = ($jobIds | ForEach-Object { "file '$((Join-Path $clips ($_ + '.mp4')).Replace('\','/'))'" }) -join "`n"
[System.IO.File]::WriteAllText($concatList, $concatText + "`n")
$final = Join-Path $work 'Oracle_Deal_Charts_Chronon3D_1920x1080.mp4'
& ffmpeg.exe -y -v error -f concat -safe 0 -i $concatList -c copy -movflags +faststart $final
if ($LASTEXITCODE -ne 0) { throw 'Could not concatenate the Chronon-rendered chart clips.' }
& ffprobe.exe -v error -select_streams v:0 -show_entries stream=codec_name,width,height,r_frame_rate,duration,nb_frames -of default=noprint_wrappers=1 $final
if ($LASTEXITCODE -ne 0) { throw 'ffprobe could not inspect the final Chronon render.' }
Write-Output "Rendered with Chronon3D software backend: $final"
