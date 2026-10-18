import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const root = path.resolve(import.meta.dirname, '../..');
const out = path.join(root, 'out/nba_rivalry/nba_rivalry_timeline_10.plan.json');
const frames = 600;
const fps = 30;
const last = frames - 1;
const cameraTravel = 840;
const cameraX = (frame) => cameraTravel * frame / last;
const angles = [
  [0, 0], [58, 8], [116, -7], [174, 10], [232, -8],
  [290, 8], [348, -10], [406, 8], [464, -8], [522, 10],
  [560, 13], [580, 22], [599, 24],
];
const angleAt = (frame) => {
  const next = angles.find(([at]) => at >= frame) ?? angles.at(-1);
  const previous = angles.filter(([at]) => at < frame).at(-1) ?? angles[0];
  const t = (frame - previous[0]) / (next[0] - previous[0] || 1);
  return previous[1] + (next[1] - previous[1]) * t;
};
const cameraComp = (frame) => 1080 * Math.tan(angleAt(frame) * Math.PI / 180);
const track = (property, keyframes, easing = 'linear') => ({
  property, easing,
  keyframes: keyframes.map(([frame, value]) => ({ frame, value })),
});

const players = [
  { id: 'paul_pierce', name: 'Paul Pierce', photo: 'assets/nba_rivalry/web/paul_pierce_2008.jpg' },
  { id: 'lebron_james', name: 'LeBron James', photo: 'assets/nba_rivalry/web/lebron_heat_2011.jpg' },
  { id: 'kevin_garnett', name: 'Kevin Garnett', photo: 'assets/nba_rivalry/players/kevin_garnett.jpg' },
  { id: 'dwyane_wade', name: 'Dwyane Wade', photo: 'assets/nba_rivalry/players/dwyane_wade.jpg' },
  { id: 'ray_allen', name: 'Ray Allen', photo: 'assets/nba_rivalry/players/ray_allen.jpg' },
  { id: 'chris_bosh', name: 'Chris Bosh', photo: 'assets/nba_rivalry/players/chris_bosh.jpg' },
  { id: 'rajon_rondo', name: 'Rajon Rondo', photo: 'assets/nba_rivalry/players/rajon_rondo.jpg' },
  { id: 'udonis_haslem', name: 'Udonis Haslem', photo: 'assets/nba_rivalry/players/udonis_haslem.jpg' },
  { id: 'kendrick_perkins', name: 'Kendrick Perkins', photo: 'assets/nba_rivalry/players/kendrick_perkins.jpg' },
  { id: 'shane_battier', name: 'Shane Battier', photo: 'assets/nba_rivalry/players/shane_battier.jpg' },
];
const cardsDir = path.join(root, 'assets/nba_rivalry/cards');
fs.mkdirSync(cardsDir, { recursive: true });
const fontPath = path.join(root, 'assets/nba_rivalry/web/DejaVuSans-Bold.ttf');
for (const player of players) {
  const photoPath = path.join(root, player.photo);
  const cardPath = path.join(cardsDir, `${player.id}.png`);
  const filters = [
    '[0:v]scale=534:665:force_original_aspect_ratio=increase,crop=534:665,setsar=1,eq=contrast=0.97:saturation=0.84[photo]',
    'color=c=0x594735:s=590x790:r=1:d=1[edge]',
    'color=c=0xf0e8d8:s=574x774:r=1:d=1[mat]',
    '[edge][mat]overlay=8:8[back]',
    `[back][photo]overlay=28:28,drawtext=fontfile=${fontPath}:text='${player.name}':fontcolor=0x33291f:fontsize=30:x=(w-text_w)/2:y=716:shadowcolor=0xe7dcc9:shadowx=1:shadowy=1,format=rgb24[out]`,
  ].join(';');
  execFileSync('ffmpeg', [
    '-hide_banner', '-loglevel', 'error', '-y', '-i', photoPath,
    '-f', 'lavfi', '-i', 'color=c=0x594735:s=590x790:r=1:d=1',
    '-f', 'lavfi', '-i', 'color=c=0xf0e8d8:s=574x774:r=1:d=1',
    '-filter_complex', filters, '-map', '[out]', '-frames:v', '1', cardPath,
  ], { stdio: 'inherit' });
}
const layers = [{
  id: 'blurred_corkboard', type: 'image', asset: 'assets/nba_rivalry/web/corkboard_bg_softblur.png',
  position: [0, 0], size: [1920, 1080], fit: 'cover', screen_space: true,
  start_frame: 0, duration_frames: frames,
}];

players.forEach((player, index) => {
  const reveal = index * 58;
  const stackX = index * 7;
  const stackY = -index * 5;
  const z = 80 - index * 5;
  const xKeys = [
    ...(reveal > 0 ? [[0, cameraX(0) - 620], [reveal, cameraX(reveal) - 620]] : [[0, cameraX(0) - 620]]),
    [reveal + 10, cameraX(reveal + 10) + stackX + cameraComp(reveal + 10)],
    ...angles.filter(([frame]) => frame > reveal + 10 && frame < last)
      .map(([frame]) => [frame, cameraX(frame) + stackX + cameraComp(frame)]),
    [last, cameraX(last) + stackX + cameraComp(last)],
  ];
  const opacity = [[0, 0], [Math.max(0, reveal + 3), 0], [reveal + 11, 1], [last, 1]];
  const animation = () => ({ tracks: [
    track('position_x', xKeys),
    track('opacity', opacity),
  ] });
  layers.push({
    id: `${player.id}_card`, type: 'image', asset: `assets/nba_rivalry/cards/${player.id}.png`,
    position: [0, stackY, z], size: [590, 790], fit: 'contain', enable_3d: true,
    start_frame: 0, duration_frames: frames,
    animation: animation(),
  });
});

const plan = {
  schema: 'chronon.render-plan.v3', version: 3,
  job_id: 'nba_rivalry_timeline_10_native',
  canvas: { width: 1920, height: 1080, fps_num: fps, fps_den: 1, duration_frames: frames },
  output: { path: 'NBA_Rivalry_10_Players_Chronon_Timeline.mp4', format: 'mp4', codec: 'h264' },
  camera: {
    type: 'perspective', position: [0, 0, -1080], rotation_deg: [0, 0, 0],
    fov_deg: 53.14, near: 0.1, far: 10000, zoom: 1,
  },
  camera_animation: {
    tracks: [
      track('camera_position_x', [[0, 0], [last, cameraTravel]]),
      track('camera_rotation_y', angles),
      track('camera_rotation_x', [[0, 0], [116, -2], [232, 2], [348, -2], [464, 2], [560, 0], [599, 0]]),
    ],
  },
  layers,
};
fs.writeFileSync(out, `${JSON.stringify(plan, null, 2)}\n`);
console.log(`Wrote ${out} (${players.length} player cards, ${frames} frames)`);
