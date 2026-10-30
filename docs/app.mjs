import{features,predict,parseCSV}from'./inference.mjs';
const $=s=>document.querySelector(s);let data;
const fmt=n=>n.toFixed(3),pct=n=>(n/2*100).toFixed(1);
try{
 const response=await fetch('results.json');if(!response.ok)throw Error('Results unavailable');data=await response.json();
 const m=data.metrics;
 $('#metrics').innerHTML=`<div class="metric"><strong>4</strong><span>Independent laboratory cells</span></div><div class="metric"><strong>${data.predictions.length}</strong><span>Held-out forecasts</span></div><div class="metric"><strong>${fmt(m.forest.mae_ah)} Ah</strong><span>Random forest mean absolute error</span></div><div class="metric"><strong>10 cycles</strong><span>Forecast horizon</span></div>`;
 $('#cell').innerHTML=Object.keys(data.cells).map(c=>`<option>${c}</option>`).join('');
 $('#scores').innerHTML=data.folds.map(f=>`<tr><td>${f.held_out_cell}</td><td>${f.n_test}</td><td>${fmt(f.forest.mae_ah)}</td><td>${fmt(f.persistence.mae_ah)}</td><td>${fmt(f.linear_trend.mae_ah)}</td></tr>`).join('')+`<tr><th>Pooled</th><td>${data.predictions.length}</td><td>${fmt(m.forest.mae_ah)}</td><td>${fmt(m.persistence.mae_ah)}</td><td>${fmt(m.linear_trend.mae_ah)}</td></tr>`;
 const improvement=100*(1-m.forest.mae_ah/m.persistence.mae_ah);
 $('#comparison').textContent=`The random forest has ${Math.abs(improvement).toFixed(1)}% ${improvement>=0?'lower':'higher'} pooled error than persistence. Its average error equals ${m.forest.mae_soh_percentage_points.toFixed(2)} percentage points of rated capacity. Results vary by battery; no vehicle-level performance is established.`;
 $('#importance').innerHTML=Object.entries(data.permutation_importance_ah).sort((a,b)=>b[1]-a[1]).map(([k,v])=>`<p><span>${k.replaceAll('_',' ')}</span><strong>${v.toFixed(4)} Ah</strong></p>`).join('');
 function render(){
 const cell=$('#cell').value,rows=data.cells[cell];$('#cycle').max=rows.length-10;
 const cycle=Math.min(Number($('#cycle').value),rows.length-10);$('#cycle').value=cycle;$('#cycle-value').textContent=cycle;
 const p=data.predictions.find(p=>p.cell===cell&&p.cycle===cycle),reveal=$('#reveal').checked;
 const x=n=>65+(n-1)/(rows.length-1)*900,y=n=>290-(n-1.1)/1.05*250;
 const path=r=>r.map((v,i)=>`${i?'L':'M'}${x(v.cycle)},${y(v.capacity)}`).join(' ');
 let svg='';for(const v of [1.2,1.4,1.6,1.8,2.0])svg+=`<line x1="65" x2="965" y1="${y(v)}" y2="${y(v)}" stroke="#e4e7eb"/><text x="12" y="${y(v)+4}" font-size="12" fill="#606a7b">${v.toFixed(1)} Ah</text>`;
 for(let i=20;i<=rows.length;i+=20)svg+=`<text x="${x(i)}" y="320" text-anchor="middle" font-size="12" fill="#606a7b">${i}</text>`;
 if(reveal)svg+=`<path d="${path(rows)}" fill="none" stroke="#bfc6cf" stroke-width="2"/>`;
 svg+=`<path d="${path(rows.slice(0,cycle))}" fill="none" stroke="#252c36" stroke-width="3"/><line x1="${x(cycle)}" x2="${x(cycle)}" y1="30" y2="290" stroke="#929bab" stroke-dasharray="4 4"/><line x1="${x(cycle)}" x2="${x(p.target_cycle)}" y1="${y(p.persistence)}" y2="${y(p.prediction)}" stroke="#315dd1" stroke-width="2" stroke-dasharray="5 5"/><circle cx="${x(p.target_cycle)}" cy="${y(p.persistence)}" r="5" fill="#fff" stroke="#788395" stroke-width="2"/><circle cx="${x(p.target_cycle)}" cy="${y(p.prediction)}" r="6" fill="#315dd1"/><text x="${x(cycle)+8}" y="24" font-size="12" fill="#315dd1">Forecast origin: ${cycle}</text>`;
 $('#chart').innerHTML=svg;
 $('#forecast').innerHTML=`<div><strong>${pct(p.persistence)}%</strong><span>Measured health at cycle ${cycle}</span></div><div><strong>${pct(p.prediction)}%</strong><span>Predicted at cycle ${p.target_cycle}</span></div><div><strong>${reveal?pct(p.actual)+'%':'Hidden'}</strong><span>${reveal?'Observed at target cycle':'Reveal future to compare'}</span></div>`;
 const threshold=Number($('#threshold').value);$('#threshold-value').textContent=threshold+'%';
 $('#inspection').textContent=p.prediction/2*100<threshold?`Forecast falls below your ${threshold}% threshold. In a validated operational system, this could prompt a diagnostic review.`:`Forecast remains above your ${threshold}% threshold. This is not a statement about battery safety.`;
 }
 for(const id of ['cell','cycle','reveal','threshold'])$('#'+id).addEventListener('input',render);render();
}catch(e){$('#metrics').textContent='Unable to load model results. '+e.message;}
$('#upload').addEventListener('change',async e=>{const out=$('#custom-result');try{const f=e.target.files[0];if(!f)return;if(f.size>1e6)throw Error('Please use a CSV smaller than 1 MB.');const rows=parseCSV(await f.text());const response=await fetch('model.json');if(!response.ok)throw Error('Model unavailable');const model=await response.json();const p=predict(model,features(rows));out.className='';out.textContent=`Predicted capacity at discharge cycle ${rows.at(-1).cycle+10}: ${fmt(p)} Ah (${pct(p)}% of rated 2 Ah). Research estimate without a calibrated uncertainty interval.`;}catch(err){out.className='error';out.textContent=err.message;}});
