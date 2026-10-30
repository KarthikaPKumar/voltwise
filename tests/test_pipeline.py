import json
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from train import features, samples, ROOT

class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = json.loads((ROOT/'docs/results.json').read_text())

    def test_future_changes_cannot_change_features(self):
        rows = self.result['cells']['B0005']
        before = samples(rows)
        changed = [dict(r) for r in rows]
        for r in changed[50:]:
            r['capacity'] = 0.9
            r['mean_temperature'] = 99
        after = samples(changed)
        for i in range(41):
            np.testing.assert_allclose(before[i][0], after[i][0])

    def test_all_test_cells_excluded_from_training(self):
        for f in self.result['folds']:
            self.assertNotIn(f['held_out_cell'], f['training_cells'])
            self.assertEqual(len(f['training_cells']), 3)

    def test_target_is_ten_cycles_later(self):
        for p in self.result['predictions']:
            self.assertEqual(p['target_cycle'], p['cycle']+10)
            self.assertEqual(p['actual'], self.result['cells'][p['cell']][p['target_cycle']-1]['capacity'])

    def test_reported_error_recomputed(self):
        p = self.result['predictions']
        expected = np.mean([abs(r['prediction']-r['actual']) for r in p])
        self.assertAlmostEqual(expected, self.result['metrics']['forest']['mae_ah'])

    def test_invalid_history_rejected(self):
        with self.assertRaises(ValueError): features([])
        rows = [dict(r) for r in self.result['cells']['B0005'][:10]]
        rows[3]['cycle'] = 99
        with self.assertRaises(ValueError): features(rows)

if __name__ == '__main__': unittest.main()
