/* MOTION observation protocol 1.0. Original tasks, not a validated clinical battery. */
(function(root){
'use strict';
const VERSION='motion-observation-1.0', DAY=86400000;
const dateKST=(v=Date.now())=>new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Seoul'}).format(new Date(v));
const median=a=>{if(!a.length)return null;const s=[...a].sort((a,b)=>a-b),m=Math.floor(s.length/2);return s.length%2?s[m]:(s[m-1]+s[m])/2;};
function score(s){
 const attention=(s.trials||[]).filter(t=>t.task==='attention'), responses=attention.filter(t=>t.kind==='response'&&t.rt>=100), opportunities=attention.filter(t=>['response','omission'].includes(t.kind));
 const memory=task=>{const rows=(s.trials||[]).filter(t=>t.task===task);return {correct:rows.filter(t=>t.answer===t.target).length,total:rows.length};};
 const digits=(s.trials||[]).filter(t=>t.task==='backward'), good=digits.filter(t=>t.answer===t.target);
 return {reactionMs:median(responses.map(t=>t.rt)),slow:responses.filter(t=>t.rt>=500).length,omissions:opportunities.filter(t=>t.kind==='omission').length,anticipations:attention.filter(t=>t.kind==='anticipation').length,attentionTrials:opportunities.length,immediate:memory('immediate'),delayed:memory('delayed'),backward:{correct:good.length,total:digits.length,maxSpan:good.length?Math.max(...good.map(t=>t.length)):0}};
}
function comparable(s){return s.status==='complete'&&s.version===VERSION&&!s.flags.length&&s.trials.filter(t=>t.task==='immediate').length===6&&s.trials.filter(t=>t.task==='delayed').length===6&&s.trials.filter(t=>t.task==='backward').length===12&&s.attentionDuration>=180000&&s.trials.filter(t=>t.task==='attention'&&['response','omission'].includes(t.kind)).length>=20;}
function eligible(sessions,device,input){return sessions.filter(s=>comparable(s)&&s.context.device===device&&s.context.input===input).sort((a,b)=>Date.parse(a.startedAt)-Date.parse(b.startedAt));}
function schedule(sessions,device,input,now=Date.now()){
 const a=eligible(sessions,device,input),practice=a[0],refs=[];
 for(const s of a.slice(1)){const prev=refs.at(-1)||practice;if(Date.parse(s.startedAt)-Date.parse(prev.startedAt)>=DAY&&refs.length<3)refs.push(s);}
 const last=refs.length===3?a.at(-1):refs.at(-1)||practice;
 const due=last?Date.parse(last.startedAt)+(refs.length<3?DAY:7*DAY):now;
 return {practice,refs,last,due,isDue:now>=due,stage:!practice?'practice':refs.length<3?'reference':'monitoring'};
}
function sleepMinutes(x){return (Date.parse(x.wake)-Date.parse(x.bed))/60000;}
function circularDifference(a,b){let d=(a-b+720)%1440;if(d<0)d+=1440;return d-720;}
function wakeDeviation(wake,target){const m=wake.match(/T(\d{2}):(\d{2})/);const t=target.split(':').map(Number);return circularDifference(+m[1]*60+ +m[2],t[0]*60+t[1]);}
function validate(h,now=Date.now()){
 const fail=()=>{throw Error('기록 형식 또는 값이 올바르지 않습니다. 원본 JSON 백업을 확인해주세요.');};
 const iso=v=>typeof v==='string'&&Number.isFinite(Date.parse(v));
 const kiso=v=>iso(v)&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:00\+09:00$/.test(v)&&dateKST(v)===v.slice(0,10);
 const date=v=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&!isNaN(Date.parse(v))&&new Date(v+'T12:00:00Z').toISOString().slice(0,10)===v&&v<=dateKST(now);
 if(!h||(h.revision!==undefined&&(!Number.isInteger(h.revision)||h.revision<0))||h.schema!==1||!Array.isArray(h.study)||!Array.isArray(h.sleep)||!Array.isArray(h.sessions)||!h.settings)fail();
 if(!/^([01]\d|2[0-3]):[0-5]\d$/.test(h.settings.wakeTarget)||typeof h.settings.device!=='string'||h.settings.device.length>60||!['keyboard','pointer'].includes(h.settings.input))fail();
 const ids=new Set();
 for(const list of [h.study,h.sleep,h.sessions]){if(list.length>5000)fail();for(const x of list){if(!x||typeof x.id!=='string'||ids.has(x.id))fail();ids.add(x.id);}}
 for(const x of h.study)if(!date(x.date)||!Number.isFinite(x.minutes)||x.minutes<=0||x.minutes>1440||typeof x.topic!=='string'||x.topic.length>100)fail();
 const byDate={};for(const x of h.study){byDate[x.date]=(byDate[x.date]||0)+x.minutes;if(byDate[x.date]>1440)fail();}
 const intervals=[];for(const x of h.sleep){if(!kiso(x.bed)||!kiso(x.wake)||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:00\+09:00$/.test(x.bed)||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:00\+09:00$/.test(x.wake)||Date.parse(x.wake)>now||sleepMinutes(x)<=0||sleepMinutes(x)>1440||typeof x.nap!=='boolean')fail();intervals.push([Date.parse(x.bed),Date.parse(x.wake)]);}
 intervals.sort((a,b)=>a[0]-b[0]);for(let i=1;i<intervals.length;i++)if(intervals[i][0]<intervals[i-1][1])throw Error('수면 기록 시간이 겹칩니다.');
 for(const s of h.sessions){
  if(s.version!==VERSION||!iso(s.startedAt)||!iso(s.endedAt)||Date.parse(s.endedAt)<Date.parse(s.startedAt)||Date.parse(s.endedAt)>now+10000||!['complete','interrupted'].includes(s.status)||!Array.isArray(s.flags)||s.flags.some(x=>typeof x!=='string'||x.length>200)||!Array.isArray(s.trials)||s.trials.length>2000||!s.context||typeof s.context.device!=='string'||s.context.device.length>60||!['keyboard','pointer'].includes(s.context.input)||typeof s.context.browser!=='string'||s.context.browser.length>1000||typeof s.context.medication!=='string'||s.context.medication.length>100||!['unknown','none','taken'].includes(s.context.medStatus)||!Number.isFinite(s.context.sleepiness)||s.context.sleepiness<0||s.context.sleepiness>10||!Number.isFinite(s.attentionDuration)||s.attentionDuration<0||s.attentionDuration>1000000||!Number.isFinite(s.delayMs)||s.delayMs<0)fail();
  if(s.context.medAt!==''&&!iso(s.context.medAt))fail();
  if(s.context.medAt&&Date.parse(s.context.medAt)>Date.parse(s.startedAt))fail();
  for(const t of s.trials){if(!['attention','immediate','delayed','backward'].includes(t.task)||!Number.isFinite(t.at)||t.at<0||t.at>3600000)fail();if(t.task==='attention'){if(!['anticipation','response','omission'].includes(t.kind)||!Number.isFinite(t.rt)||t.rt<0||t.rt>20000)fail();}else if(t.task==='backward'){if(typeof t.target!=='string'||!/^\d{2,7}$/.test(t.target)||typeof t.answer!=='string'||!/^\d{0,7}$/.test(t.answer)||t.length!==t.target.length||!Number.isFinite(t.rt)||t.rt<0||t.rt>20000)fail();}else if(!Number.isInteger(t.target)||t.target<0||t.target>8||!Number.isInteger(t.answer)||t.answer< -1||t.answer>8||!Number.isInteger(t.symbol)||t.symbol<0||t.symbol>5||!Number.isFinite(t.rt)||t.rt<0||t.rt>20000)fail();}
 }
 if(h.learning!==undefined){const L=typeof module!=='undefined'&&module.exports?require('./learning-core.js'):root.MotionLearning;if(!L)fail();L.validate(h.learning,dateKST(now));}
 return h;
}
const api={VERSION,DAY,dateKST,median,score,comparable,eligible,schedule,sleepMinutes,wakeDeviation,validate};
if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.MotionObservation=api;
})(typeof globalThis!=='undefined'?globalThis:this);
