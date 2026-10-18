import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '../..');
const out = path.join(root, 'out/nba_rivalry/nba_rivalry_precomp_2.plan.json');
const duration = 240;

const track = (property, keyframes, easing = 'in_out_cubic') => ({
  property,
  easing,
  keyframes: keyframes.map(([frame, value]) => ({ frame, value })),
});

const positionTracks = (from, to, join = 132) => [
  track('position_x', [[0, from[0]], [join, to[0]], [duration - 1, to[0]]]),
  track('position_y', [[0, from[1]], [join, to[1]], [duration - 1, to[1]]]),
];

const photoGroup = ({ id, asset, side, z, top, isTop }) => {
  const start = side < 0 ? [-508, 22, z] : [508, 22, z];
  const end = isTop ? [18, 28, z] : [-12, 42, z];
  const pinOpacity = isTop
    ? [[0, 0], [10, 0.82], [duration - 1, 0.82]]
    : [[0, 0], [10, 0.82], [120, 0.82], [132, 0], [duration - 1, 0]];
  const group = [
    {
      id: `${id}_matte`, type: 'image', asset: 'assets/nba_rivalry/web/photo_matte.png',
      fit: 'contain', size: [544, 694],
      position: [0, 0, z], enable_3d: true,
      start_frame: 0, duration_frames: duration,
      animation: { tracks: positionTracks(start, end) },
    },
    {
      id: `${id}_photo`, type: 'image', asset,
      position: [0, 0, z - 1], size: [520, 670], fit: 'cover', enable_3d: true,
      start_frame: 0, duration_frames: duration,
      animation: { tracks: positionTracks(start, [end[0], end[1], end[2] - 1]) },
    },
    {
      id: `${id}_pin`, type: 'image', asset: 'assets/nba_rivalry/web/red_pushpin.png',
      position: [0, 0, 0], size: [64, 56], fit: 'contain', enable_3d: true,
      start_frame: 0, duration_frames: duration,
      animation: {
        tracks: [
          track('position_x', [[0, start[0]], [22, start[0]], [40, start[0]], [120, start[0]], [132, end[0]], [duration - 1, end[0]]], 'out_cubic'),
          track('position_y', [[0, 720], [22, 720], [40, 325 - start[1]], [120, 325 - start[1]], [132, 325 - end[1]], [duration - 1, 325 - end[1]]], 'out_cubic'),
          track('position_z', [[0, start[2] - 24], [22, start[2] - 24], [40, start[2] - 24], [120, start[2] - 24], [132, end[2] - 24], [duration - 1, end[2] - 24]], 'out_cubic'),
          track('opacity', pinOpacity, 'linear'),
        ],
      },
    },
  ];
  return group;
};

const plan = {
  schema: 'chronon.render-plan.v3',
  version: 3,
  job_id: 'nba_rivalry_precomp_camera_2_0',
  canvas: { width: 1920, height: 1080, fps_num: 30, fps_den: 1, duration_frames: duration },
  output: { path: 'NBA_Rivalry_Chronon_Recreation_2.0.mp4', format: 'mp4', codec: 'h264' },
  camera: {
    type: 'perspective', position: [0, 0, -1080], rotation_deg: [0, 0, 0],
    fov_deg: 53.14, near: 0.1, far: 10000, zoom: 1,
  },
  camera_animation: {
    tracks: [
      track('camera_rotation_y', [[0, 0], [150, 0], [205, 42], [239, 52]]),
      track('camera_position_x', [[0, 0], [150, 0], [205, -723], [239, -851]]),
      track('camera_position_z', [[0, -1080], [150, -1080], [205, -802], [239, -665]]),
    ],
  },
  layers: [
    {
      id: 'corkboard', type: 'image', asset: 'assets/nba_rivalry/web/corkboard_bg.png',
      position: [0, 0], size: [1920, 1080], fit: 'cover', screen_space: true,
      start_frame: 0, duration_frames: duration,
    },
    ...photoGroup({ id: 'pierce', asset: 'assets/nba_rivalry/web/paul_pierce_2008.jpg', side: -1, z: 55, isTop: false }),
    ...photoGroup({ id: 'lebron', asset: 'assets/nba_rivalry/web/lebron_heat_2011.jpg', side: 1, z: 0, isTop: true }),
  ],
};

fs.writeFileSync(out, `${JSON.stringify(plan, null, 2)}\n`);
console.log(`Wrote ${out}`);
