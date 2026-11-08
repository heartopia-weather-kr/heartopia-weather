const assert=require('node:assert/strict');require('../assets/clock-layout.js');
const L=globalThis.ClockLayout;
for(let hour=0;hour<24;hour++){
 const p=L.point(hour);
 assert.ok(Math.abs(Math.hypot(p.x-50,p.y-50)-39)<1e-9);
 assert.deepEqual(p,L.point(hour%12));
 assert.ok(L.sector(hour).endsWith('Z'));
}
assert.deepEqual(L.point(0),{x:50,y:11});
assert.deepEqual(L.point(3),{x:89,y:50});
assert.ok(2*39*Math.sin(Math.PI/12)>2*L.ringRadius);
for(let hour=0;hour<12;hour++){
 const width=hour===0||hour>9?6:4,height=4.62;
 const p=L.labelPoint(hour,width,height),slot=L.point(hour),original=L.point(hour,L.labelRadius);
 const gap=point=>Math.hypot(Math.max(0,Math.abs(point.x-slot.x)-width/2),Math.max(0,Math.abs(point.y-slot.y)-height/2))-L.ringRadius-.225;
 assert.ok(Math.abs(gap(p)/gap(original)-.5)<1e-6);
 assert.ok(Math.hypot(p.x-50,p.y-50)<L.labelRadius);
}
console.log('PASS: 24 slot coordinates, cardinal anchors, uniform rings, wraparound sectors');
