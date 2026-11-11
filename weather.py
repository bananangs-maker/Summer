"""Yeosu weather; model-based precipitation, not station observations."""
from datetime import datetime, timedelta, date
from urllib.parse import urlencode
from urllib.request import urlopen, Request
import json
import threading
import time
from engine import KST
LAT,LON=34.7604,127.6622
_lock=threading.Lock()
_mem={}
def parse_weather(raw, now, source):
    h=raw.get('hourly',{}); groups={}
    for i,t in enumerate(h.get('time',[])):
        if t>now.strftime('%Y-%m-%dT%H:00'):continue
        d=t[:10];g=groups.setdefault(d,[])
        p=h.get('precipitation',[]);sn=h.get('snowfall',[])
        v=p[i] if i<len(p) else None; n=sn[i] if i<len(sn) else None
        if v is not None and n is not None:g.append((float(v),float(n)))
    result={}
    for d,values in groups.items():
        wet=any(p>0 or n>0 for p,n in values)
        complete=len(values)==24 and d<now.date().isoformat()
        if values:
            result[d]={'wet':wet,'complete':complete,'precipitation':round(sum(v[0] for v in values),2),'snowfall':round(sum(v[1] for v in values),2),'source':source,'checkedAt':now.isoformat()}
    return result

def get_weather(store,start,now=None):
    now=now or datetime.now(KST); key=str(store.url or store.path)
    with _lock:
        if key in _mem and time.monotonic()-_mem[key][0]<1800 and _mem[key][1]<=start:
            return _mem[key][2]
        cached=store.weather_read(); result=dict(cached)
        def fetch(host,path,params):
            query={'latitude':LAT,'longitude':LON,'hourly':'precipitation,snowfall','timezone':'Asia/Seoul',**params}
            try:
                with urlopen(Request(host+path+'?'+urlencode(query),headers={'User-Agent':'MOTION-personal-training/1.1'}),timeout=6) as r:
                    payload=json.load(r)
                parsed=parse_weather(payload,now,'Open-Meteo · 예보/재분석 모델')
                # Previously detected wet weather stays exempt if the model is later revised.
                for d,v in parsed.items():
                    if cached.get(d,{}).get('wet'):v['wet']=True
                result.update(parsed)
            except Exception:
                pass # Unknown weather is never silently treated as dry.
        recent=(now.date()-timedelta(days=14)).isoformat()
        if start<recent:
            first=max(start,'1940-01-01');last=(now.date()-timedelta(days=15)).isoformat()
            d=date.fromisoformat(first); missing=[]
            while d.isoformat()<=last:
                if not cached.get(d.isoformat(),{}).get('complete'):missing.append(d.isoformat())
                d+=timedelta(days=1)
            if missing:fetch('https://archive-api.open-meteo.com','/v1/archive',{'start_date':missing[0],'end_date':missing[-1]})
        fetch('https://api.open-meteo.com','/v1/forecast',{'past_days':14,'forecast_days':1})
        if result!=cached:store.weather_write(result)
        _mem[key]=(time.monotonic(),start,result)
        return result
