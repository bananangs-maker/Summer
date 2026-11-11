"""Deterministic exercise ledger. Dates and settlement use Asia/Seoul."""
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
import math
SPORTS = ('pullup','pushup','running','badminton')
KST = ZoneInfo('Asia/Seoul')
def today(): return datetime.now(KST).date()
def settled_through(now=None):
    now = now or datetime.now(KST)
    return now.date() - timedelta(days=1 if now.hour >= 4 else 2)
def validate(s):
    if not isinstance(s,dict): raise ValueError('잘못된 데이터 형식입니다.')
    p=s.get('profile')
    if not p: raise ValueError('초기 설정이 필요합니다.')
    for key in ('weight','target'):
        n=p.get(key)
        if isinstance(n,bool) or not isinstance(n,(int,float)) or not math.isfinite(n) or not 30<=n<=300: raise ValueError('체중은 30~300kg 범위로 입력해주세요.')
    if p['target']>=p['weight']: raise ValueError('목표 체중은 시작 체중보다 낮게 입력해주세요.')
    start=date.fromisoformat(p['start'])
    if start>today(): raise ValueError('시작일은 오늘 이후일 수 없습니다.')
    if (today()-start).days>36500: raise ValueError('시작일을 확인해주세요.')
    if not isinstance(s.get('logs'),list): raise ValueError('운동 기록 목록을 확인해주세요.')
    routines=s.get('routines',{})
    if not isinstance(routines,dict): raise ValueError('루틴 설정을 확인해주세요.')
    for sport,r in routines.items():
        if sport not in ('pullup','pushup') or not isinstance(r,dict): raise ValueError('루틴 설정을 확인해주세요.')
        if sport=='pullup' and not 1<=int(r.get('week',1))<=38: raise ValueError('풀업 주차를 확인해주세요.')
        if sport=='pushup' and (int(r.get('week',4)) not in (4,5,6) or int(r.get('day',1)) not in (1,2,3) or int(r.get('track',0)) not in (0,1,2)): raise ValueError('푸쉬업 단계를 확인해주세요.')
    if len(s.get('logs',[]))>50000: raise ValueError('기록 수가 너무 많습니다.')
    vacations=s.get('vacations',[])
    if not isinstance(vacations,list) or len(vacations)!=len(set(vacations)): raise ValueError('휴가 날짜가 중복되었습니다.')
    months={}
    for v in vacations:
        vd=date.fromisoformat(v)
        if vd<start or vd>today(): raise ValueError('휴가는 시작일~오늘 사이에만 사용할 수 있습니다.')
        months[v[:7]]=months.get(v[:7],0)+1
        if months[v[:7]]>2: raise ValueError('휴가는 한 달에 2회까지 사용할 수 있습니다.')
    notes=s.get('vacationNotes',{})
    if not isinstance(notes,dict) or any(not isinstance(v,str) or len(v)>200 for v in notes.values()): raise ValueError('휴가 메모는 200자 이내로 입력해주세요.')
    ids=set()
    for x in s.get('logs',[]):
        if not isinstance(x,dict): raise ValueError('운동 기록을 확인해주세요.')
        if not isinstance(x.get('note',''),str) or len(x.get('note',''))>500: raise ValueError('메모는 500자 이내로 입력해주세요.')
        if not isinstance(x.get('id'),str) or x['id'] in ids: raise ValueError('기록 ID가 중복되거나 없습니다.')
        ids.add(x['id'])
        d=date.fromisoformat(x['date'])
        if d<start or d>today(): raise ValueError('기록 날짜는 시작일~오늘 사이여야 합니다.')
        if x.get('sport') not in SPORTS: raise ValueError('운동 종류를 확인해주세요.')
        for k in ('minutes','distance','active'):
            v=x.get(k,0)
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 or v> (1440 if k!='distance' else 200): raise ValueError('시간·거리를 확인해주세요.')
        sets=x.get('sets',[])
        if not isinstance(sets,list) or len(sets)>30 or any(type(v)!=int or not 0<=v<=2000 for v in sets): raise ValueError('세트별 횟수를 확인해주세요.')
        if x['sport'] in ('pullup','pushup') and sum(sets)<=0: raise ValueError('실제 수행한 횟수를 입력해주세요.')
        if x['sport'] in ('running','badminton') and x.get('minutes',0)<=0: raise ValueError('유산소 운동 시간을 입력해주세요.')
        if x['sport']=='running' and x.get('distance',0)<=0: raise ValueError('러닝 거리를 입력해주세요.')
        if x.get('minutes',0) and x.get('active',0)>x.get('minutes',0): raise ValueError('실제 운동 시간은 총 소요 시간보다 클 수 없습니다.')
        if x.get('effort','moderate') not in ('moderate','hard','match'): raise ValueError('운동 강도를 확인해주세요.')
        if x.get('sport')=='pullup' and not 1<=int(x.get('week',1))<=38: raise ValueError('풀업 주차를 확인해주세요.')
        if x.get('sport')=='pushup' and (int(x.get('week',4)) not in (4,5,6) or int(x.get('day',1)) not in (1,2,3) or int(x.get('track',0)) not in (0,1,2)): raise ValueError('푸쉬업 단계를 확인해주세요.')
    return s

def energy(x,w):
    sport=x['sport']; mins=x.get('minutes',0); estimated=False
    if sport in ('pullup','pushup'):
        # Active time is explicitly supplied or estimated at 3 seconds/rep.
        active=x.get('active',0) or sum(x.get('sets',[]))*3/60
        estimated=not bool(x.get('active',0))
        if mins: active=min(active,mins)
        met=7.5 if x.get('effort')=='hard' else 3.8
        # Rest is baseline, not credited as vigorous exercise.
        net=max(0,met-1.3)*w*3.5/200*active
    elif sport=='badminton':
        met={'moderate':5.5,'hard':7,'match':9}[x.get('effort','moderate')]
        net=(met-1.3)*w*3.5/200*mins
    else:
        speed=x['distance']/mins*60
        table=[(5,3.3),(6.8,6.5),(7.8,7.8),(8.5,8.5),(9.5,9),(10.3,9.3),(11,10.5),(11.8,11),(12.5,11.8),(13.3,12),(14.1,12.5),(15,13),(16.2,14.8),(18,16.8)]
        met=min(table,key=lambda a:abs(a[0]-speed))[1]
        net=max(0,met-1.3)*w*3.5/200*mins
    return round(net,2), estimated

def analyze(s,now=None,weather=None):
    if not s.get('profile'): return None
    weather=weather if weather is not None else {}
    p=s['profile']; start=date.fromisoformat(p['start']); end=(now or datetime.now(KST)).date(); cutoff=settled_through(now)
    by={}
    for x in s.get('logs',[]): by.setdefault(x['date'],[]).append(x)
    w=p['weight']; xp=0; total=0; series=[]; details=[]; clear_seen=set(); training_days=0
    d=start
    while d<=end:
        rows=by.get(d.isoformat(),[]); present={x['sport'] for x in rows}; body=d.weekday() in (0,2,4,6)
        fulfilled=({'pullup','pushup'}<=present) if body else bool(present&{'running','badminton'})
        if body:
            missing=len({'pullup','pushup'}-present)
            score=100 if missing==0 else (-40 if missing==1 else -80)
            if not missing: score+=25*len(present&{'running','badminton'})
        else: score=100+25*(len(present&{'running','badminton'})-1) if fulfilled else -80
        vacation=d.isoformat() in s.get('vacations',[])
        wx=weather.get(d.isoformat())
        wet=bool(wx and wx.get('wet'))
        unknown=not body and not fulfilled and not vacation and not wet and not (wx and wx.get('complete'))
        exempt=vacation or (not body and wet)
        if (exempt or unknown) and score<0: score=0
        if vacation and not fulfilled: score=50*len(present&{'pullup','pushup'})+25*len(present&{'running','badminton'})
        # No penalty before the next 04:00 settlement.
        pending=d>cutoff
        if pending and score<0: score=0
        daykcal=0; enriched=[]
        for x in rows:
            kcal,est=energy(x,w); daykcal+=kcal
            enriched.append(dict(x,kcal=kcal,estimated=est))
            key=(x['sport'],x.get('week'),x.get('day'),x.get('track'))
            if x.get('clear') and x['sport'] in ('pullup','pushup') and key not in clear_seen:
                clear_seen.add(key)
                if fulfilled: score+=20
        xp=max(0,xp+score); total+=daykcal
        w=max(1,w-daykcal/7700)
        if rows: training_days+=1
        series.append({'date':d.isoformat(),'weight':round(w,3),'kcal':round(daykcal,1),'xp':xp,'score':score,'complete':fulfilled,'pending':pending,'vacation':vacation,'weatherExempt':bool(not body and wet),'weatherPending':unknown,'wet':wet})
        details.extend(enriched); d+=timedelta(days=1)
    completed=[x for x in series if x['date']<=cutoff.isoformat()][-28:]
    # Coefficient scales energy with projected bodyweight as it falls.
    coeff=sum(x['kcal']/max(x['weight'],1) for x in completed)/len(completed) if completed else 0
    def project(factor=1):
        if w<=p['target']: return 0
        if coeff<=0: return None
        v=w
        for n in range(1,3651):
            v-=v*coeff*factor/7700
            if v<=p['target']: return n
        return None
    days=project() if len(completed)>=7 else None
    eta=(end+timedelta(days=days)).isoformat() if days is not None else None
    badges=[]
    if training_days: badges.append('첫 기록')
    if training_days>=7: badges.append('운동 7일')
    if clear_seen: badges.append('첫 단계 클리어')
    if sum(x.get('distance',0) for x in s.get('logs',[]) if x['sport']=='running')>=10: badges.append('누적 러닝 10km')
    if set(SPORTS)<={x['sport'] for x in s.get('logs',[])}: badges.append('네 종목 플레이어')
    return {'weight':round(w,2),'lost':round(p['weight']-w,2),'remaining':round(max(0,w-p['target']),2),'progress':round(min(100,max(0,(p['weight']-w)/(p['weight']-p['target'])*100)),1),'xp':xp,'vacationsRemaining':2-sum(v.startswith(end.isoformat()[:7]) for v in s.get('vacations',[])),'kcal':round(total),'series':series,'details':details,'days':days,'eta':eta,'range':[project(1.3),project(.7)] if len(completed)>=7 else None,'sampleDays':len(completed),'badges':badges,'trainingDays':training_days}
