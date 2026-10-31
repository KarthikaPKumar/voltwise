# Voltwise

An applied data-science project by Kathy: forecast lithium-ion cell capacity **ten discharge cycles ahead** using real NASA laboratory data. Designed to illustrate battery analytics relevant to EV manufacturers, energy-storage teams and fleet operators. Independent project; no affiliation with Tesla or NASA.

## What is built

- Reproducible extraction from four NASA MATLAB files into `data/cycles.csv` (636 completed discharge cycles).
- Rolling history features, a random forest that predicts capacity change, persistence and linear-trend baselines.
- Leave-one-battery-out evaluation: every test battery is entirely excluded from its fold's training set.
- An interactive static dashboard, held-out forecasts, per-cell errors, permutation importance, and browser-local CSV inference with training-range checks.
- A portable JSON model, data fingerprints, automated tests and a model card. The public demo needs no cloud account, API key or paid service. Its build uses an embedded DuckDB database.

## Analytics and AI extension

The project now includes **dbt + DuckDB**, a shared semantic metric catalogue, a **FastAPI** read-only metrics service, and an optional **Ollama tool-calling agent**. The dashboard exposes eight named metrics and guided investigations, with SQL definitions, test evidence and data lineage.

Run `python scripts/build_analytics.py` after installing requirements. It builds two seeds, three models and 13 dbt tests, then publishes `docs/analytics.json`. CI runs the same pipeline before deploying. To run the optional local AI edition, follow [ARCHITECTURE.md](ARCHITECTURE.md). A local tool-capable model must be installed and configured separately; the public GitHub Pages site does not host an LLM.

The semantic layer is a custom catalogue built on dbt, not a hosted MetricFlow service. Public guided answers are deterministic and labelled accordingly. The actual local agent chooses tools, observes evidence and returns a sourced interpretation; automated unit tests use a mock model, with real-model checks recorded separately. Generated interpretations still need review.

## Results

560 held-out forecasts from **four independent cells**, with fixed hyperparameters and no tuning on these test folds:

| Model | MAE (Ah) | RMSE (Ah) |
| --- | ---: | ---: |
| Random forest capacity change | 0.02408 | 0.03307 |
| Persistence | 0.04358 | 0.05272 |
| Recent linear trend | 0.04563 | 0.06007 |

The random forest has 44.7% lower pooled MAE than persistence, and lower MAE in all four folds. The mean error is 1.20 percentage points of the 2 Ah rated capacity. These are exploratory laboratory results, not evidence of vehicle performance or business savings. Overlapping windows are correlated; the sample size at battery level is four. See `docs/results.json` for full per-cell results and raw-file SHA-256 hashes.

## Reproduce

Python 3.14 was used for the pinned environment. From this directory:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/download.py
python scripts/train.py
python scripts/build_analytics.py
python -m unittest discover -s tests -p 'test_*.py'
node --test tests/*.test.mjs
python -m http.server 8766 --directory docs
```

Open http://localhost:8766. Training writes the dashboard results and the all-cell serving model; the serving model is never used to compute held-out evaluation scores. The download retrieves the approximately 56 MB nested archive from NASA's linked public mirror. Raw binaries are ignored by Git. `data/raw/README.txt` preserves the supplied data description; `data/cycles.csv` is a reproducible numeric derivative.

## Intended industrial workflow

1. Collect representative cell/pack telemetry, diagnostic capacities and operating conditions with clear units and provenance.
2. Forecast health and rank assets for diagnostic inspection; combine results with engineering rules.
3. Validate on unseen packs, vehicle families and later time periods; calibrate uncertainty and measure false alarms.
4. Monitor data quality, forecast error and drift before considering operational decisions.

This prototype implements a small laboratory analogue of steps 1–2. It does **not** model remaining useful life, battery safety, vehicle range, warranty outcomes or optimal charging. Inspection thresholds are illustrative user settings. It cannot turn limited laboratory data into a Tesla-ready production model.

## Data provenance

B. Saha and K. Goebel (2007), “Battery Data Set”, NASA Ames Prognostics Data Repository, NASA Ames Research Center, Moffett Field, CA.

Official source: https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/

Archive: https://phm-datasets.s3.amazonaws.com/NASA/5.%20Battery%20Data%20Set.zip

Selected cells: B0005, B0006, B0007 and B0018. Their different laboratory discharge cut-offs limit comparability. Source attribution is retained; NASA names and marks are not used to imply endorsement.
