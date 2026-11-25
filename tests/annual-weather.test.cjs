const assert=require('node:assert/strict');
const release=require('../annual-weather.json');
const annual={...release,days:Object.fromEntries(Object.entries(release.days).filter(([key])=>key.startsWith('2026-')))};
require('../assets/weather-core.js');
require('../assets/weather-visual.js');
const C=WeatherCore;
assert.equal(C.validateAnnual(annual),annual);
assert.throws(()=>C.validateAnnual({...annual,unknownWeather:[]}),/24시간/);
const build=iso=>C.annualWindow(annual,C.kst(new Date(iso)).date);

for(const [before,after] of [['2026-11-25','2026-11-26'],['2026-11-30','2026-12-01'],['2026-12-31','2027-01-01']]){
  const old=build(before+'T14:59:00Z');
  const next=build(before+'T15:00:00Z');
  assert.equal(old.days[0].startDate,before);
  assert.equal(old.days[1].startDate,after);
  assert.equal(next.days[0].startDate,after);
  assert.equal(next.days.length,9);
  assert.equal(next.basisDate,old.basisDate);
  assert.deepEqual(next.days[0],old.days[1]);
}
const future=build('2026-12-31T15:00:00Z').days[0];
assert.equal(future.changeRate,null);
assert.ok(future.weather.every(row=>C.name(row)==='?'&&row.mark==='?'));
assert.throws(()=>C.calculate(future,0,1),/데이터/);
assert.match(WeatherVisual.shareText(future),/00:00 \? \[정기\]/);
const days={...annual.days};
delete days['2026-11-26'];
assert.equal(C.annualWindow({...annual,days},'2026-11-26').days[0].changeRate,null);
assert.throws(()=>C.annualWindow({...annual,days:{'2026-11-26':days['2026-11-27']}},'2026-11-26'),/날짜/);
assert.throws(()=>C.annualWindow({...annual,basisDate:'2026-02-30'},'2026-11-26'),/연간/);

for(const [key,day] of Object.entries(annual.days)){
  const priorKey=new Date(Date.parse(key)-86400000).toISOString().slice(0,10);
  const dates=[annual.days[priorKey],day].filter(Boolean);
  for(const [hour,row] of day.weather.entries()){
    assert.ok(C.entry(row.weather),key);
    assert.equal(row.changed,WeatherVisual.actualChange(dates,key,hour),key+' '+hour);
  }
  const result=C.calculate(day,0,23);
  assert.equal(result.changes,day.changes-Number(day.weather[0].changed),key);
  assert.match(WeatherVisual.shareText(day),/00:00 .+ \[정기\]/);
}
