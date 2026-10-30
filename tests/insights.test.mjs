import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {investigate} from '../docs/insights.mjs';
const snapshot=JSON.parse(readFileSync(new URL('../docs/analytics.json',import.meta.url)));
test('guided workflow returns actual metric evidence for the selected scope',()=>{
 const r=investigate(snapshot,'performance','B0005');
 assert.equal(r.evidence[0].value,snapshot.rows.find(r=>r.cell==='B0005').mae_ah);
 assert.match(r.summary,/B0005/);assert.equal(r.trace.length,4);
});
test('hardest-cell comparison uses all cells and correct ranking',()=>{
 const r=investigate(snapshot,'hardest','B0005');assert.match(r.summary,/B0018/);
 assert.equal(r.evidence.length,4);assert.ok(r.evidence[0].value>=r.evidence[1].value);
});
test('inspection flags describe windows and fixed threshold, not vehicles',()=>{
 const r=investigate(snapshot,'flags');assert.match(r.summary,/overlapping windows/);
 assert.equal(r.evidence[0].name,'review_flag_rate_pct');
});
test('quality uses build evidence and rejects unsupported questions or cells',()=>{
 assert.match(investigate(snapshot,'quality').summary,/13 dbt/);
 assert.throws(()=>investigate(snapshot,'make up savings'));
 assert.throws(()=>investigate(snapshot,'flags','unknown'));
});
