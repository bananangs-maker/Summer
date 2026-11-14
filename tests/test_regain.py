import unittest,sys,copy
from pathlib import Path
from datetime import datetime
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine import analyze,KST
NOW=datetime(2026,11,12,5,tzinfo=KST)
def exercise(sport,day,reps=None):
 return {'id':sport+day,'sport':sport,'date':day,'sets':reps or [],'minutes':30 if sport=='running' else 5,'distance':5 if sport=='running' else 0,'active':0,'effort':'moderate','clear':False,'week':1 if sport=='pullup' else 4,'day':1,'track':0}
def fixture():
 return {'profile':{'weight':65,'target':55,'start':'2026-11-05'},'logs':[exercise('running','2026-11-'+str(i).zfill(2)) for i in (5,6,7,8)],'routines':{},'regainStart':'2026-11-09'}
def row(s,day='2026-11-09',weather=None,now=NOW):
 return next(x for x in analyze(s,now,weather=weather)['series'] if x['date']==day)
class RegainTests(unittest.TestCase):
 def test_missing_day_raises_weight(self):
  q=analyze(fixture(),NOW);a=q['series'][3];b=q['series'][4]
  self.assertGreater(b['weight'],a['weight']);self.assertGreater(b['regain'],0)
 def test_partial_is_half(self):
  s=fixture();a=row(s);s['logs'].append(exercise('pullup','2026-11-09',[1]));b=row(s)
  self.assertAlmostEqual(a['regain'],b['regain']*2,places=5)
 def test_both_present_no_repetition_or_clear_threshold(self):
  s=fixture();s['logs'] += [exercise('pullup','2026-11-09',[1]),exercise('pushup','2026-11-09',[1])]
  self.assertEqual(row(s)['regain'],0)
  for x in s['logs']:x['clear']=True
  self.assertEqual(row(s)['regain'],0)
 def test_cardio_any_one_satisfies(self):
  for sport in ('running','badminton'):
   s=fixture();s['logs'].append(exercise(sport,'2026-11-10'))
   self.assertEqual(row(s,'2026-11-10')['regain'],0)
 def test_cardio_confirmed_dry_only(self):
  s=fixture();d='2026-11-10'
  self.assertEqual(row(s,d)['regain'],0)
  self.assertEqual(row(s,d,{d:{'wet':True,'complete':True}})['regain'],0)
  self.assertGreater(row(s,d,{d:{'wet':False,'complete':True}})['regain'],0)
 def test_rain_does_not_waive_body(self):
  self.assertGreater(row(fixture(),weather={'2026-11-09':{'wet':True}})['regain'],0)
 def test_vacation_exempt_and_cancel(self):
  s=fixture();s['vacations']=['2026-11-09'];self.assertEqual(row(s)['regain'],0)
  s['vacations']=[];self.assertGreater(row(s)['regain'],0)
 def test_0400_boundary(self):
  s=fixture();a=row(s,now=datetime(2026,11,10,3,59,tzinfo=KST));b=row(s,now=datetime(2026,11,10,4,0,tzinfo=KST))
  self.assertEqual(a['regain'],0);self.assertGreater(b['regain'],0)
 def test_cap_start_weight(self):
  s=fixture();q=analyze(s,datetime(2026,12,1,5,tzinfo=KST),weather={})
  self.assertTrue(all(x['weight']<=65 for x in q['series']))
 def test_no_prior_exercise_no_invented_gain(self):
  s=fixture();s['logs']=[];q=analyze(s,NOW)
  self.assertEqual(q['regainTotal'],0);self.assertEqual(q['weight'],65)
 def test_no_retroactive_application(self):
  s=fixture();s['regainStart']='2026-11-12';self.assertEqual(analyze(s,NOW)['regainTotal'],0)
 def test_edit_past_missing_day_removes_gain(self):
  s=fixture();before=analyze(s,NOW)['regainTotal'];s['logs'] += [exercise('pullup','2026-11-09',[1]),exercise('pushup','2026-11-09',[1])]
  self.assertLess(analyze(s,NOW)['regainTotal'],before)
 def test_eta_uses_net_progress(self):
  s=fixture();without=copy.deepcopy(s);without['regainStart']='2026-11-12'
  a=analyze(without,NOW);b=analyze(s,NOW)
  self.assertLess(b['averageNetKcal'],a['averageNetKcal'])
  self.assertTrue(b['days'] is None or b['days']>=a['days'])
 def test_deterministic_recalculation(self):
  s=fixture();self.assertEqual(analyze(s,NOW),analyze(s,NOW))
if __name__=='__main__':unittest.main()
