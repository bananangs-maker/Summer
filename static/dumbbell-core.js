(function(root){
'use strict';
const specs={hammer_curl:{name:'해머 컬',sets:2,min:10,max:15,rest:75},dumbbell_curl:{name:'덤벨 컬',sets:1,min:10,max:15,rest:75},dumbbell_row:{name:'덤벨 로우',sets:2,min:8,max:12,rest:105},reverse_fly:{name:'벤트오버 리버스 플라이',sets:2,min:12,max:20,rest:75},shoulder_press:{name:'덤벨 숄더 프레스',sets:2,min:8,max:12,rest:105},lateral_raise:{name:'사이드 레터럴 레이즈',sets:2,min:12,max:20,rest:75}};
const ids=Object.keys(specs),order=['dumbbell_row','shoulder_press','hammer_curl','dumbbell_curl','reverse_fly','lateral_raise'];
const is=s=>ids.includes(s),names=Object.fromEntries(ids.map(k=>[k,specs[k].name]));
const config=(state,id)=>({...specs[id],increment:.5,...state.dumbbellConfig?.[id]});
const execution=id=>id==='dumbbell_row'?'per_side':'together';
const reps=x=>(x.sets||[]).reduce((a,b)=>a+b,0),volume=x=>reps(x)*x.load*2,active=x=>reps(x)*3/60*(x.execution==='per_side'?2:1);
function energy(x,w){let minutes=x.active||active(x);if(x.minutes)minutes=Math.min(minutes,x.minutes);return {kcal:Math.round(((x.effort==='hard'?6:3.5)-1.3)*w*3.5/200*minutes*100)/100,estimated:!x.active};}
function daily(state,date,present,wx){present=new Set(present);const body=[0,1,3,5].includes(new Date(date+'T12:00:00Z').getUTCDay()),cardios=['running','badminton'].filter(s=>present.has(s)).length,count=['pullup','pushup'].filter(s=>present.has(s)).length,dbDone=ids.filter(s=>present.has(s)).length,dbRequired=!!(!body&&state.dumbbellStart&&date>=state.dumbbellStart),vacation=(state.vacations||[]).includes(date),wet=!!wx?.wet;
 let complete=body?count===2:cardios>0,score=body?(count===2?100+25*cardios:count===1?-40:-80):(cardios?100+25*(cardios-1):-80),weatherPending=!body&&!complete&&!vacation&&!wet&&!wx?.complete,weatherExempt=!body&&wet,exempt=vacation||weatherExempt,missedFraction=body?(2-count)/2:(complete?0:1);
 if((exempt||weatherPending)&&score<0)score=0;if(vacation&&!complete)score=50*count+25*cardios;
 if(dbRequired){weatherPending=!cardios&&!vacation&&!wet&&!wx?.complete;complete=dbDone===6&&(cardios>0||wet);const missingSlots=6-dbDone+(!cardios&&!wet&&!weatherPending?1:0);missedFraction=missingSlots/7;score=complete?100+25*Math.max(0,cardios-1):-Math.round(80*missedFraction);exempt=vacation;if(vacation&&!complete)score=50*count+25*cardios;}
 return {body,complete,score,weatherPending,weatherExempt,wet,vacation,exempt,missedFraction,dbRequired,dbDone,missingDumbbells:dbRequired?ids.filter(s=>!present.has(s)):[]};
}
function validate(state,today){
 if(state.dumbbellStart&&(!/^\d{4}-\d{2}-\d{2}$/.test(state.dumbbellStart)||state.dumbbellStart>today||new Date(state.dumbbellStart+'T12:00:00Z').toISOString().slice(0,10)!==state.dumbbellStart))throw Error('덤벨 적용일을 확인해주세요.');
 const conf=state.dumbbellConfig||{};if(typeof conf!=='object'||Array.isArray(conf))throw Error('덤벨 설정을 확인해주세요.');
 for(const [id,c]of Object.entries(conf)){if(!is(id)||!c)throw Error('덤벨 종목을 확인해주세요.');for(const [key,lo,hi]of [['sets',1,10],['min',1,100],['max',1,100],['rest',15,300]])if(!Number.isInteger(c[key])||c[key]<lo||c[key]>hi)throw Error('덤벨 목표 세트·횟수·휴식을 확인해주세요.');if(c.min>c.max||!Number.isFinite(c.increment)||c.increment<=0||c.increment>20)throw Error('덤벨 목표 횟수·증량 단위를 확인해주세요.');}
 for(const x of state.logs||[]){if(!is(x.sport))continue;if(!Number.isFinite(x.load)||x.load<=0||x.load>200||!Array.isArray(x.sets)||x.sets.length>30||x.sets.some(v=>!Number.isInteger(v)||v<0||v>2000)||reps(x)<=0||!['together','per_side'].includes(x.execution)||!['moderate','hard'].includes(x.effort||'moderate'))throw Error('덤벨 중량·실제 횟수·횟수 기준·강도를 확인해주세요.');for(const k of ['minutes','active'])if(x[k]!==undefined&&(!Number.isFinite(x[k])||x[k]<0||x[k]>1440))throw Error('덤벨 운동 시간을 확인해주세요.');if(x.minutes&&x.active>x.minutes)throw Error('실제 동작 시간은 총 소요 시간보다 클 수 없습니다.');}
 return state;
}
function progression(state,id){const c=config(state,id),groups=new Map();for(const x of state.logs.filter(x=>x.sport===id).sort((a,b)=>a.date.localeCompare(b.date))){const key=x.date+'|'+x.load+'|'+x.execution;if(!groups.has(key))groups.set(key,{date:x.date,load:x.load,execution:x.execution,sets:[]});groups.get(key).sets.push(...x.sets);}const a=[...groups.values()].sort((a,b)=>a.date.localeCompare(b.date));const last=a.at(-1);if(!last)return {load:null,ready:false,next:null};const same=a.filter(x=>x.load===last.load&&x.execution===last.execution);const recent=same.slice(-2);const ready=recent.length===2&&recent[0].date!==recent[1].date&&a.slice(-2).every(x=>x.load===last.load&&x.execution===last.execution)&&recent.every(x=>x.sets.length>=c.sets&&x.sets.slice(0,c.sets).every(n=>n>=c.max));return {load:last.load,ready,next:ready?Math.round((last.load+c.increment)*1000)/1000:null};}
const api={specs,ids,order,names,is,config,execution,reps,volume,active,energy,daily,validate,progression};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.MotionDumbbells=api;
})(typeof globalThis!=='undefined'?globalThis:this);
