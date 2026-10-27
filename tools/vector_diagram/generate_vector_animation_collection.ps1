param(
    [string]$Workspace = "C:\Users\pater\Pyt",
    [int]$Width = 1280,
    [int]$Height = 720,
    # Render one unique image per output frame; the previous 15 fps source
    # duplicated frames at encode time and looked visibly stuttery.
    [int]$Fps = 30,
    [switch]$Resume,
    [int]$StartVariation = 1,
    [int]$EndVariation = 100,
    [switch]$SkipFinalArtifacts,
    [int]$Seconds = 4
)

$ErrorActionPreference = "Stop"
$assets = Join-Path $Workspace "ChrononTemplate\assets\downloaded_vectors"
$out = Join-Path $Workspace "ChrononTemplate\out\vector_animation_collection"
$previewDir = Join-Path $out "previews"
$svgWork = Join-Path $out "svg_work"
$sourceDir = Join-Path $out "sources"
New-Item -ItemType Directory -Force -Path $previewDir,$svgWork,$sourceDir | Out-Null
if (-not $SkipFinalArtifacts) {
    Copy-Item -Path (Join-Path $assets '*') -Destination $sourceDir -Force
    if (Test-Path (Join-Path $out 'keyframes')) { Remove-Item -LiteralPath (Join-Path $out 'keyframes') -Recurse -Force }
    Remove-Item -LiteralPath (Join-Path $out 'SHA256SUMS.txt') -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath (Join-Path (Split-Path $out -Parent) 'vector_animation_collection.zip'),(Join-Path (Split-Path $out -Parent) 'vector_animation_collection.zip.sha256') -Force -ErrorAction SilentlyContinue
}

$magick = (Get-Command magick.exe).Source
$ffmpeg = (Get-Command ffmpeg.exe).Source
$ffprobe = (Get-Command ffprobe.exe).Source
$ffmpegEncoders = (& $ffmpeg -hide_banner -encoders 2>&1 | Out-String)
if ($ffmpegEncoders -notmatch 'h264_nvenc') { throw 'GPU encoding unavailable: FFmpeg does not expose h264_nvenc.' }
$themes = @(
    @{id='summit_signal'; icon='mountain'; title='SUMMIT SIGNAL'},
    @{id='solar_arc'; icon='sun'; title='SOLAR ARC'},
    @{id='lunar_drift'; icon='moon'; title='LUNAR DRIFT'},
    @{id='forest_beacon'; icon='tree-pine'; title='FOREST BEACON'},
    @{id='compass_trace'; icon='compass'; title='COMPASS TRACE'},
    @{id='waypoint_bloom'; icon='map-pin'; title='WAYPOINT BLOOM'},
    @{id='alpine_ride'; icon='bike'; title='ALPINE RIDE'},
    @{id='transit_glow'; icon='train-front'; title='TRANSIT GLOW'},
    @{id='night_route'; icon='bus-front'; title='NIGHT ROUTE'},
    @{id='escape_vector'; icon='rocket'; title='ESCAPE VECTOR'},
    @{id='idea_ignition'; icon='lightbulb'; title='IDEA IGNITION'},
    @{id='lab_signal'; icon='flask-conical'; title='LAB SIGNAL'},
    @{id='atom_pulse'; icon='atom'; title='ATOM PULSE'},
    @{id='vital_arc'; icon='heart-pulse'; title='VITAL ARC'},
    @{id='footstep_odyssey'; icon='footprints'; title='FOOTSTEP ODYSSEY'},
    @{id='tidal_memory'; icon='waves'; title='TIDAL MEMORY'},
    @{id='stormfront'; icon='cloud-sun'; title='STORMFRONT'},
    @{id='observatory'; icon='telescope'; title='OBSERVATORY'},
    @{id='deep_voyage'; icon='ship'; title='DEEP VOYAGE'},
    @{id='orbit_garden'; icon='orbit'; title='ORBIT GARDEN'}
)
$palettes = @(
    @{name='arctic_cyan'; a='#54F5E6'; b='#87B7FF'; bg='#07131E'},
    @{name='solar_amber'; a='#FFD36A'; b='#FF6A57'; bg='#1A0E16'},
    @{name='ultraviolet'; a='#D897FF'; b='#6E7CFF'; bg='#100B22'},
    @{name='verdant'; a='#A8FF78'; b='#26D6A5'; bg='#071A18'},
    @{name='rose_neon'; a='#FF83C7'; b='#FFB16A'; bg='#1C0C1A'}
)

if ($Resume) {
    for ($i=0; $i -lt 20; $i++) {
        $p=$i%5
        $old=Join-Path $out ('{0:00}_{1}.mp4' -f ($i+1),$themes[$i].id)
        $variationIndex=$i*5+$p+1
        $new=Join-Path $out ('{0:000}_{1}_{2}.mp4' -f $variationIndex,$themes[$i].id,$palettes[$p].name)
        if ((Test-Path $old) -and -not (Test-Path $new)) { Move-Item -LiteralPath $old -Destination $new }
    }
}

function Get-IconMarkup([string]$icon,[string]$color) {
    $path = Join-Path $assets "lucide-$icon.svg"
    if (-not (Test-Path $path)) { $path = Join-Path $assets 'lucide-mountain.svg' }
    [xml]$doc = Get-Content -Raw -Path $path
    $root = $doc.SelectSingleNode("//*[local-name()='svg']")
    $content = $root.InnerXml.Replace('#ffffff',$color).Replace('#FFFFFF',$color)
    return $content
}

function Get-Profile([int]$seed) {
    $pts = @()
    $n = 7
    for ($j=0; $j -lt $n; $j++) {
        $x = [Math]::Round(85 + $j * 183 + (($seed * 13 + $j * 31) % 37))
        $wave = [Math]::Sin(($j * 1.31) + ($seed * 0.63))
        $y = [Math]::Round(506 - (82 + (($seed * 7 + $j * 19) % 112)) - $wave * 28)
        $pts += ,@($x,$y)
    }
    $pts[0] = @(72,560)
    $pts[$n-1] = @(1206,552)
    return ,$pts
}

function Get-ProgressPoint($points,[double]$progress) {
    $lengths = @(); $total = 0.0
    for ($j=0; $j -lt $points.Count-1; $j++) {
        $dx = $points[$j+1][0] - $points[$j][0]
        $dy = $points[$j+1][1] - $points[$j][1]
        $len = [Math]::Sqrt($dx*$dx+$dy*$dy)
        $lengths += $len; $total += $len
    }
    $progress = [Math]::Max(0.0,[Math]::Min(1.0,$progress))
    $remaining = $progress * $total
    for ($j=0; $j -lt $lengths.Count; $j++) {
        if ($remaining -le $lengths[$j] -or $j -eq $lengths.Count-1) {
            $t = if ($lengths[$j] -gt 0) {$remaining/$lengths[$j]} else {0}
            return @(
                [Math]::Round($points[$j][0]+($points[$j+1][0]-$points[$j][0])*$t,2),
                [Math]::Round($points[$j][1]+($points[$j+1][1]-$points[$j][1])*$t,2)
            )
        }
        $remaining -= $lengths[$j]
    }
    return $points[-1]
}

function New-SceneSvg([int]$themeIndex,[int]$paletteIndex,[int]$frame,[bool]$preview=$false) {
    $theme = $themes[$themeIndex]
    $palette = $palettes[$paletteIndex]
    $t = if ($preview) {0.68} else {$frame / [double]($Fps*$Seconds-1)}
    $u = ($t-0.08)/0.78
    $u = [Math]::Max(0.0,[Math]::Min(1.0,$u))
    $progress = 1.0-[Math]::Pow(1.0-$u,3)
    $points = Get-Profile ($themeIndex+1+$paletteIndex*23)
    $d = 'M ' + (($points | ForEach-Object { "$($_[0]),$($_[1])" }) -join ' L ')
    $length = 0.0
    for ($i=0;$i -lt $points.Count-1;$i++) {
        $dx=$points[$i+1][0]-$points[$i][0]; $dy=$points[$i+1][1]-$points[$i][1]
        $length += [Math]::Sqrt($dx*$dx+$dy*$dy)
    }
    $marker = Get-ProgressPoint $points $progress
    $r = 13 + 3*[Math]::Sin($t*12 + $themeIndex*0.73)
    $cameraScale = 1.08 - 0.10*$t
    $camX = [Math]::Round(28*[Math]::Sin($t*2.3+$themeIndex),2)
    $camY = [Math]::Round(-15 + 24*$t,2)
    $icon = Get-IconMarkup $theme.icon $palette.a
    $stars = [System.Text.StringBuilder]::new()
    for ($s=0;$s -lt 65;$s++) {
        $x = (37*$s + 71*$themeIndex + 19*$paletteIndex) % $Width
        $y = (53*$s + 47*$themeIndex + 29*$paletteIndex) % 390
        $rr = 0.7 + (($s*7+$themeIndex)%10)/8.0
        $alpha = 0.18 + (($s*11+$themeIndex*3)%6)/20.0
        [void]$stars.Append("<circle cx='$x' cy='$y' r='$rr' fill='#D8EEFF' opacity='$alpha'/>")
    }
    $dust = [System.Text.StringBuilder]::new()
    for ($s=0;$s -lt 100;$s++) {
        $x=(97*$s+31*$themeIndex+17*$frame)%$Width
        $y=(67*$s+23*$paletteIndex+11*$frame)%$Height
        $alpha=0.12+(($s*3+$frame)%8)/45.0
        [void]$dust.Append("<circle cx='$x' cy='$y' r='0.8' fill='#E7F4FF' opacity='$alpha'/>")
    }
    $checkpoints = [System.Text.StringBuilder]::new()
    $fractions = @(0.34,0.68,0.94)
    for ($c=0;$c -lt $fractions.Count;$c++) {
        $pos=Get-ProgressPoint $points $fractions[$c]
        if ($progress -ge $fractions[$c]-0.03) {
            $pulse=1.0+0.16*[Math]::Sin($t*15+$c*1.7+$themeIndex)
            $rad=10*$pulse
            [void]$checkpoints.Append("<circle cx='$($pos[0])' cy='$($pos[1])' r='$([Math]::Round($rad+10,2))' fill='none' stroke='#FF465F' stroke-width='3' opacity='.20'/><circle cx='$($pos[0])' cy='$($pos[1])' r='$([Math]::Round($rad,2))' fill='#FF465F' opacity='.85'/><circle cx='$($pos[0])' cy='$($pos[1])' r='3' fill='#FFF2F4'/>")
        }
    }
    $dash = [Math]::Round($length,2)
    $off = [Math]::Round($length*(1-$progress),2)
    $glowWidth = 24 + 3*[Math]::Sin($t*8+$themeIndex)
    $title = $theme.title
    $variantCode = ('V{0:000}' -f ($themeIndex*5+$paletteIndex+1))
    $svg = @"
<svg xmlns="http://www.w3.org/2000/svg" width="$Width" height="$Height" viewBox="0 0 $Width $Height">
 <defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="$($palette.bg)"/><stop offset="1" stop-color="#03050C"/></linearGradient>
  <linearGradient id="route" x1="0" y1="1" x2="1" y2="0"><stop stop-color="$($palette.b)"/><stop offset=".55" stop-color="$($palette.a)"/><stop offset="1" stop-color="#FFF3C6"/></linearGradient>
  <radialGradient id="orb"><stop stop-color="#FFFFFF"/><stop offset=".35" stop-color="$($palette.a)"/><stop offset="1" stop-color="$($palette.a)" stop-opacity="0"/></radialGradient>
  <radialGradient id="bokeh"><stop stop-color="$($palette.a)" stop-opacity=".35"/><stop offset=".45" stop-color="$($palette.b)" stop-opacity=".12"/><stop offset="1" stop-color="$($palette.b)" stop-opacity="0"/></radialGradient>
 </defs>
 <rect width="100%" height="100%" fill="url(#bg)"/>
 <g opacity=".82"><circle cx="190" cy="220" r="110" fill="url(#bokeh)"/><circle cx="1080" cy="310" r="145" fill="url(#bokeh)"/></g>
 <g>$($stars.ToString())</g>
 <path d="M0 606 Q220 488 438 594 T870 582 T1280 540 V720 H0Z" fill="$($palette.b)" opacity=".045"/>
 <g transform="translate($([Math]::Round($Width/2+$camX,2)) $([Math]::Round($Height/2+$camY,2))) scale($([Math]::Round($cameraScale,4))) translate(-$([Math]::Round($Width/2,2)) -$([Math]::Round($Height/2,2)))">
  <g transform="translate(640 244) rotate($([Math]::Round(2*[Math]::Sin($t*3+$themeIndex),2))) scale(9.0) translate(-12 -12)" opacity=".92">$icon</g>
  <circle cx="640" cy="244" r="154" fill="none" stroke="$($palette.a)" stroke-width="1" opacity=".15"/>
  <circle cx="640" cy="244" r="174" fill="none" stroke="$($palette.b)" stroke-width="1" stroke-dasharray="4 12" opacity=".22" transform="rotate($([Math]::Round(360*$t,1)) 640 244)"/>
  <path d="$d" pathLength="$dash" fill="none" stroke="$($palette.a)" stroke-width="$glowWidth" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="$dash" stroke-dashoffset="$off" opacity=".13"/>
  <path d="$d" pathLength="$dash" fill="none" stroke="$($palette.a)" stroke-width="15" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="$dash" stroke-dashoffset="$off" opacity=".20"/>
  <path d="$d" pathLength="$dash" fill="none" stroke="url(#route)" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="$dash" stroke-dashoffset="$off" opacity=".94"/>
  <path d="$d" pathLength="$dash" fill="none" stroke="#FFF9EA" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="$dash" stroke-dashoffset="$off" opacity=".92"/>
  $($checkpoints.ToString())
  <circle cx="$($marker[0])" cy="$($marker[1])" r="31" fill="url(#orb)" opacity=".72"/>
  <circle cx="$($marker[0])" cy="$($marker[1])" r="22" fill="url(#orb)" opacity=".88"/>
  <circle cx="$($marker[0])" cy="$($marker[1])" r="$([Math]::Round($r,2))" fill="#FFF3B8" stroke="$($palette.a)" stroke-width="3"/>
  <circle cx="$($marker[0])" cy="$($marker[1])" r="3.4" fill="#FFFFFF"/>
 </g>
 <g opacity=".40"><circle cx="110" cy="654" r="34" fill="url(#bokeh)"/><circle cx="1160" cy="116" r="27" fill="url(#bokeh)"/></g>
 <g>$($dust.ToString())</g>
 <text x="62" y="78" fill="#F4F6FF" font-family="Arial,sans-serif" font-size="22" font-weight="700" letter-spacing="5" opacity=".88">$title</text>
 <text x="64" y="108" fill="$($palette.a)" font-family="Arial,sans-serif" font-size="12" font-weight="600" letter-spacing="4" opacity=".78">VECTOR STUDY  /  $variantCode</text>
 <text x="1218" y="78" fill="#E5ECF9" font-family="Arial,sans-serif" font-size="13" text-anchor="end" letter-spacing="3" opacity=".56">CHRONON / FIELD NOTES</text>
 <path d="M62 628H1218" stroke="#B7C6DE" stroke-width="1" opacity=".22"/>
 <path d="M62 628H$([Math]::Round(62+1156*$progress,1))" stroke="$($palette.a)" stroke-width="2.5" opacity=".82"/>
 <text x="62" y="665" fill="#DDE7F7" font-family="Arial,sans-serif" font-size="12" letter-spacing="3" opacity=".58">TRIM PATH  |  FOLLOW PATH  |  GLOW  |  CAMERA  |  DOF  |  FILM GRAIN</text>
 <text x="1218" y="665" fill="#DDE7F7" font-family="Arial,sans-serif" font-size="12" text-anchor="end" letter-spacing="2" opacity=".72">$([Math]::Round($t*100,0))%</text>
</svg>
"@
    return $svg
}

$variationRecords = [System.Collections.Generic.List[object]]::new()
$previewFiles = [System.Collections.Generic.List[string]]::new()
for ($i=0; $i -lt 20; $i++) {
    for ($p=0; $p -lt 5; $p++) {
        $idx=$i*5+$p+1
        if (-not $SkipFinalArtifacts) {
            $svg=New-SceneSvg $i $p 0 $true
            $file=Join-Path $previewDir ('variation_{0:000}.svg' -f $idx)
            [System.IO.File]::WriteAllText($file,$svg,[System.Text.UTF8Encoding]::new($false))
            $previewFiles.Add($file)
        }
        $variationRecords.Add([pscustomobject]@{
            variation=$idx; theme=$themes[$i].id; vector="lucide-$($themes[$i].icon).svg";
            palette=$palettes[$p].name; primitives=@('svg_path','trim_path','follow_path','gradient','inner_glow','rim_light','bloom','checkpoint_pulse','camera_dolly','depth_of_field','deterministic_dust','layer_compositing')
        })
    }
}
$manifest = [ordered]@{
    title='Chronon SVG Primitive Animation Collection'; created_utc=(Get-Date).ToUniversalTime().ToString('o');
    output_format=[ordered]@{width=$Width;height=$Height;fps=$Fps;source_fps=$Fps;seconds=$Seconds;codec='H.264 NVENC / yuv420p';gpu='NVIDIA NVENC'};
    vector_sources=@(
        [ordered]@{name='Wikimedia Mountains';file='assets/downloaded_vectors/Wikimedia_Mountains.svg';source='https://commons.wikimedia.org/wiki/File:Mountains.svg';license='Public domain';author='Herzi Pinki';used_by_clips=$false},
        [ordered]@{name='Lucide';source='https://github.com/lucide-icons/lucide';api='https://api.iconify.design/lucide/{icon}.svg';license='ISC';attribution='Lucide contributors';used_by_clips=$true}
    );
    clips=@(); variations=$variationRecords
}

for ($i=0; $i -lt 20; $i++) {
    for ($p=0; $p -lt 5; $p++) {
        $variationIndex=$i*5+$p+1
        if ($variationIndex -lt $StartVariation -or $variationIndex -gt $EndVariation) { continue }
        $theme=$themes[$i]
        $palette=$palettes[$p]
        $name=('{0:000}_{1}_{2}.mp4' -f $variationIndex,$theme.id,$palette.name)
        $mp4=Join-Path $out $name
        $clipDir=Join-Path $svgWork ('clip_{0:000}' -f $variationIndex)
        $primitives=$variationRecords[$variationIndex-1].primitives
        if ($Resume -and (Test-Path $mp4)) {
            $manifest.clips += [pscustomobject]@{variation=$variationIndex;id=$theme.id;file=$name;vector="lucide-$($theme.icon).svg";palette=$palette.name;source_frames=($Fps*$Seconds);source_fps=$Fps;output_frames=($Fps*$Seconds);fps=$Fps;width=$Width;height=$Height;encoder='h264_nvenc';primitives=$primitives}
            Write-Host ("Already rendered {0}/100: {1}" -f $variationIndex,$name)
            continue
        }
        if (Test-Path $clipDir) { Remove-Item -LiteralPath $clipDir -Recurse -Force }
        New-Item -ItemType Directory -Force -Path $clipDir | Out-Null
        $frameCount=$Fps*$Seconds
        for ($f=0;$f -lt $frameCount;$f++) {
            $svg=New-SceneSvg $i $p $f
            $file=Join-Path $clipDir ('frame_{0:0000}.svg' -f $f)
            [System.IO.File]::WriteAllText($file,$svg,[System.Text.UTF8Encoding]::new($false))
        }
        $magickArgs=@('-limit','memory','256MiB','-limit','map','512MiB')
        $svgFrames=Get-ChildItem $clipDir -Filter '*.svg' | Sort-Object Name
        Push-Location $clipDir
        foreach ($svgFrame in $svgFrames) {
            $pngPath=$svgFrame.BaseName + '.png'
            $magickArgs+=@('-density','96',$svgFrame.Name,'-background','black','-alpha','remove','-alpha','off','-resize',"${Width}x${Height}!",'-write',$pngPath,'+delete')
        }
        $magickArgs+='null:'
        & $magick @magickArgs
        Pop-Location
        if ($LASTEXITCODE -ne 0) { throw "ImageMagick SVG render failed for $name" }
        $accent='0x'+$palette.a.Substring(1)
        $videoFilter="drawbox=x=948:y=48:w=280:h=44:color=0x07131E:t=fill,drawbox=x=948:y=48:w=3:h=44:color=${accent}:t=fill,drawtext=fontfile='C\:/Windows/Fonts/arial.ttf':text='CHRONON / FIELD NOTES':fontcolor=0xE5ECF9:fontsize=13:x=965:y=66"
        & $ffmpeg -hide_banner -loglevel error -y -framerate $Fps -i (Join-Path $clipDir 'frame_%04d.png') -vf $videoFilter -t $Seconds -r $Fps -c:v h264_nvenc -preset p5 -tune hq -rc vbr -cq 17 -b:v 0 -pix_fmt yuv420p -movflags +faststart $mp4
        if ($LASTEXITCODE -ne 0) { throw "FFmpeg encoding failed for $name" }
        $manifest.clips += [pscustomobject]@{variation=$variationIndex;id=$theme.id;file=$name;vector="lucide-$($theme.icon).svg";palette=$palette.name;source_frames=$frameCount;source_fps=$Fps;output_frames=$frameCount;fps=$Fps;width=$Width;height=$Height;encoder='h264_nvenc';primitives=$primitives}
        Write-Host ("Rendered {0}/100: {1}" -f $variationIndex,$name)
        Remove-Item -LiteralPath $clipDir -Recurse -Force
    }
}

if ($SkipFinalArtifacts) {
    $partPath=Join-Path $out ('manifest_part_{0:000}_{1:000}.json' -f $StartVariation,$EndVariation)
    $manifest | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 $partPath
    Write-Host "Rendered range $StartVariation-$EndVariation."
    return
}

$manifestPath=Join-Path $out 'manifest.json'
$manifest | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 $manifestPath
$previewPngs = foreach ($f in $previewFiles) { [System.IO.Path]::ChangeExtension($f,'.png') }
$previewArgs=@('-limit','memory','256MiB','-limit','map','512MiB')
Push-Location $previewDir
for ($p=0;$p -lt $previewFiles.Count;$p++) {
    $previewArgs+=@('-density','96',(Split-Path -Leaf $previewFiles[$p]),'-background','black','-alpha','remove','-alpha','off','-resize','320x180!','-write',(Split-Path -Leaf $previewPngs[$p]),'+delete')
}
$previewArgs+='null:'
& $magick @previewArgs
Pop-Location
if ($LASTEXITCODE -ne 0) { throw 'Rendering the 100 variation preview cards failed.' }
& $magick montage @previewPngs -tile 10x10 -geometry 320x180+3+3 -background '#050812' (Join-Path $out 'contact_sheet_100_variations.jpg')
if ($LASTEXITCODE -ne 0) { throw 'Building the 100 variation contact sheet failed.' }
Remove-Item -LiteralPath $svgWork -Recurse -Force
Get-ChildItem $out -Filter 'manifest_part_*.json' -ErrorAction SilentlyContinue | Remove-Item -Force
Write-Host "Collection complete: $out"
