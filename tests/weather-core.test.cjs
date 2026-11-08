const assert=require('node:assert/strict');
const fs=require('node:fs');
require('../assets/weather-core.js');
const C=globalThis.WeatherCore;
const data=JSON.parse(fs.readFileSync('weather.json','utf8'));
C.validate(data);
assert.equal(C.catalog.length,21);
assert.equal(C.name({weather:'Heavy Rain'}),'강한 비');
assert.equal(C.name({weather:'Moon Rainbow'}),'달 무지개');
assert.equal(C.special({weather:'Moon Rainbow',special:false}),true);
assert.equal(C.kst(new Date('2026-11-07T20:59:00Z')).gameDate,'2026-11-07');
assert.equal(C.kst(new Date('2026-11-07T21:00:00Z')).gameDate,'2026-11-08');
assert.equal(C.kst(new Date('2026-11-07T15:00:00Z')).hour,0);
assert.equal(C.entry('Aurora 3')[0],'Aurora 3');
assert.equal(C.entry('Rainbow 2')[0],'Rainbow');
assert.equal(C.entry('Unknown'),undefined);
for(const day of data.days){
 for(let start=0;start<24;start++)for(let end=0;end<24;end++){
  const a=(start+18)%24,b=(end+18)%24;
  if(b<=a)assert.throws(()=>C.calculate(day,start,end));
  else{const result=C.calculate(day,start,end);assert.equal(result.changes,day.weather.slice(a+1,b+1).filter(row=>row.changed).length);assert.equal(result.rate,(result.changes/(b-a)*100).toFixed(1));assert.equal(result.rows.length,b-a+1);}
 }
}
const broken=structuredClone(data);broken.days[0].weather.pop();assert.throws(()=>C.validate(broken));
const invalidCases=[
 x=>{delete x.days[0].status;},x=>{x.days[0].status=null;},x=>{x.days[0].status=5;},x=>{x.days[0].status={};},x=>{x.days[0].status=' ';},
 x=>{delete x.days[0].dateLabel;},x=>{x.days[0].dateLabel=[];},
 x=>{x.updated=123;},x=>{delete x.updated;},x=>{x.updated='2026-02-30 12:00';},x=>{x.updated='2026-11-08 24:00';},
 x=>{x.days[0]=null;},x=>{x.days[0].startDate='2026-02-30';},x=>{delete x.days[0].startDate;},x=>{delete x.days[0].weather;},
 x=>{x.days[0].weather[0]=null;},x=>{delete x.days[0].weather[0].time;},x=>{x.days[0].weather[0].weather=[];},x=>{x.days[0].weather[0].weather=' ';},
 x=>{delete x.days[0].weather[0].changed;},x=>{x.days[0].weather[0].special='false';},x=>{x.days[0].weather[0].name={};},
 x=>{x.days[0].changes='8';},x=>{delete x.days[0].changes;},x=>{x.days[0].changeRate='33.3';},x=>{delete x.days[0].changeRate;}
];
for(const mutate of invalidCases){const candidate=structuredClone(data);mutate(candidate);assert.throws(()=>C.validate(candidate));}
// Optional fallback metadata and unknown weather remain supported.
const fallback=structuredClone(data);delete fallback.days[0].weather[0].name;delete fallback.days[0].weather[0].special;fallback.days[0].weather[0].weather='Unknown';C.validate(fallback);
assert.deepEqual(C.validate(data),data);
console.log(`PASS: ${invalidCases.length} malformed payload cases rejected before state replacement`);
console.log('PASS: 21 icons, mappings, KST boundary, special weather, schema, 4,032 calculator intervals');
