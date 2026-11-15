import unittest,sys,copy,math
from pathlib import Path
from datetime import datetime
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine import DUMBBELLS,analyze,validate,energy,KST,today

class DumbbellTests(unittest.TestCase):
 def state(self):return {'profile':{'weight':65,'target':55,'start':'2026-11-01'},'regainStart':'2026-11-01','dumbbellStart':'2026-11-03','logs':[],'routines':{}}
 def log(self,sport,date='2026-11-03'):
  return {'id':sport+date,'sport':sport,'date':date,'sets':[10,10] if sport in DUMBBELLS or sport=='pullup' else [],'load':5,'execution':'per_side' if sport=='dumbbell_row' else 'together','minutes':20 if sport=='running' else 0,'distance':3 if sport=='running' else 0,'effort':'moderate'}
 def day(self,s,wx={'wet':False,'complete':True}):return analyze(s,datetime(2026,11,4,5,tzinfo=KST),{'2026-11-03':wx})['series'][-2]
 def test_all_six_and_cardio(self):
  s=self.state();s['logs']=[self.log(k) for k in (*DUMBBELLS,'running')];d=self.day(s);self.assertTrue(d['complete']);self.assertEqual(d['dbDone'],6);self.assertEqual(d['score'],100);self.assertEqual(d['missedFraction'],0)
 def test_actual_reps_count_even_under_target(self):
  s=self.state();s['logs']=[self.log(k) for k in (*DUMBBELLS,'running')]
  for x in s['logs']:
   if x['sport'] in DUMBBELLS:x['sets']=[1];x['clear']=False
  self.assertTrue(self.day(s)['complete'])
 def test_missing_one(self):
  s=self.state();s['logs']=[self.log(k) for k in (*DUMBBELLS[:-1],'running')];d=self.day(s);self.assertFalse(d['complete']);self.assertAlmostEqual(d['missedFraction'],1/7);self.assertEqual(d['score'],-11)
 def test_rain_only_waives_cardio(self):
  s=self.state();s['logs']=[self.log(k) for k in DUMBBELLS];self.assertTrue(self.day(s,{'wet':True,'complete':True})['complete']);s['logs']=s['logs'][:-1];d=self.day(s,{'wet':True,'complete':True});self.assertFalse(d['complete']);self.assertEqual(d['score'],-11)
 def test_unknown_waives_only_cardio_pending(self):
  s=self.state();s['logs']=[self.log(k) for k in DUMBBELLS[:-1]];d=self.day(s,{});self.assertTrue(d['weatherPending']);self.assertEqual(d['score'],-11);self.assertAlmostEqual(d['missedFraction'],1/7)
 def test_vacation_waives_all(self):
  s=self.state();s['vacations']=['2026-11-03'];d=self.day(s);self.assertEqual(d['score'],0);self.assertEqual(d['regain'],0)
 def test_upgrade_not_retroactive(self):
  s=self.state();s['dumbbellStart']='2026-11-04';s['logs']=[self.log('running')];d=self.day(s);self.assertTrue(d['complete']);self.assertFalse(d['dbRequired'])
 def test_valid_load_and_mode(self):
  s=self.state();x=self.log('hammer_curl',today().isoformat());s['logs']=[x];validate(s)
  for key,v in [('load',True),('load',0),('load',float('nan')),('execution','other')]:
   n=copy.deepcopy(s);n['logs'][0][key]=v
   with self.assertRaises(ValueError):validate(n)
 def test_energy_mode_and_weight(self):
  x=self.log('hammer_curl');a=energy(x,65)[0];x['load']=50;self.assertEqual(energy(x,65)[0],a);x['execution']='per_side';self.assertAlmostEqual(energy(x,65)[0],2*a,delta=.02);x['minutes']=.1;self.assertLess(energy(x,65)[0],a)
 def test_regain_on_rain_and_unknown_missing_db(self):
  s=self.state();s['logs']=[self.log('running','2026-11-01')]
  for wx in ({'wet':True,'complete':True},{}):self.assertGreater(self.day(s,wx)['regain'],0)
if __name__=='__main__':unittest.main()

class DumbbellPreviewParity(unittest.TestCase):
 def test_preview_matches_server(self):
  import json,subprocess
  root=Path(__file__).resolve().parents[1]
  base={'profile':{'weight':65,'target':55,'start':'2026-11-01'},'regainStart':'2026-11-01','dumbbellStart':'2026-11-03','logs':[],'routines':{}}
  helper=DumbbellTests();base['logs']=[helper.log('running','2026-11-01')]
  for mode in ('all','missing','rain','unknown','vacation','legacy'):
   s=copy.deepcopy(base);s['logs'] += [helper.log(k) for k in DUMBBELLS]
   wx={'wet':False,'complete':True}
   if mode=='all':s['logs'].append(helper.log('running'))
   if mode in ('missing','unknown'):s['logs']=s['logs'][:-1]
   if mode=='rain':wx={'wet':True,'complete':True};s['logs']=s['logs'][:-1]
   if mode=='unknown':wx={}
   if mode=='vacation':s['vacations']=['2026-11-03']
   if mode=='legacy':s.pop('dumbbellStart');s['logs'].append(helper.log('running'))
   weather={'2026-11-03':wx};now=datetime(2026,11,5,5,tzinfo=KST)
   py=analyze(s,now,weather);payload=json.dumps({'state':s,'weather':weather,'date':'2026-11-05','hour':5})
   js=json.loads(subprocess.check_output(['node',str(root/'tests/test_dumbbell_parity.cjs')],input=payload.encode()))
   for a,b in zip(py['series'],js['series']):
    for key in ('complete','score','dbRequired','dbDone','weatherExempt','weatherPending','missingDumbbells'):self.assertEqual(a[key],b[key],(mode,key,a,b))
    for key in ('weight','regain','netKcal'):self.assertAlmostEqual(a[key],b[key],places=5,msg=str((mode,key)))
