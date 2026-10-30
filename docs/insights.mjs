export function investigate(snapshot, intent, cell='__all__') {
 const row=snapshot.rows.find(r=>r.cell===cell);
 if(!row)throw Error('Unknown battery scope.');
 const get=(key,r=row)=>({name:key,label:snapshot.catalog[key].label,value:r[key],unit:snapshot.catalog[key].unit,definition:snapshot.catalog[key].description,cell:r.cell});
 let evidence=[],summary='';
 if(intent==='performance'){
  evidence=['mae_ah','baseline_mae_ah','improvement_pct','forecast_count'].map(k=>get(k));
  summary=`For ${cell==='__all__'?'all four laboratory cells':cell}, the model has ${Math.abs(row.improvement_pct).toFixed(1)}% ${row.improvement_pct>=0?'lower':'higher'} error than persistence across ${row.forecast_count} held-out forecast windows.`;
 }else if(intent==='hardest'){
  const ranked=snapshot.rows.filter(r=>r.cell!=='__all__').sort((a,b)=>b.mae_ah-a.mae_ah);
  evidence=ranked.map(r=>get('mae_ah',r));
  summary=`${ranked[0].cell} has the largest mean absolute error (${ranked[0].mae_ah.toFixed(3)} Ah). This compares all four cells, regardless of the scope selector. It indicates forecast difficulty, not battery danger.`;
 }else if(intent==='flags'){
  evidence=['review_flag_rate_pct','flag_precision_pct','forecast_count'].map(k=>get(k));
  summary=`${row.review_flag_rate_pct.toFixed(1)}% of historical forecast windows in this scope fall below the illustrative 80% capacity threshold. These are overlapping windows, not unique fleet assets or replacement recommendations.`;
 }else if(intent==='quality'){
  summary=`${snapshot.quality.passed} dbt data tests passed with ${snapshot.quality.failed} failures when this snapshot was built. Tests cover keys, row counts, finite measurements and ten-cycle target alignment. Passing data tests does not establish model accuracy on vehicles.`;
 }else throw Error('Choose one of the supported investigations.');
 return {summary,evidence,trace:['Select documented investigation', 'Resolve metric definitions and units', 'Read dbt-validated aggregate snapshot', 'Return evidence and scope limits'],source:'dbt:mart_metrics',generated_at:snapshot.generated_at};
}

if(typeof document!=='undefined'){
 const $=s=>document.querySelector(s);
 const value=(v)=>v===null?'Not defined':Number.isInteger(v)?String(v):v.toFixed(3);
 const node=(tag,text)=>{const el=document.createElement(tag);el.textContent=text;return el;};
 try{
  const response=await fetch('analytics.json');if(!response.ok)throw Error('Analytics snapshot unavailable.');
  const snapshot=await response.json();
  $('#quality-status').textContent=`${snapshot.quality.passed} checks passed · Built ${new Date(snapshot.generated_at).toLocaleString()} · Historical laboratory data`;
  for(const [id,metric]of Object.entries(snapshot.catalog)){const o=node('option',metric.label);o.value=id;$('#metric-choice').append(o);}
  function renderMetric(){
   const id=$('#metric-choice').value,cell=$('#metric-cell').value,r=snapshot.rows.find(r=>r.cell===cell),m=snapshot.catalog[id];
   $('#metric-value').textContent=`${value(r[id])} ${m.unit}`;
   $('#metric-definition').textContent=m.description;
   $('#metric-formula').textContent=m.expression;
  }
  $('#metric-choice').addEventListener('change',renderMetric);$('#metric-cell').addEventListener('change',renderMetric);renderMetric();
  for(const step of snapshot.lineage){const li=node('li',step.name+' ← '+(step.depends_on.map(n=>n.split('.').at(-1)).join(', ')||'source CSV'));$('#lineage-list').append(li);}
  $('#run-investigation').addEventListener('click',()=>{
   const result=investigate(snapshot,$('#investigation-choice').value,$('#metric-cell').value);
   $('#investigation-summary').textContent=result.summary;
   const evidence=$('#investigation-evidence');evidence.replaceChildren();
   for(const e of result.evidence){const row=node('p',`${e.cell==='__all__'?'All cells':e.cell} · ${e.label}: ${value(e.value)} ${e.unit}`);evidence.append(row);}
   $('#investigation-trace').replaceChildren(...result.trace.map(s=>node('li',s)));
  });
 }catch(e){$('#quality-status').textContent=e.message;$('#run-investigation').disabled=true;}
 // Never probe a visitor's localhost from the public website.
 if(['127.0.0.1','localhost'].includes(location.hostname)){
  try{
   const r=await fetch('/api/status');if(r.ok){const status=await r.json();$('#local-agent').hidden=false;
    $('#agent-status').textContent=status.model_configured?`Local model configured: ${status.model}. Availability is checked when you ask.`:'Local AI is not configured. See the repository setup guide.';
    $('#ask-agent').disabled=!status.model_configured;
   }
  }catch{}
 }
 $('#agent-form').addEventListener('submit',async e=>{
  e.preventDefault();$('#ask-agent').disabled=true;$('#agent-answer').textContent='Investigating with read-only tools…';
  try{const r=await fetch('/api/agent',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:$('#agent-question').value})});const answer=await r.json();if(!r.ok)throw Error(typeof answer.detail==='string'?answer.detail:'Unable to run investigation.');
   $('#agent-answer').textContent=answer.answer+'\n\n'+answer.notice;
   $('#agent-evidence').textContent=JSON.stringify({evidence:answer.evidence,trace:answer.trace,elapsed_ms:answer.elapsed_ms},null,2);
  }catch(err){$('#agent-answer').textContent=err.message;}finally{$('#ask-agent').disabled=false;}
 });
}
