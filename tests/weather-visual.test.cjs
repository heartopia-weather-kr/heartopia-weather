const assert=require('node:assert/strict');
require('../assets/weather-visual.js');
const V=globalThis.WeatherVisual;
const day=date=>({startDate:date,weather:Array.from({length:24},(_,i)=>({time:String((i+6)%24).padStart(2,'0')+':00',weather:'Sunny',changed:true}))});
const days=[day('2026-11-08'),day('2026-11-09')];
for(const hour of [0,6,12,18])assert.equal(V.actualChange(days,days[1].startDate,hour),false,'Forced changes do not imply a visual shift');
assert.equal(V.actualChange(days,days[0].startDate,6),false,'Unknown previous hour');
days[0].weather[23].weather='Cloudy';
assert.equal(V.actualChange(days,days[1].startDate,6),true,'05 to 06 across game dates');
days[1].weather[17].weather='Cloudy';
assert.equal(V.actualChange(days,days[1].startDate,0),true,'23 to 00');
days[1].weather[18].weather='Cloudy';
assert.equal(V.actualChange(days,days[1].startDate,0),false,'Unchanged at midnight');
days[1].weather[1].weather='Light Rain';
assert.equal(V.actualChange(days,days[1].startDate,7),true,'Changes outside regular periods');
for(const [before,after,changed] of [
 ['Rainbow 1','Rainbow 2',false],[' Aurora 1 ','aurora 2',true],
 ['Meteor Shower 1','Meteor Shower 3',true],['Moon Rainbow','Rainbow',true],
 ['Moon Rainbow','Moon Rainbow',false],['Sunny',' sunny ',false]
]){
 days[1].weather[2].weather=before;days[1].weather[3].weather=after;
 assert.equal(V.actualChange(days,days[1].startDate,9),changed,`${before} -> ${after}`);
}
assert.equal(V.actualChange([],days[0].startDate,12),false);
console.log('PASS: display-only shifts, fixed-hour exclusions, missing previous data, midnight/game-day boundaries, special variants');
