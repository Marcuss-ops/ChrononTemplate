param(
    [string]$TemplateRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path,
    [string]$ChrononCli = '',
    [int]$ThrottleLimit = 4,
    [int[]]$TestIds = (1..36),
    [switch]$SkipRender
)

$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent $TemplateRoot
if (-not $ChrononCli) {
    $ChrononCli = Join-Path $workspace 'Chronon3d-windows-latest\build\chronon\win-release-clang\apps\chronon3d_cli\chronon3d_cli.exe'
}
$chrononDlls = Join-Path $workspace 'Chronon3d-windows-latest\vcpkg_installed\win-release\x64-windows\bin'
$corpus = Join-Path $TemplateRoot 'out\charts_corpus'
$plans = Join-Path $corpus 'json'
$output = Join-Path $corpus 'mp4'
$timings = Join-Path $corpus 'timing'
if (-not (Test-Path -LiteralPath $ChrononCli -PathType Leaf)) { throw "Chronon CLI not found: $ChrononCli" }
if (-not (Test-Path -LiteralPath $plans -PathType Container)) { throw "C++ RenderPlans not found: $plans" }
$allPlans = @(Get-ChildItem -LiteralPath $plans -File -Filter 'test_*.plan.json')
$planFiles = foreach ($id in 1..36) {
    $prefix = 'test_{0:D2}_' -f $id
    $match = @($allPlans | Where-Object Name -Like "$prefix*.plan.json" |
        Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1)
    if ($match.Count -ne 1) { throw "Missing C++ RenderPlan for test $id" }
    $match[0]
}
if ($planFiles.Count -ne 36) { throw "Expected 36 C++ plans, found $($planFiles.Count)" }
if (@($TestIds | Where-Object { $_ -lt 1 -or $_ -gt 36 }).Count -gt 0) { throw 'TestIds must be between 1 and 36' }
$activePlans = @($planFiles | ForEach-Object FullName)
$stalePlans = @($allPlans | Where-Object { $_.FullName -NotIn $activePlans })
foreach ($stale in $stalePlans) { Remove-Item -LiteralPath $stale.FullName -Force }
New-Item -ItemType Directory -Force -Path $output | Out-Null
New-Item -ItemType Directory -Force -Path $timings | Out-Null

$renderPlans = @($planFiles | Where-Object {
    $planId = [int]([regex]::Match($_.Name, '^test_(\d{2})_').Groups[1].Value)
    $planId -In $TestIds
})
if (-not $SkipRender) { $renderPlans | ForEach-Object -Parallel {
    $ErrorActionPreference = 'Stop'
    $plan = $_.FullName
    $root = $using:output
    $assets = $using:TemplateRoot
    $cli = $using:ChrononCli
    $env:PATH = $using:chrononDlls + ';' + $env:PATH
    $stem = $_.BaseName -replace '\.plan$', ''
    $timingDir = $using:timings
    $raw = Join-Path $timingDir ($stem + '.nv12')
    $temporary = Join-Path $root ($stem + '.native.tmp.mp4')
    $final = Join-Path $root ($stem + '.mp4')

    & $cli render --plan $plan --assets-root $assets --backend software --profile production `
        --start-frame 0 --end-frame 119 --fps 30 --video-sink raw --pipe-pixfmt nv12 `
        --hardware none --log-level error --output $raw
    if ($LASTEXITCODE -ne 0) { throw "Chronon C++ render failed: $stem (exit $LASTEXITCODE)" }

    & ffmpeg -y -v error -f rawvideo -pixel_format nv12 -video_size 1920x1080 -framerate 30 `
        -i $raw -frames:v 120 -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p $temporary
    if ($LASTEXITCODE -ne 0) { throw "H.264 encode failed: $stem (exit $LASTEXITCODE)" }

    $probeJson = & ffprobe -v error -select_streams v:0 `
        -show_entries stream=codec_name,width,height,r_frame_rate,nb_frames -of json $temporary
    if ($LASTEXITCODE -ne 0) { throw "ffprobe failed: $stem" }
    $stream = ($probeJson | ConvertFrom-Json).streams[0]
    if ($stream.codec_name -ne 'h264' -or $stream.width -ne 1920 -or $stream.height -ne 1080 -or
        $stream.r_frame_rate -ne '30/1' -or [int]$stream.nb_frames -ne 120) {
        throw "Invalid output contract for ${stem}: $($stream | ConvertTo-Json -Compress)"
    }
    Move-Item -LiteralPath $temporary -Destination $final -Force
    Remove-Item -LiteralPath $raw -Force
    Write-Output "OK $([IO.Path]::GetFileName($final))"
} -ThrottleLimit $ThrottleLimit }

$activeStems = @($planFiles | ForEach-Object { $_.BaseName -replace '\.plan$', '' })
$staleVideos = @(Get-ChildItem -LiteralPath $output -File -Filter 'test_*.mp4' |
    Where-Object { $_.BaseName -NotIn $activeStems })
foreach ($stale in $staleVideos) { Remove-Item -LiteralPath $stale.FullName -Force }
$staleTimings = @(Get-ChildItem -LiteralPath $timings -File -Filter 'test_*.nv12.timing.json' |
    Where-Object { $_.Name -replace '\.nv12\.timing\.json$', '' -NotIn $activeStems })
foreach ($stale in $staleTimings) { Remove-Item -LiteralPath $stale.FullName -Force }
$mp4Files = @(Get-ChildItem -LiteralPath $output -File -Filter 'test_*.mp4' | Sort-Object Name)
if ($mp4Files.Count -ne 36) { throw "Expected 36 rendered MP4s, found $($mp4Files.Count)" }
$clips = foreach ($file in $mp4Files) {
    $probeJson = & ffprobe -v error -select_streams v:0 `
        -show_entries stream=codec_name,width,height,r_frame_rate,nb_frames -of json $file.FullName
    if ($LASTEXITCODE -ne 0) { throw "ffprobe failed: $($file.Name)" }
    $stream = ($probeJson | ConvertFrom-Json).streams[0]
    if ($stream.codec_name -ne 'h264' -or $stream.width -ne 1920 -or $stream.height -ne 1080 -or
        $stream.r_frame_rate -ne '30/1' -or [int]$stream.nb_frames -ne 120) {
        throw "Invalid output contract for $($file.Name): $($stream | ConvertTo-Json -Compress)"
    }
    [pscustomobject]@{video=$file.Name; codec='h264'; width=1920; height=1080; fps=30; frames=120}
}
$manifest = [pscustomobject]@{
    schema = 'chronontemplate.charts.render-manifest.v1'
    renderer = 'Chronon3D C++ RenderPlan -> raw NV12; FFmpeg libx264 encode'
    clips = @($clips)
}
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $plans 'render_manifest.json') -Encoding utf8

Write-Output "Rendered and verified 36 MP4s using Chronon C++ -> NV12 -> FFmpeg H.264: $output"
