param(
    [string]$TemplateRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path,
    [string]$ChrononCli = '',
    [int]$ThrottleLimit = 2,
    [int[]]$TestIds = (1..6),
    [switch]$SkipRender
)

$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent $TemplateRoot
if (-not $ChrononCli) {
    $ChrononCli = Join-Path $workspace 'Chronon3d-windows-latest\build\chronon\win-release-clang\apps\chronon3d_cli\chronon3d_cli.exe'
}
$chrononDlls = Join-Path $workspace 'Chronon3d-windows-latest\vcpkg_installed\win-release\x64-windows\bin'
$corpus = Join-Path $TemplateRoot 'out\graphs_recreated'
$plans = Join-Path $corpus 'json'
$output = Join-Path $corpus 'mp4'
$timings = Join-Path $corpus 'timing'
if (-not (Test-Path -LiteralPath $ChrononCli -PathType Leaf)) { throw "Chronon CLI not found: $ChrononCli" }
if (-not (Test-Path -LiteralPath $plans -PathType Container)) { throw "C++ RenderPlans not found: $plans" }
$allPlans = @(Get-ChildItem -LiteralPath $plans -File -Filter 'graphs_*.plan.json')
$planFiles = foreach ($id in 1..6) {
    $prefix = 'graphs_{0:D2}_' -f $id
    $match = @($allPlans | Where-Object Name -Like "$prefix*.plan.json" | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1)
    if ($match.Count -ne 1) { throw "Missing C++ RenderPlan for graph $id" }
    $match[0]
}
if ($planFiles.Count -ne 6) { throw "Expected six C++ plans, found $($planFiles.Count)" }
if (@($TestIds | Where-Object { $_ -lt 1 -or $_ -gt 6 }).Count -gt 0) { throw 'TestIds must be between 1 and 6' }
$activePlans = @($planFiles | ForEach-Object FullName)
foreach ($stale in @($allPlans | Where-Object { $_.FullName -NotIn $activePlans })) { Remove-Item -LiteralPath $stale.FullName -Force }
New-Item -ItemType Directory -Force -Path $output | Out-Null
New-Item -ItemType Directory -Force -Path $timings | Out-Null
$renderPlans = @($planFiles | Where-Object {
    $id = [int]([regex]::Match($_.Name, '^graphs_(\d{2})_').Groups[1].Value)
    $id -In $TestIds
})
if (-not $SkipRender) {
    $renderPlans | ForEach-Object -Parallel {
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
        if ($LASTEXITCODE -ne 0) { throw "H.264 encode failed: $stem" }
        $probeJson = & ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,width,height,r_frame_rate,nb_frames -of json $temporary
        if ($LASTEXITCODE -ne 0) { throw "ffprobe failed: $stem" }
        $stream = ($probeJson | ConvertFrom-Json).streams[0]
        if ($stream.codec_name -ne 'h264' -or $stream.width -ne 1920 -or $stream.height -ne 1080 -or $stream.r_frame_rate -ne '30/1' -or [int]$stream.nb_frames -ne 120) {
            throw "Invalid output contract for ${stem}: $($stream | ConvertTo-Json -Compress)"
        }
        Move-Item -LiteralPath $temporary -Destination $final -Force
        Remove-Item -LiteralPath $raw -Force
        Write-Output "OK $([IO.Path]::GetFileName($final))"
    } -ThrottleLimit $ThrottleLimit
}
$activeStems = @($planFiles | ForEach-Object { $_.BaseName -replace '\.plan$', '' })
foreach ($stale in @(Get-ChildItem -LiteralPath $output -File -Filter 'graphs_*.mp4' | Where-Object { $_.BaseName -NotIn $activeStems })) { Remove-Item -LiteralPath $stale.FullName -Force }
$clips = foreach ($file in @(Get-ChildItem -LiteralPath $output -File -Filter 'graphs_*.mp4' | Sort-Object Name)) {
    $probeJson = & ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,width,height,r_frame_rate,nb_frames -of json $file.FullName
    if ($LASTEXITCODE -ne 0) { throw "ffprobe failed: $($file.Name)" }
    $stream = ($probeJson | ConvertFrom-Json).streams[0]
    if ($stream.codec_name -ne 'h264' -or $stream.width -ne 1920 -or $stream.height -ne 1080 -or $stream.r_frame_rate -ne '30/1' -or [int]$stream.nb_frames -ne 120) {
        throw "Invalid output contract for $($file.Name): $($stream | ConvertTo-Json -Compress)"
    }
    [pscustomobject]@{video=$file.Name; codec='h264'; width=1920; height=1080; fps=30; frames=120}
}
$expectedCount = if ($TestIds.Count -eq 6) { 6 } else { $TestIds.Count }
if ($clips.Count -lt $expectedCount) { throw "Expected at least $expectedCount rendered MP4s, found $($clips.Count)" }
$manifest = [pscustomobject]@{schema='chronontemplate.graph-reference-render-manifest.v1'; renderer='Chronon C++ RenderPlan -> raw NV12; FFmpeg libx264 encode'; clips=@($clips)}
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $plans 'render_manifest.json') -Encoding utf8
Write-Output "Rendered and verified $($clips.Count) graph recreation videos: $output"
