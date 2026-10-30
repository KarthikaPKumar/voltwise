export function features(rows){
 if(rows.length<10)throw Error('Provide at least ten completed cycles.');
 const r=rows.slice(-10), c=r.map(x=>x.capacity);
 if(r.some(x=>!['cycle','capacity','mean_temperature','peak_temperature'].every(k=>Number.isFinite(x[k]))||x.capacity<=0||!Number.isInteger(x.cycle)||x.cycle<1||x.peak_temperature<x.mean_temperature))throw Error('Use finite measurements, positive capacity and valid cycle numbers. Peak temperature must be at least the mean.');
 if(r.some((x,i)=>i&&x.cycle!==r[i-1].cycle+1))throw Error('Cycles must be consecutive and ordered.');
 const mean=c.reduce((a,b)=>a+b,0)/10;
 const slope=c.reduce((s,v,i)=>s+(i-4.5)*(v-mean),0)/82.5;
 return [c[9],mean,slope,Math.sqrt(c.reduce((s,v)=>s+(v-mean)**2,0)/10),r[9].cycle,r[9].mean_temperature,r[9].peak_temperature];
}
export function predict(model,x){
 if(x.length!==model.features.length||x.some(v=>!Number.isFinite(v)))throw Error('Invalid feature vector.');
 const out=x.some((v,i)=>v<model.feature_min[i]-1e-9||v>model.feature_max[i]+1e-9);
 if(out)throw Error('This history is outside the model’s laboratory training ranges. Prediction withheld.');
 const f=x.map(Math.fround);
 const delta=model.trees.reduce((s,t)=>{let n=0;while(t.left[n]!==-1)n=f[t.feature[n]]<=t.threshold[n]?t.left[n]:t.right[n];return s+t.value[n]},0)/model.trees.length;
 return x[0]+delta;
}
export function parseCSV(text){
 const lines=text.trim().split(/\r?\n/),headers=lines.shift().replace(/^\uFEFF/,'').split(',').map(s=>s.trim());
 const keys=['cycle','capacity','mean_temperature','peak_temperature'];
 if(keys.some(k=>!headers.includes(k))||new Set(headers).size!==headers.length)throw Error('CSV must include unique cycle, capacity, mean_temperature and peak_temperature columns.');
 return lines.map(line=>{const v=line.split(',');if(v.length!==headers.length)throw Error('CSV row has the wrong number of columns.');return Object.fromEntries(keys.map(k=>{const s=v[headers.indexOf(k)].trim();if(!s)throw Error('Missing measurement.');return [k,Number(s)]}));});
}
