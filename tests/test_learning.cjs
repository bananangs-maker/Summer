'use strict';
const assert=require('node:assert/strict'),L=require('../static/learning-core.js');
const today='2026-11-15',start='2026-08-01',end=L.addDays(start,99),g={id:'g',title:'회계관리 1급',color:'#0047ab',start,end,weekdays:[0,1,2,3,4,5,6],exam:'2026-11-20',subgoals:[{id:'s',title:'교재',total:100,unit:'페이지',first:1}]};
function state(){return {schema:1,goals:[structuredClone(g)],tasks:L.plannedDays(g).map((date,i)=>({id:'t'+i,goalId:'g',subgoalId:'s',date,quantity:1,from:i+1,to:i+1,done:i<50})),vacations:[]};}
let a=state();L.validate(a,today);assert.equal(L.goalStats(a,g,today).total,100);assert.equal(L.goalStats(a,g,today).rate,50);assert.equal(L.goalStats(a,g,today).ended,true);
// One incomplete subgoal blocks the whole goal-day, without fractional credit.
a.goals[0].subgoals.push({id:'s2',title:'문제',total:1,unit:'개',first:1});a.tasks.push({id:'extra',goalId:'g',subgoalId:'s2',date:start,quantity:1,from:1,to:1,done:false});assert.equal(L.goalStats(a,a.goals[0],today).rate,49);
// Equal arithmetic weighting despite different lengths.
a=state();const b={id:'b',title:'전산세무',color:'#be651b',start:'2026-11-01',end:'2026-11-10',weekdays:[0,1,2,3,4,5,6],exam:'',subgoals:[{id:'bs',title:'문제',total:10,unit:'개',first:1}]};a.goals.push(b);a.tasks.push(...L.plannedDays(b).map((date,i)=>({id:'bt'+i,goalId:'b',subgoalId:'bs',date,quantity:1,from:i+1,to:i+1,done:i<8})));assert.equal(L.average(a,today),65);
// Vacations exempt denominator and never create completion.
a=state();a.vacations=[L.addDays(start,70)];let q=L.goalStats(a,g,today);assert.equal(q.completed,50);assert.equal(q.total,99);assert.equal(q.exempt,1);a.vacations=[start];q=L.goalStats(a,g,today);assert.equal(q.completed,49);assert.equal(q.total,99);
const seven=L.dates('2026-11-16','2026-11-22'),amounts=L.distribute(100,seven,2);assert.equal(amounts.reduce((a,b)=>a+b,0),100);assert(amounts.slice(5).every(x=>x>Math.max(...amounts.slice(0,5))));assert.equal(L.distribute(100,seven,1).reduce((a,b)=>a+b),100);assert(L.distribute(7,seven,5).every(x=>x>=1));
const x={...g,start:'2026-11-16',end:'2026-12-16',weekdays:[1,2,3,4,5,6,0]},s=g.subgoals[0],plan={...state(),vacations:['2026-11-17']};const rows=L.allocate(plan,x,s,'2026-11-16',10,2);assert.equal(rows.length,10);assert(!rows.some(r=>r.date==='2026-11-17'));assert.equal(rows[0].from,1);assert.equal(rows.at(-1).to,100);assert.equal(rows.reduce((v,r)=>v+r.quantity,0),100);assert.throws(()=>L.allocate(plan,x,s,'2026-11-16',100,2));
assert.equal(L.dday('2026-11-20',today),5);assert.equal(L.dday(today,today),0);assert.equal(L.dday('2026-11-14',today),-1);assert.equal(L.average(L.empty(),today),null);
for(const mutate of [a=>a.vacations=['2026-11-01','2026-11-02','2026-11-03'],a=>a.tasks[1].from=a.tasks[0].from,a=>a.tasks[0].date='2026-02-30',a=>a.goals[0].color='red',a=>a.goals[0].weekdays=[],a=>a.goals[0].id='bad"id',a=>a.tasks[0].done='yes']){const a=state();mutate(a);assert.throws(()=>L.validate(a,today));}
a=state();a.tasks[0].date='2027-01-01';assert.throws(()=>L.validate(a,today));
const H=require('../static/wellbeing-core.js');const h={schema:1,study:[],sleep:[],sessions:[],settings:{device:'',input:'keyboard',wakeTarget:'07:00'},learning:state()};assert(H.validate(h,Date.parse(today+'T12:00:00+09:00')));h.learning.vacations=['2026-11-01','2026-11-02','2026-11-03'];assert.throws(()=>H.validate(h,Date.parse(today+'T12:00:00+09:00')));
console.log('Learning: all-tasks day completion, 50/100 final score, unweighted 65% mean, vacation caps, exact weighted allocation, date/range integrity and health backup validation passed.');
