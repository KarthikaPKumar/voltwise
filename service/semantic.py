"""Read-only access to named metrics. No caller-supplied SQL is accepted."""
from pathlib import Path
import hashlib
import json
import duckdb
import yaml

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT/'warehouse/voltwise.duckdb'
CELLS = ('B0005', 'B0006', 'B0007', 'B0018', '__all__')

def catalog():
    return yaml.safe_load((ROOT/'analytics/dbt_project.yml').read_text())['vars']['semantic_metrics']

def query_metrics(metrics, cell='__all__'):
    definitions = catalog()
    if not isinstance(metrics, list) or not 1 <= len(metrics) <= 8:
        raise ValueError('Request between one and eight named metrics.')
    if any(not isinstance(m, str) or m not in definitions for m in metrics) or cell not in CELLS:
        raise ValueError('Unknown metric or cell. Use the catalogue.')
    if len(set(metrics)) != len(metrics):
        raise ValueError('Duplicate metrics are not allowed.')
    snapshot = json.loads((ROOT/'docs/analytics.json').read_text())
    if snapshot['catalog'] != definitions:
        raise ValueError('Metric definitions changed. Rebuild analytics first.')
    if snapshot['source_sha256'] != hashlib.sha256((ROOT/'docs/results.json').read_bytes()).hexdigest():
        raise ValueError('Analytics is stale relative to model results. Rebuild first.')
    # SQL identifiers come only from checked-in definitions, never model/user text.
    sql = 'select '+', '.join('"'+m+'"' for m in metrics)+' from mart_metrics where cell = ?'
    with duckdb.connect(str(DB), read_only=True) as conn:
        row = conn.execute(sql, [cell]).fetchone()
    if row is None:
        raise ValueError('No metric data for this cell.')
    published = next(r for r in snapshot['rows'] if r['cell'] == cell)
    for name, value in zip(metrics, row):
        expected = published[name]
        if (value is None) != (expected is None) or (value is not None and abs(value-expected) > 1e-10):
            raise ValueError('Warehouse differs from verified snapshot. Rebuild analytics first.')
    return {'cell': cell, 'metrics': {m: {'value': v, 'unit': definitions[m]['unit'],
             'definition': definitions[m]['description']} for m, v in zip(metrics, row)},
            'source': 'dbt:mart_metrics', 'snapshot': snapshot['generated_at']}

def read_context(topic):
    paths = {'model': ROOT/'MODEL_CARD.md', 'architecture': ROOT/'ARCHITECTURE.md'}
    if topic not in paths:
        raise ValueError('Choose model or architecture.')
    return {'source': paths[topic].name, 'text': paths[topic].read_text()[:14000]}
