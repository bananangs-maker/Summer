import unittest,sys
from pathlib import Path
from datetime import datetime
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine import analyze,validate,KST
from weather import parse_weather
NOW=datetime(2026,11,12,5,tzinfo=KST)
def state(v=None):return {'profile':{'weight':65,'target':55,'start':'2026-11-01'},'logs':[],'routines':{},'vacations':v or []}
class ExemptionTests(unittest.TestCase):
 def row(self,s,d,weather=None):return next(x for x in analyze(s,NOW,weather=weather)['series'] if x['date']==d)
 def test_rain_cardio_waived(self):
  x=self.row(state(),'2026-11-10',{'2026-11-10':{'wet':True,'complete':True}})
  self.assertEqual(x['score'],0);self.assertTrue(x['weatherExempt']);self.assertFalse(x['complete'])
 def test_rain_body_not_waived(self):
  x=self.row(state(),'2026-11-09',{'2026-11-09':{'wet':True,'complete':True}})
  self.assertEqual(x['score'],-80);self.assertFalse(x['weatherExempt'])
 def test_unknown_not_dry(self):
  x=self.row(state(),'2026-11-10');self.assertTrue(x['weatherPending']);self.assertEqual(x['score'],0)
 def test_confirmed_dry_penalty(self):
  x=self.row(state(),'2026-11-10',{'2026-11-10':{'wet':False,'complete':True}});self.assertEqual(x['score'],-80)
 def test_vacation_body_waived(self):
  x=self.row(state(['2026-11-09']),'2026-11-09');self.assertEqual(x['score'],0);self.assertTrue(x['vacation'])
 def test_vacation_no_fake_loss(self):
  q=analyze(state(['2026-11-09']),NOW);self.assertEqual(q['weight'],65);self.assertEqual(q['trainingDays'],0)
 def test_month_limit_and_duplicate(self):
  with self.assertRaises(ValueError):validate(state(['2026-11-01','2026-11-02','2026-11-03']))
  with self.assertRaises(ValueError):validate(state(['2026-11-01','2026-11-01']))
 def test_month_reset(self):
  s=state(['2026-10-01','2026-10-02','2026-11-01']);s['profile']['start']='2026-10-01';validate(s)
  self.assertEqual(analyze(s,NOW)['vacationsRemaining'],1)
 def test_cancel_restores_penalty(self):
  a=self.row(state(['2026-11-09']),'2026-11-09');b=self.row(state(),'2026-11-09');self.assertEqual(a['score'],0);self.assertEqual(b['score'],-80)
 def test_future_forecast_not_exempt(self):
  now=datetime(2026,11,11,12,tzinfo=KST)
  raw={'hourly':{'time':['2026-11-11T10:00','2026-11-11T18:00'],'precipitation':[0,1],'snowfall':[0,0]}}
  out=parse_weather(raw,now,'test');self.assertFalse(out['2026-11-11']['wet']);self.assertFalse(out['2026-11-11']['complete'])
 def test_tiny_snow_or_rain_counts(self):
  now=datetime(2026,11,11,12,tzinfo=KST)
  for rain,snow in [(0.01,0),(0,0.01)]:
   raw={'hourly':{'time':['2026-11-11T10:00'],'precipitation':[rain],'snowfall':[snow]}}
   self.assertTrue(parse_weather(raw,now,'test')['2026-11-11']['wet'])
 def test_null_hours_not_complete(self):
  raw={'hourly':{'time':[f'2026-11-10T{h:02d}:00' for h in range(24)],'precipitation':[None]*24,'snowfall':[None]*24}}
  self.assertEqual(parse_weather(raw,NOW,'test'),{})
if __name__=='__main__':unittest.main()
