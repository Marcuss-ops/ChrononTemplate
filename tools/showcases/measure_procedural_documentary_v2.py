#!/usr/bin/env python3
"""Measure decoded certification videos; metrics are observations, not aesthetic gates."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np


def decoded_sample(video: Path, frame: int, width=480, height=270) -> np.ndarray:
    result = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(video), '-vf',
        f'select=eq(n\\,{frame}),scale={width}:{height}', '-frames:v', '1',
        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True)
    if len(result.stdout) != width * height * 3:
        raise RuntimeError(f'Cannot decode frame {frame}: {video}')
    return np.frombuffer(result.stdout, dtype=np.uint8).reshape(height, width, 3).astype(np.float32)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    args = parser.parse_args()
    metrics = {'quality_status': 'PARTIAL', 'note': 'Measurements do not certify absence of banding, tiling or artistic defects.',
               'videos': {}}
    for plan in sorted(args.out.glob('*.plan.json')):
        name = plan.name.removesuffix('.plan.json')
        video = args.out / f'{name}.mp4'
        if not video.exists():
            metrics['videos'][name] = {'status': 'NOT RUN'}
            continue
        try:
            samples = [decoded_sample(video, i) for i in (0, 74, 75, 76, 149)]
            luminance = [a @ np.array([.2126, .7152, .0722], dtype=np.float32) for a in samples]
            adjacent = [float(np.abs(luminance[i + 1] - luminance[i]).mean()) for i in (1, 2)]
            row = {'status': 'MEASURED', 'mean_luminance': [float(a.mean()) for a in luminance],
                   'luminance_stddev': [float(a.std()) for a in luminance],
                   'adjacent_mean_absolute_difference': adjacent,
                   'first_last_difference': float(np.abs(luminance[0] - luminance[-1]).mean()),
                   'dark_pixel_fraction': float((luminance[2] < 2).mean()),
                   'sha256': hashlib.sha256(video.read_bytes()).hexdigest()}
            sidecar = args.out / f'{name}.mp4.timing.json'
            if sidecar.exists():
                timing = json.loads(sidecar.read_text())
                row['renderer_timing'] = {k: timing[k] for k in ('render_ms', 'wall_time_ms', 'memory', 'job') if k in timing}
            metrics['videos'][name] = row
        except (subprocess.CalledProcessError, RuntimeError, OSError, ValueError) as exc:
            metrics['videos'][name] = {'status': 'FAIL', 'error': str(exc)}
        (args.out / 'quality-metrics.json').write_text(json.dumps(metrics, indent=2) + '\n')
    (args.out / 'quality-metrics.json').write_text(json.dumps(metrics, indent=2) + '\n')
    if any(v['status'] in ('NOT RUN', 'FAIL') for v in metrics['videos'].values()):
        raise SystemExit('Quality measurements incomplete; see quality-metrics.json')


if __name__ == '__main__':
    main()
