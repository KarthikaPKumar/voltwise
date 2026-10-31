# Voltwise analytics and AI architecture

## Running systems

`NASA measurements → Python feature extraction / held-out model evaluation → CSV seeds → dbt → DuckDB → validated metrics snapshot → GitHub Pages dashboard`

`Local question → FastAPI → Ollama model → allowed read-only tools → DuckDB metrics / project documentation → model interpretation + evidence trace`

The public Pages site runs the trained random forest in JavaScript and displays dbt-built metrics. Its guided investigation interface is a **deterministic workflow, not a language model or autonomous agent**. The local edition adds the actual model-directed tool loop. No API keys are embedded in the website, and public pages never probe localhost.

## dbt and semantic layer

Two CSV seeds feed three materialised DuckDB models: `stg_cycles`, `fct_forecasts`, `mart_metrics`. Thirteen dbt tests check uniqueness, nulls, population counts, numeric validity and alignment of forecast targets with NASA measurements. The export only replaces the public JSON after a successful build and tests. Lineage and the run invocation ID accompany the snapshot.

The canonical metric catalogue lives in `analytics/dbt_project.yml → vars.semantic_metrics`. Its SQL expressions are used directly by dbt and exported with labels, definitions and units. The API only exposes allowlisted metric names and cell dimensions. This is a **custom lightweight semantic layer built on dbt**, not the hosted dbt Semantic Layer or a MetricFlow query service. No paid dbt account is required.

All metrics have a forecast-window grain. `__all__` is calculated from raw forecast rows, so improvement is the ratio of pooled errors, not an unweighted average of cell percentages. Below-threshold flag rates refer to overlapping historical windows at a fixed illustrative 1.6 Ah threshold. The independent explorer slider does not change the governed 80% metric definition. There are no live fleet records or operating savings metrics.

## Agentic AI

The local agent uses Ollama's tool-calling API. The model selects `list_metrics`, `query_metrics` and `read_context`, observes results and can request additional evidence before answering. At most five model rounds and eight tool calls are allowed. Each model request has a 45-second timeout; the loop checks a 150-second wall-time budget between requests. One request can overrun that budget by its timeout. Only one investigation runs at once.

The agent cannot execute arbitrary SQL, shell commands, file paths, web requests, data mutations, retraining or deployment. The warehouse connection is read-only. Host/origin checks and a loopback-only launch command keep the local service separate from public hosting. No prompt or answer is persisted by this application. Ollama has its own operating settings.

The response includes tool arguments, sources and elapsed time. Tool results are validated, but generated prose is not automatically fact-checked; even with evidence and instructions, a language model can misstate numbers or scope. This is not a production security boundary, clinical/safety tool or autonomous maintenance decision-maker. Do not expose the unauthenticated local service publicly.

## Start the local edition

On the configured Mac, double-click `Start Voltwise.command`, then open http://127.0.0.1:8766/#local-agent. Keep the launcher window open while using the assistant. It starts Qwen2.5 7B through Ollama and the local web service. Control-C stops the services it started; an Ollama instance already running before the launcher is left alone. The model is stored by Ollama on this computer and is not uploaded to GitHub.

The default is `qwen2.5:7b` (approximately 4.7 GB), with tool calling, an 8,192-token context and short final responses. Override `VOLTWISE_OLLAMA_MODEL` only with an installed compatible model. The launcher disables Ollama cloud features when it starts the model server.

For a fresh checkout:

```sh
pip install -r requirements.txt
python scripts/build_analytics.py
# Install Ollama separately and download a tool-capable local model of your choice.
# Set this to the exact installed model name; no model is downloaded automatically.
export VOLTWISE_OLLAMA_MODEL=your-installed-model
uvicorn service.api:app --host 127.0.0.1 --port 8766
```

Open http://127.0.0.1:8766 for the dashboard and local AI form. API documentation: http://127.0.0.1:8766/api/docs. Missing or unavailable models produce an explicit unavailable response, never a simulated AI answer. Model downloads may be large and memory requirements depend on your choice.

## Observability and verification

The public analytics JSON carries data-test counts, dbt lineage, build time and the model-results checksum. Each agent response carries its tool trace and latency. These are build/interaction diagnostics, not continuous live production monitoring. CI rebuilds the warehouse and snapshot, tests the API/tools and checks that SQL metrics match Python evaluation. Mock-model tests exercise agent decisions, bounds and errors. A real Qwen2.5 7B smoke test on 31 October 2026 retrieved and correctly compared B0005 and B0018 MAE in about 13 seconds; evidence is in `reports/local-ai-smoke.json`. This limited check does not establish general answer accuracy. Qwen3 4B failed completion tests in this environment and is not the default. Truncated output and catalogue-only answers are rejected; invalid tool arguments receive bounded correction feedback without executing the invalid request.

References: https://github.com/duckdb/dbt-duckdb and https://docs.ollama.com/capabilities/tool-calling
