"""Reproducible, battery-held-out capacity forecasting. No future features."""
from pathlib import Path
import csv
import hashlib
import json
import numpy as np
from scipy.io import loadmat
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.inspection import permutation_importance

ROOT = Path(__file__).resolve().parents[1]
CELLS = ['B0005', 'B0006', 'B0007', 'B0018']
HORIZON = 10
WINDOW = 10
FEATURES = ['capacity_ah', 'recent_mean_ah', 'recent_slope_ah_per_cycle',
            'recent_std_ah', 'cycle', 'mean_temperature_c', 'peak_temperature_c']


def features(history):
    if len(history) < WINDOW:
        raise ValueError('At least ten completed discharge cycles are required.')
    recent = history[-WINDOW:]
    caps = np.array([r['capacity'] for r in recent], dtype=float)
    last = recent[-1]
    values = [caps[-1], caps.mean(), np.polyfit(np.arange(WINDOW), caps, 1)[0],
              caps.std(), last['cycle'], last['mean_temperature'], last['peak_temperature']]
    if not np.isfinite(values).all() or (caps <= 0).any():
        raise ValueError('Capacity must be positive and all inputs finite.')
    if any(b['cycle'] != a['cycle'] + 1 for a, b in zip(recent, recent[1:])):
        raise ValueError('History must contain consecutive ordered discharge cycles.')
    return values


def samples(rows):
    return [(features(rows[:i+1]), rows[i+HORIZON]['capacity'], rows[i]['cycle'])
            for i in range(WINDOW-1, len(rows)-HORIZON)]


def forest():
    # Fixed before evaluation; predicting change stabilizes the capacity baseline.
    return RandomForestRegressor(n_estimators=200, min_samples_leaf=8,
                                 max_features=1.0, random_state=42, n_jobs=-1)


def metrics(y, p):
    return {'mae_ah': float(mean_absolute_error(y, p)),
            'rmse_ah': float(np.sqrt(mean_squared_error(y, p))),
            'mae_soh_percentage_points': float(mean_absolute_error(y, p)*50)}


def main():
    cells, hashes = {}, {}
    for cell in CELLS:
        path = ROOT / 'data/raw' / f'{cell}.mat'
        hashes[cell] = hashlib.sha256(path.read_bytes()).hexdigest()
        cycles = loadmat(path, simplify_cells=True)[cell]['cycle']
        rows = []
        for c in cycles:
            if c['type'] != 'discharge':
                continue
            d = c['data']
            cap = float(d['Capacity'])
            temps = np.asarray(d['Temperature_measured'], dtype=float)
            if not np.isfinite(cap) or cap <= 0 or not np.isfinite(temps).all():
                raise ValueError(f'Invalid observation in {cell}; refusing silent row removal.')
            rows.append({'cycle': len(rows)+1, 'capacity': cap,
                         'mean_temperature': float(temps.mean()),
                         'peak_temperature': float(temps.max())})
        cells[cell] = rows
    (ROOT / 'data/cycles.csv').parent.mkdir(exist_ok=True)
    with (ROOT / 'data/cycles.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['cell', *cells[CELLS[0]][0]])
        w.writeheader()
        for cell, rows in cells.items():
            w.writerows({'cell': cell, **r} for r in rows)
    sets = {cell: samples(rows) for cell, rows in cells.items()}
    predictions, folds, importance = [], [], []
    for held in CELLS:
        train = [s for cell, ss in sets.items() if cell != held for s in ss]
        test = sets[held]
        x, y = np.array([s[0] for s in train]), np.array([s[1] for s in train])
        xt, yt = np.array([s[0] for s in test]), np.array([s[1] for s in test])
        model = forest().fit(x, y-x[:, 0])
        pred = xt[:, 0]+model.predict(xt)
        baseline = xt[:, 0]
        trend = xt[:, 0]+HORIZON*xt[:, 2]
        folds.append({'held_out_cell': held, 'training_cells': [c for c in CELLS if c != held],
                      'n_train': len(train), 'n_test': len(test),
                      'forest': metrics(yt, pred), 'persistence': metrics(yt, baseline),
                      'linear_trend': metrics(yt, trend)})
        pi = permutation_importance(model, xt, yt-xt[:, 0], scoring='neg_mean_absolute_error',
                                    n_repeats=10, random_state=42)
        importance.append(pi.importances_mean)
        for s, p, b, t in zip(test, pred, baseline, trend):
            predictions.append({'cell': held, 'cycle': s[2], 'target_cycle': s[2]+HORIZON,
                                'actual': s[1], 'prediction': float(p),
                                'persistence': float(b), 'linear_trend': float(t)})
    actual = [r['actual'] for r in predictions]
    result = {'horizon': HORIZON, 'window': WINDOW, 'rated_capacity_ah': 2,
              'source': 'NASA PCoE, Saha & Goebel (2007)', 'raw_sha256': hashes,
              'features': FEATURES, 'cells': cells, 'predictions': predictions, 'folds': folds,
              'metrics': {name: metrics(actual, [r[key] for r in predictions]) for name, key in
                          [('forest', 'prediction'), ('persistence', 'persistence'), ('linear_trend', 'linear_trend')]},
              'permutation_importance_ah': dict(zip(FEATURES, np.mean(importance, axis=0).tolist()))}
    (ROOT/'docs/results.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    # Final serving model uses all cells; evaluation above never uses this model.
    all_samples = [s for ss in sets.values() for s in ss]
    x = np.array([s[0] for s in all_samples]); y = np.array([s[1] for s in all_samples])
    model = forest().fit(x, y-x[:, 0])
    trees = []
    for est in model.estimators_:
        t = est.tree_
        trees.append({'left': t.children_left.tolist(), 'right': t.children_right.tolist(),
                      'feature': t.feature.tolist(), 'threshold': t.threshold.tolist(),
                      'value': t.value[:, 0, 0].tolist()})
    artifact = {'features': FEATURES, 'horizon': HORIZON, 'trees': trees,
                'feature_min': x.min(axis=0).tolist(), 'feature_max': x.max(axis=0).tolist()}
    (ROOT/'docs/model.json').write_text(json.dumps(artifact, allow_nan=False))
    fixture = [{'x': row.tolist(), 'expected': float(row[0]+model.predict(row.reshape(1, -1))[0])}
               for row in x[::25]]
    (ROOT/'tests/serving-fixtures.json').write_text(json.dumps(fixture))
    with (ROOT/'docs/example.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(cells['B0005'][0]))
        w.writeheader(); w.writerows(cells['B0005'][40:50])
    print(json.dumps({'folds': folds, 'metrics': result['metrics']}, indent=2))


if __name__ == '__main__':
    main()
