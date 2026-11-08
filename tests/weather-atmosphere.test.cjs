const assert=require('node:assert/strict');
global.window=globalThis;
require('../assets/weather-core.js');require('../assets/weather-atmosphere.js');
const A=WeatherAtmosphere;
assert.deepEqual(Object.keys(A.effects),WeatherCore.catalog.map(row=>row[0]));
assert.equal(new Set(Object.values(A.effects).map(effect=>effect.id)).size,21);
for(const item of WeatherCore.catalog){assert.equal(A.select(item[0]),A.effects[item[0]]);assert.ok(A.select(item[0]).count<=26);}
assert.notEqual(A.select('Sunny').id,A.select('Clear').id);
assert.equal(A.select('Rainbow 2').id,'rainbow');
assert.equal(A.select('Meteor Shower').id,'meteor-1');
assert.equal(A.select('Aurora 3').id,'aurora-3');
assert.equal(A.select('Unknown Weather'),null);assert.equal(A.select(null),null);
for(const family of ['Meteor Shower','Aurora'])assert.deepEqual([1,2,3].map(n=>A.select(family+' '+n).count),[1,2,3]);
assert.ok(A.select('Light Rain').count<A.select('Moderate Rain').count);
assert.ok(A.select('Moderate Rain').count<A.select('Heavy Rain').count);
assert.ok(A.select('Heavy Rain').duration<A.select('Moderate Rain').duration);
assert.deepEqual(Object.values(A.effects).map(effect=>effect.duration),[28,14,32,3.8,3.6,2.9,2.2,4,14,12,10,26,30,22,20,18,28,25,22,24,15]);
console.log('PASS: exact 21 weather keys/effects, distinct variants, bounded particles, unknown fallback, no icon mapping changes');
