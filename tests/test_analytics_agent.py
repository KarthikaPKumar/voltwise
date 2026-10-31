import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from service.semantic import ROOT, query_metrics, catalog
from service.agent import investigate, execute, ollama_chat, AgentError
from service.api import app
from fastapi.testclient import TestClient

def call(name, **args):
    return {'role': 'assistant', 'content': '', 'tool_calls': [{'function': {'name': name, 'arguments': args}}]}

class AnalyticsTests(unittest.TestCase):
    def test_sql_metrics_match_independent_python_evaluation(self):
        result = json.loads((ROOT/'docs/results.json').read_text())
        for cell in ['__all__', 'B0005', 'B0006', 'B0007', 'B0018']:
            rows = [r for r in result['predictions'] if cell == '__all__' or r['cell'] == cell]
            mae = sum(abs(r['prediction']-r['actual']) for r in rows)/len(rows)
            baseline = sum(abs(r['persistence']-r['actual']) for r in rows)/len(rows)
            output = query_metrics(['mae_ah', 'improvement_pct', 'forecast_count'], cell)['metrics']
            self.assertAlmostEqual(mae, output['mae_ah']['value'])
            self.assertAlmostEqual(100*(1-mae/baseline), output['improvement_pct']['value'])
            self.assertEqual(len(rows), output['forecast_count']['value'])

    def test_unknown_metric_sql_and_dimensions_rejected(self):
        for metrics, cell in [(['mae_ah; drop table cycles'], '__all__'), (['mae_ah'], "x' OR 1=1--"),
                              ([], '__all__'), (['mae_ah', 'mae_ah'], '__all__')]:
            with self.assertRaises(ValueError): query_metrics(metrics, cell)

    def test_snapshot_contains_passing_tests_and_lineage(self):
        data = json.loads((ROOT/'docs/analytics.json').read_text())
        self.assertEqual(data['quality']['failed'], 0)
        self.assertGreaterEqual(data['quality']['passed'], 13)
        self.assertEqual(len(data['lineage']), 5)
        self.assertEqual(data['catalog'], catalog())

class AgentTests(unittest.TestCase):
    def test_model_can_select_tools_observe_and_answer(self):
        replies = iter([call('list_metrics'), call('query_metrics', metrics=['mae_ah'], cell='B0005'),
                        {'role': 'assistant', 'content': 'See the dbt:mart_metrics evidence for laboratory forecast error.'}])
        seen = []
        def chat(messages):
            seen.append(json.loads(json.dumps(messages)))
            return next(replies)
        r = investigate('What is B0005 error?', chat)
        self.assertEqual(len(r['trace']), 2)
        self.assertEqual(r['evidence'][1]['cell'], 'B0005')
        self.assertTrue(any(m['role'] == 'tool' for m in seen[-1]))

    def test_ungrounded_answer_is_not_presented_as_success(self):
        with self.assertRaises(AgentError): investigate('What is the error?', lambda _: {'content': '99% accurate'})

    def test_catalog_only_is_not_an_evidence_backed_answer(self):
        replies = iter([call('list_metrics'), {'role': 'assistant', 'content': 'I will look it up.'}])
        with self.assertRaises(AgentError): investigate('What is the error?', lambda _: next(replies))

    def test_invalid_metric_can_be_corrected_without_executing_it(self):
        replies = iter([call('query_metrics', metrics=['forecast_mae']),
                        call('query_metrics', metrics=['mae_ah'], cell='B0005'),
                        {'role': 'assistant', 'content': 'The verified metric is in dbt:mart_metrics.'}])
        r = investigate('Get forecast error', lambda _: next(replies))
        self.assertEqual(r['trace'][0]['source'], 'tool_validation')
        self.assertEqual(len(r['evidence']), 1)
        self.assertEqual(r['evidence'][0]['cell'], 'B0005')

    def test_truncated_model_output_is_rejected(self):
        with patch.dict(os.environ, {'VOLTWISE_OLLAMA_MODEL': 'test-model'}), patch('service.agent.httpx.post') as post:
            post.return_value.json.return_value = {'done_reason': 'length', 'message': {'content': 'Incomplete answer'}}
            with self.assertRaises(AgentError): ollama_chat([])

    def test_agent_rejects_write_tool_and_arbitrary_sql(self):
        with self.assertRaises(AgentError): investigate('Delete data', lambda _: call('run_sql', sql='drop table cycles'))
        with self.assertRaises(ValueError): execute('read_context', {'topic': '../../etc/passwd'})

    def test_loop_is_bounded(self):
        with self.assertRaises(AgentError): investigate('Keep investigating', lambda _: call('list_metrics'))

    def test_invalid_tool_arguments_and_long_prompts_rejected(self):
        with self.assertRaises(AgentError): investigate('Question', lambda _: call('query_metrics', metrics=['unknown']))
        with self.assertRaises(ValueError): investigate('x'*1501)

    def test_local_api_validation_and_missing_model(self):
        client = TestClient(app)
        self.assertEqual(client.get('/api/metrics/mae_ah').status_code, 200)
        self.assertEqual(client.get('/api/metrics/invented').status_code, 400)
        self.assertEqual(client.post('/api/agent', json={'question': '', 'sql': 'select 1'}).status_code, 422)
        self.assertEqual(client.post('/api/agent', json={'question': 'test'}, headers={'origin': 'https://other.example'}).status_code, 403)
        with patch.dict(os.environ, {}, clear=True):
            r = client.post('/api/agent', json={'question': 'Compare models'})
            self.assertEqual(r.status_code, 503)
            self.assertIn('not configured', r.json()['detail'])

if __name__ == '__main__': unittest.main()
