import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {features,predict,parseCSV} from '../docs/inference.mjs';
const read=p=>JSON.parse(readFileSync(new URL(p,import.meta.url),'utf8'));
const model=read('../docs/model.json');
test('browser forest agrees with sklearn serving predictions',()=>{
 for(const f of read('./serving-fixtures.json'))assert.ok(Math.abs(predict(model,f.x)-f.expected)<1e-10);
});
test('feature calculations agree with saved Python history',()=>{
 const d=read('../docs/results.json'),rows=d.cells.B0005.slice(0,10),x=features(rows);
 const fixture=read('./serving-fixtures.json')[0];
 x.forEach((v,i)=>assert.ok(Math.abs(v-fixture.x[i])<1e-10));
});
test('rejects missing, nonfinite and unordered measurements',()=>{
 assert.throws(()=>parseCSV('cycle,capacity,mean_temperature,peak_temperature\n1,,20,30'));
 assert.throws(()=>features([]));
 const rows=read('../docs/results.json').cells.B0005.slice(0,10);rows[1].cycle=999;
 assert.throws(()=>features(rows));
});
test('rejects out-of-domain inputs',()=>{
 const x=read('./serving-fixtures.json')[0].x;x[0]=70;
 assert.throws(()=>predict(model,x),/outside/);
});
test('example CSV produces a finite forecast',()=>{
 const rows=parseCSV(readFileSync(new URL('../docs/example.csv',import.meta.url),'utf8'));
 assert.ok(Number.isFinite(predict(model,features(rows))));
});
