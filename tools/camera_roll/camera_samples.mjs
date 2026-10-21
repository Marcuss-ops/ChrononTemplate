import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');

export function resolveCameraSamples(camera, channels, fps, frameCount) {
  const buildDir = path.resolve(process.env.CHRONONTEMPLATE_BUILD_DIR ?? path.join(ROOT, 'build/dev'));
  const executable = path.join(buildDir, 'chronontemplate_resolve_camera_samples');
  if (!fs.existsSync(executable)) {
    throw new Error(`Build chronontemplate_resolve_camera_samples first: ${executable}`);
  }
  const request = JSON.stringify({camera, channels, fps, frame_count: frameCount});
  const output = execFileSync(executable, [], {cwd: ROOT, input: request, encoding: 'utf8'});
  const samples = JSON.parse(output);
  if (samples.length !== frameCount || samples.some((sample, frame) => sample.frame !== frame)) {
    throw new Error('CM3D returned an incomplete or unordered camera sample sequence');
  }
  return samples;
}
