$ErrorActionPreference = 'Stop'
$workspace = 'C:\Users\pater\Pyt'
$collection = Join-Path $workspace 'ChrononTemplate\out\vector_animation_collection'
$videos = Get-ChildItem $collection -Filter '*.mp4' | Where-Object { $_.Name -match '^\d{3}_.*\.mp4$' }
$manifest = Get-Content -Raw (Join-Path $collection 'manifest.json') | ConvertFrom-Json
$zipArtifacts = @((Join-Path (Split-Path $collection -Parent) 'vector_animation_collection.zip'),(Join-Path (Split-Path $collection -Parent) 'vector_animation_collection.zip.sha256')) | Where-Object { Test-Path $_ }
$badVideos = [System.Collections.Generic.List[string]]::new()
$badEncoderRecords = @($manifest.clips | Where-Object { $_.encoder -ne 'h264_nvenc' }).Count
foreach ($video in $videos) {
    $probe = & ffprobe -v error -count_frames -select_streams v:0 -show_entries format=duration -show_entries stream=width,height,r_frame_rate,nb_read_frames -of json $video.FullName | ConvertFrom-Json
    $stream = $probe.streams[0]
    if ($stream.width -ne 1280 -or $stream.height -ne 720 -or $stream.r_frame_rate -ne '30/1' -or $stream.nb_read_frames -ne '120' -or $probe.format.duration -ne '4.000000') {
        $badVideos.Add($video.Name)
    }
}
$previewPngs = (Get-ChildItem (Join-Path $collection 'previews') -Filter 'variation_*.png').Count
$sourceSvgs = (Get-ChildItem (Join-Path $collection 'sources') -Filter '*.svg').Count
$result = [pscustomobject]@{Videos=$videos.Count;ManifestClips=$manifest.clips.Count;Variations=$manifest.variations.Count;PreviewPngs=$previewPngs;SourceSvgs=$sourceSvgs;BadVideos=$badVideos.Count;BadEncoderRecords=$badEncoderRecords;OutputFps=$manifest.output_format.fps;ZipArtifacts=$zipArtifacts.Count}
$result | Format-List
if ($result.Videos -ne 100 -or $result.ManifestClips -ne 100 -or $result.Variations -ne 100 -or $result.PreviewPngs -ne 100 -or $result.SourceSvgs -ne 25 -or $result.BadVideos -ne 0 -or $result.BadEncoderRecords -ne 0 -or $result.OutputFps -ne 30 -or $result.ZipArtifacts -ne 0) {
    throw "MP4 collection verification failed. Bad videos: $($badVideos -join ', ')"
}
Write-Host 'PASS: all 100 variations are verified MP4 videos.'
