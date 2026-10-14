#!/usr/bin/env python3
"""Tests for Documentary Phrase Highlighting 3.0 plan authoring."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

MODULE=Path(__file__).with_name('documentary_phrase_highlighting_v3.py')
spec=importlib.util.spec_from_file_location('documentary_phrase_highlighting_v3',MODULE)
MOD=importlib.util.module_from_spec(spec); spec.loader.exec_module(MOD)

class DocumentaryPhraseV3Tests(unittest.TestCase):
 def test_ten_presets_have_paired_six_second_full_hd_plans(self):
  self.assertEqual(len(MOD.PRESETS),10)
  plans=[MOD.build(p,b) for p in MOD.PRESETS for b in ('dark','ivory')]
  self.assertEqual(len(plans),20)
  self.assertEqual(len({p['job_id'] for p in plans}),20)
  for p in plans:
   with self.subTest(job=p['job_id']):
    self.assertEqual(p['canvas'],{'width':1920,'height':1080,'fps_num':30,'fps_den':1,'duration_frames':180})
    self.assertEqual(p['output']['codec'],'h264')
    self.assertTrue(any(x.get('type')=='text' and x.get('text','').strip() for x in p['layers']))
 def test_authoring_is_deterministic_and_output_names_match(self):
  for p in MOD.PRESETS:
   for bg in ('dark','ivory'):
    self.assertEqual(MOD.build(p,bg),MOD.build(p,bg))
    plan=MOD.build(p,bg)
    self.assertEqual(plan['output']['path'],plan['job_id']+'.mp4')
 def test_all_semantic_span_targets_are_exact_utf8_ranges(self):
  for preset in MOD.PRESETS:
   for bg in ('dark','ivory'):
    plan=MOD.build(preset,bg)
    for layer in plan['layers']:
     raw=layer.get('text','').encode('utf-8')
     ids=set()
     for span in layer.get('spans',[]):
      self.assertGreaterEqual(span['start'],0); self.assertGreater(span['end'],span['start']); self.assertLessEqual(span['end'],len(raw))
      raw[span['start']:span['end']].decode('utf-8')
      self.assertNotIn(span['semantic_id'],ids); ids.add(span['semantic_id'])
 def test_focus_uses_native_semantic_selectors_and_temporal_phrase_highlights(self):
  focus=MOD.build(MOD.PRESETS[4],'dark')
  layer=next(x for x in focus['layers'] if x.get('id')=='phrase-1')
  animators=layer['text_animators']
  self.assertEqual(len(animators),4)
  self.assertTrue(all(a['selectors'][0]['semantic_id'] in {s['semantic_id'] for s in layer['spans']} for a in animators))
  sequence=MOD.build(MOD.PRESETS[8],'dark')
  final=next(x for x in sequence['layers'] if x.get('id')=='phrase-3')
  self.assertEqual(final['start_frame'],92)
  self.assertEqual(final['text_animators'][0]['properties'][0]['keyframes'][1]['frame'],120)
  self.assertEqual(final['text_animators'][0]['properties'][0]['keyframes'][1]['value'][3],0)
  self.assertGreater(final['text_animators'][0]['properties'][0]['keyframes'][2]['value'][3],0)
 def test_connectors_are_trimmed_native_paths_with_variable_stroke_range(self):
  plan=MOD.build(MOD.PRESETS[2],'dark')
  paths=[l for l in plan['layers'] if l.get('shape',{}).get('type')=='path']
  self.assertGreaterEqual(len(paths),1)
  for layer in paths:
   self.assertNotIn('fill',layer['shape'])
   self.assertGreaterEqual(layer['shape']['stroke']['width'],.75)
   self.assertLessEqual(layer['shape']['stroke']['width'],6)
   self.assertEqual(layer['shape']['operators'][0]['kind'],'trim')
   self.assertEqual(layer['shape']['path'][0]['type'],'move_to')
 def test_emit_writes_only_twenty_plans_before_render(self):
  with tempfile.TemporaryDirectory() as d:
   paths=MOD.emit(Path(d))
   self.assertEqual(len(paths),20)
   self.assertEqual(len(list(Path(d).glob('*.plan.json'))),20)
   self.assertEqual(len(list(Path(d).glob('*.mp4'))),0)
   for path in paths:
    self.assertEqual(json.loads(path.read_text())['canvas']['duration_frames'],180)

 def test_corrected_master_uses_explicit_canvas_space_for_native_paths(self):
  for bg in ('dark','ivory'):
   plan=MOD.build_master(bg)
   self.assertEqual(plan['canvas']['duration_frames'],180)
   paths=[layer for layer in plan['layers'] if layer.get('shape',{}).get('type')=='path']
   self.assertEqual(len(paths),6)
   self.assertTrue(all(layer.get('screen_space') is True for layer in paths))
   self.assertTrue(all(layer['position']==[0,0] for layer in paths))
   self.assertEqual({layer['id'] for layer in paths}, {
    'highlight-missing','highlight-witness','highlight-report',
    'connector-1','connector-2','connector-3'})
   for layer in paths:
    # Open corrected-master strokes explicitly disable the default opaque fill;
    # otherwise Vulkan native promotion rejects them and drops the ink.
    self.assertEqual(layer['shape']['fill'],[0.0,0.0,0.0,0.0],layer['id'])
    if layer['id'].startswith('connector-'):
     points=[command['point'] for command in layer['shape']['path'] if command['type']!='close']
     xs=[point[0]+MOD.W/2 for point in points]; ys=[point[1]+MOD.H/2 for point in points]
     self.assertGreaterEqual(min(xs),150); self.assertLessEqual(max(xs),MOD.W-150)
     self.assertGreaterEqual(min(ys),150); self.assertLessEqual(max(ys),MOD.H-150)
    commands=layer['shape']['path']
    self.assertGreaterEqual(len(commands),2)
    self.assertEqual(commands[0]['type'],'move_to')
    self.assertTrue(all(len(command['point'])==2 for command in commands if command['type']!='close'))
   self.assertEqual(plan['output']['path'],'documentary_phrase_master_corrected.mp4')
   for layer in paths:
    canvas_points=[(command['point'][0]+MOD.W/2,command['point'][1]+MOD.H/2)
                   for command in layer['shape']['path'] if command['type']!='close']
    self.assertTrue(all(0<=x<=MOD.W and 0<=y<=MOD.H for x,y in canvas_points),layer['id'])

 def test_master_highlights_are_drawn_after_their_target_text_and_trimmed(self):
  plan=MOD.build_master('dark')
  ids=[layer['id'] for layer in plan['layers']]
  for target,highlight in [('title','highlight-missing'),('witness','highlight-witness'),('report','highlight-report')]:
   self.assertLess(ids.index(target),ids.index(highlight))
   layer=next(item for item in plan['layers'] if item['id']==highlight)
   trim=layer['shape']['operators'][0]
   self.assertEqual(trim['kind'],'trim')
   keys=trim['params']['animation']['keyframes']
   self.assertEqual(keys[0]['value'][1],0)
   self.assertEqual(keys[-1]['value'][1],1)

 def test_acceptance_gate_rejects_a_video_without_required_stream(self):
  with tempfile.TemporaryDirectory() as d:
   video=Path(d)/'empty.mp4'; video.write_bytes(b'not a video')
   with self.assertRaises(Exception):
    MOD.verify_master(video,MOD.build_master('dark'),'dark',Path(d)/'report',
                      ffprobe='false')

 def test_presets_six_through_ten_keep_their_existing_job_contract(self):
  expected={'06_hand_drawn_underline','07_phrase_to_phrase_trace',
            '08_precision_bracket_highlight','09_sequential_statement_highlight',
            '10_documentary_phrase_master'}
  self.assertEqual({item[0] for item in MOD.PRESETS[5:]},expected)
  for preset in MOD.PRESETS[5:]:
   for bg in ('dark','ivory'):
    generated=MOD.build(preset,bg)
    self.assertEqual(generated['job_id'],preset[0]+'_'+bg)
    self.assertEqual(generated['canvas']['duration_frames'],180)
    self.assertEqual(generated['output']['path'],preset[0]+'_'+bg+'.mp4')
    self.assertTrue(any(layer.get('type')=='text' for layer in generated['layers']))

if __name__=='__main__': unittest.main()
