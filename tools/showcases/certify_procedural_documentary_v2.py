#!/usr/bin/env python3
"""Certify C++-authored RenderPlans through the canonical Chronon3D CLI.

Serial rendering, bounded CPU thread budgets and an available-memory admission
check avoid competing full-frame renders. GPU-native rejection is not a pass.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]


def available_memory() -> int:
    for line in Path('/proc/meminfo').read_text().splitlines():
        if line.startswith('MemAvailable:'):
            return int(line.split()[1]) * 1024
    raise RuntimeError('Cannot determine available memory')


def execute(command: list[str], log: Path) -> float:
    if available_memory() < 4 * 1024**3:
        raise RuntimeError('Render admission rejected: less than 4 GiB available')
    env = dict(os.environ, OMP_NUM_THREADS='4', OPENBLAS_NUM_THREADS='1',
               CHRONON3D_CPU_RENDER_THREADS='4', CHRONON3D_CPU_DECODE_THREADS='1',
               CHRONON3D_CPU_ENCODE_THREADS='2')
    started = time.perf_counter()
    with log.open('w') as output:
        result = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT, env=env)
    if result.returncode:
        raise RuntimeError(f'{command[0]} failed ({result.returncode}); see {log}')
    return time.perf_counter() - started


def probe_video(path: Path) -> dict:
    result = subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height,avg_frame_rate,nb_read_frames,duration',
        '-of', 'json', str(path)], check=True, capture_output=True, text=True)
    stream = json.loads(result.stdout)['streams'][0]
    if (stream['width'], stream['height'], stream['avg_frame_rate'], int(stream['nb_read_frames'])) != (1920, 1080, '30/1', 150):
        raise RuntimeError(f'Video dimensions/rate/frame count mismatch: {path}: {stream}')
    if abs(float(stream['duration']) - 5.0) > .001:
        raise RuntimeError(f'Video duration mismatch: {path}: {stream}')
    return stream


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cli', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=ROOT / 'ChrononTemplate/out/procedural_documentary_v2')
    parser.add_argument('--backend', choices=['software', 'vulkan'], default='vulkan')
    parser.add_argument('--native', action='store_true', help='Fail if strict GPU-native admission rejects a plan')
    parser.add_argument('--frames-only', action='store_true')
    parser.add_argument('--resume', action='store_true', help='Reuse only hash-matching, already verified artifacts')
    parser.add_argument('--only', nargs='+', help='Certify selected names from the complete emitted suite')
    args = parser.parse_args()
    plans = sorted(args.out.glob('*.plan.json'))
    if len(plans) != 17:
        raise RuntimeError(f'Expected 17 native plans, found {len(plans)}')
    if args.only:
        known = {p.name.removesuffix('.plan.json') for p in plans}
        if not set(args.only) <= known:
            parser.error('--only contains an unknown composition')
        plans = [p for p in plans if p.name.removesuffix('.plan.json') in args.only]
    metrics_path = args.out / f'metrics-{args.backend}{"-native" if args.native else ""}.json'
    previous = json.loads(metrics_path.read_text()) if args.resume and metrics_path.exists() else {}
    metrics = {'backend': args.backend, 'strict_gpu_native': args.native,
               'frames_only': args.frames_only, 'artifacts': {}}
    failures = []
    for plan in plans:
        name = plan.name.removesuffix('.plan.json')
        plan_sha = hashlib.sha256(plan.read_bytes()).hexdigest()
        old = previous.get('artifacts', {}).get(name, {})
        if (old.get('status') == 'PASS' and old.get('plan_sha256') == plan_sha
                and previous.get('frames_only') == args.frames_only):
            if not args.frames_only:
                probe_video(args.out / f'{name}.mp4')
            metrics['artifacts'][name] = old
            print(f'{name}: PASS (verified resume)', flush=True)
            continue
        record = {'status': 'NOT RUN', 'plan_sha256': plan_sha}
        metrics['artifacts'][name] = record
        common = [str(args.cli.resolve()), 'render', '--assets-root', str(ROOT), '--plan', str(plan.resolve()),
                  '--backend', args.backend, '-v', 'warn']
        if args.native:
            common += ['--gpu-hot-path-mode', 'require_gpu_native']
        try:
            golden = args.out / f'{name}.{args.backend}.golden.png'
            repeated = args.out / f'{name}.{args.backend}.repeat.png'
            # The CLI explicitly declares still-PNG output not pixel-truth.
            # Use the actual video executor and decode its single-frame output.
            for label, image in [('golden', golden), ('repeat', repeated)]:
                sample = args.out / f'{name}.{args.backend}.{label}.mp4'
                record[f'{label}_seconds'] = execute(common + ['--start-frame', '75', '--end-frame', '75',
                    '-o', str(sample.resolve()), '--ffmpeg-mode', 'pipe'],
                    args.out / f'{name}.{args.backend}.{label}.log')
                subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(sample), '-frames:v', '1',
                                str(image)], check=True)
            a = hashlib.sha256(golden.read_bytes()).hexdigest()
            b = hashlib.sha256(repeated.read_bytes()).hexdigest()
            if a != b:
                raise RuntimeError('Same seed/frame/backend golden hashes differ')
            record['golden_sha256'] = a
            record['determinism'] = 'PASS'
            if not args.frames_only:
                video = args.out / f'{name}.mp4'
                record['video_seconds'] = execute(common + ['-o', str(video.resolve()), '--ffmpeg-mode', 'pipe'],
                                                  args.out / f'{name}.{args.backend}.video.log')
                record['video'] = probe_video(video)
            if hashlib.sha256(plan.read_bytes()).hexdigest() != plan_sha:
                raise RuntimeError('Plan changed during certification; rerun the affected artifact')
            record['status'] = 'PASS'
        except (RuntimeError, subprocess.CalledProcessError, OSError, ValueError, KeyError) as exc:
            record.update(status='FAIL', error=str(exc))
            failures.append(name)
        metrics_path.write_text(json.dumps(metrics, indent=2) + '\n')
        print(f'{name}: {record["status"]}', flush=True)
    metrics_path.write_text(json.dumps(metrics, indent=2) + '\n')
    if failures:
        raise SystemExit(f'Certification failed: {", ".join(failures)}')


if __name__ == '__main__':
    main()
