import unittest, sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine import analyze,validate,settled_through,KST,energy
NOW=datetime(2026,11,12,5,tzinfo=KST)
def state(logs=None,start='2026-11-09'):
    return {'profile':{'weight':65,'target':55,'start':start},'logs':logs or [],'routines':{}}
def log(s,d='2026-11-09',**kw):
    return dict(id=s+d,sport=s,date=d,sets=[5,5] if s in ('pullup','pushup') else [],minutes=20,distance=3 if s=='running' else 0,active=0,effort='moderate',clear=False,week=1 if s=='pullup' else 4,day=1,track=0,**kw)
class EngineTests(unittest.TestCase):
    def test_boundary(self):
        self.assertEqual(settled_through(datetime(2026,11,12,3,59,tzinfo=KST)).isoformat(),'2026-11-10')
        self.assertEqual(settled_through(NOW).isoformat(),'2026-11-11')
    def test_both_required(self):
        q=analyze(state([log('pullup')]),NOW)
        self.assertEqual(q['series'][0]['score'],-40)
        self.assertEqual(q['xp'],0)
    def test_bonus_cannot_mask_missing(self):
        q=analyze(state([log('pullup'),log('running'),log('badminton')]),NOW)
        self.assertEqual(q['series'][0]['score'],-40)
    def test_duplicate_sport_not_duplicate_points(self):
        rows=[log('pullup'),log('pushup'),log('running')]; rows.append(dict(rows[0],id='extra'))
        self.assertEqual(analyze(state(rows),NOW)['series'][0]['score'],125)
    def test_cardio_choice(self):
        q=analyze(state([log('badminton','2026-11-10'),log('running','2026-11-10')]),NOW)
        self.assertEqual(q['series'][1]['score'],125)
    def test_pending_no_penalty(self):
        q=analyze(state(),NOW)
        self.assertEqual(q['series'][-1]['score'],0)
    def test_edit_recalculates(self):
        a=analyze(state([log('pullup'),log('pushup')]),NOW)
        b=analyze(state(),NOW)
        self.assertGreater(a['kcal'],b['kcal'])
    def test_rest_not_vigorous(self):
        x=log('pullup'); a=energy(x,65)[0]; x['minutes']=120
        self.assertEqual(a,energy(x,65)[0])
    def test_manual_clear_independent_of_reps(self):
        x=log('pullup'); x['clear']=True;x['sets']=[1]
        q=analyze(state([x,log('pushup')]),NOW)
        self.assertEqual(q['series'][0]['score'],120)
    def test_repeated_clear_no_farming(self):
        a=log('pullup');a['clear']=True;b=dict(a,id='again')
        self.assertEqual(analyze(state([a,b,log('pushup')]),NOW)['series'][0]['score'],120)
    def test_forecast_includes_empty_days(self):
        q=analyze(state([log('running',f'2026-11-{d:02d}') for d in range(1,8)],start='2026-11-01'),NOW)
        self.assertEqual(q['sampleDays'],11)
        self.assertGreater(q['days'],100)
        self.assertLess(q['range'][0],q['days'])
    def test_validation(self):
        with self.assertRaises(ValueError):validate(state([dict(log('pullup'),sets=[-1])]))
        with self.assertRaises(ValueError):validate(state([dict(log('running'),minutes=0)]))
        with self.assertRaises(ValueError):validate(state([dict(log('pullup'),date='2099-01-01')]))
if __name__=='__main__':unittest.main()
