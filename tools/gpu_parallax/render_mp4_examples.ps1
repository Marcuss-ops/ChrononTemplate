param(
    [string]$Chronon3dCli = "..\Chronon3d-mainfix\build\chronon\win-release-clang\apps\chronon3d_cli\chronon3d_cli.exe",
    [string]$OutputDirectory = "out\gpu_food_parallax_v1\mp4"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
if (-not [System.IO.Path]::IsPathRooted($Chronon3dCli)) {
    $Chronon3dCli = Join-Path $root $Chronon3dCli
}
if (-not [System.IO.Path]::IsPathRooted($OutputDirectory)) {
    $OutputDirectory = Join-Path $root $OutputDirectory
}
if (-not (Test-Path -LiteralPath $Chronon3dCli -PathType Leaf)) {
    throw "Chronon3D CLI not found: $Chronon3dCli"
}
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$author = Join-Path $root "tools\gpu_parallax\author_food_parallax.py"
& python $author
if ($LASTEXITCODE -ne 0) {
    throw "Failed to author the GPU parallax RenderPlans"
}

$workspace = Split-Path -Parent $root
$plans = Join-Path $root "examples\gpu_food_parallax_v1\plans"
Get-ChildItem -LiteralPath $plans -Filter "*.plan.json" | Sort-Object Name | ForEach-Object {
    $name = $_.BaseName -replace '\.plan$', ''
    $output = Join-Path $OutputDirectory ($name + ".mp4")
    & $Chronon3dCli render --plan $_.FullName --assets-root $workspace `
        --backend vulkan --profile maximum --start-frame 0 --end-frame 179 `
        --fps 30 --codec h264_nvenc --hardware nvenc --pipe-pixfmt nv12 `
        --motion-blur --motion-blur-mode 1 --motion-blur-samples 6 --shutter-angle 150 `
        --output $output --report
    if ($LASTEXITCODE -ne 0) {
        throw "Render failed: $($_.Name)"
    }

    $timing = Get-Content -LiteralPath "$output.timing.json" -Raw | ConvertFrom-Json
    if ($timing.frame_times_ms.Count -ne 180 -or
        $timing.job.gpu.effective_backend -ne "vulkan" -or
        $timing.job.gpu.gpu_nodes -le 0 -or
        $timing.job.gpu.software_fallback_nodes -ne 0) {
        throw "GPU/frame verification failed: $output"
    }
    Write-Output "Rendered $output (1920x1080, 180 frames, Vulkan, NVENC)"
}
