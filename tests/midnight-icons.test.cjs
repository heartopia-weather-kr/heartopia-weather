const assert=require('node:assert/strict');
const fs=require('node:fs');
require('../assets/weather-core.js');
global.window=globalThis;
require('../assets/midnight-icons.js');
const manifest=JSON.parse(fs.readFileSync('assets/midnight-icons/manifest.json','utf8'));
const keys=WeatherCore.catalog.map(row=>row[0]);
assert.deepEqual(Object.keys(MidnightIcons),keys);
assert.deepEqual(Object.keys(manifest),keys);
assert.equal(new Set(Object.values(MidnightIcons)).size,21);
for(const key of keys){
 const file=MidnightIcons[key]+'.png';assert.equal(manifest[key].file,file);
 assert.ok(fs.existsSync('assets/midnight-icons/'+file));
}
for(const family of ['Meteor Shower','Aurora']){
 assert.equal(new Set([1,2,3].map(n=>MidnightIcons[WeatherCore.entry(`${family} ${n}`)[0]])).size,3);
}
console.log('PASS: all 21 native Midnight assets mapped 1:1; special variants remain distinct');
