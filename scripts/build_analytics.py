"""Build tested dbt marts, then atomically export a traceable public snapshot."""
from pathlib import Path
import csv
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
import duckdb
import yaml

ROOT = Path(__file__).resolve().parents[1]

def main():
    project = ROOT/'analytics'
    (ROOT/'warehouse').mkdir(exist_ok=True)
    (project/'seeds').mkdir(exist_ok=True)
    result = json.loads((ROOT/'docs/results.json').read_text())
    with (project/'seeds/forecasts.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(result['predictions'][0]))
        writer.writeheader(); writer.writerows(result['predictions'])
    env = dict(os.environ, VOLTWISE_DB_PATH=str(ROOT/'warehouse/voltwise.duckdb'),
               DBT_SEND_ANONYMOUS_USAGE_STATS='false')
    exe = str(Path(sys.executable).parent/'dbt')
    subprocess.run([exe, 'build', '--profiles-dir', '.', '--no-use-colors'],
                   cwd=project, env=env, check=True)
    run = json.loads((project/'target/run_results.json').read_text())
    manifest = json.loads((project/'target/manifest.json').read_text())
    tests = [r for r in run['results'] if r['unique_id'].startswith('test.')]
    if not tests or any(t['status'] != 'pass' for t in tests):
        raise RuntimeError('Refusing to publish unverified analytics.')
    with duckdb.connect(str(ROOT/'warehouse/voltwise.duckdb'), read_only=True) as conn:
        cur = conn.execute('select * from mart_metrics order by cell')
        columns = [d[0] for d in cur.description]
        rows = [dict(zip(columns, row)) for row in cur.fetchall()]
    catalog = yaml.safe_load((project/'dbt_project.yml').read_text())['vars']['semantic_metrics']
    payload = {'generated_at': datetime.now(timezone.utc).isoformat(),
               'mode': 'offline laboratory evaluation snapshot',
               'source_sha256': hashlib.sha256((ROOT/'docs/results.json').read_bytes()).hexdigest(),
               'catalog': catalog, 'rows': rows,
               'quality': {'passed': len(tests), 'failed': 0, 'invocation_id': run['metadata']['invocation_id']},
               'lineage': [{'name': n['name'], 'type': n['resource_type'],
                            'depends_on': n.get('depends_on', {}).get('nodes', [])}
                           for n in manifest['nodes'].values() if n['resource_type'] in ['model', 'seed']]}
    target = ROOT/'docs/analytics.json'
    temp = target.with_suffix('.tmp')
    temp.write_text(json.dumps(payload, indent=2, allow_nan=False)+'\n');temp.replace(target)
    print(f'Published analytics snapshot: {len(tests)} dbt tests passed.')

if __name__ == '__main__': main()
