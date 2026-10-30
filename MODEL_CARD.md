# Voltwise model card

## Task and scope
Predict measured discharge capacity in Ah at cycle t+10, after observing the completed discharge at t. Health is reported as capacity / 2 Ah × 100. This is short-horizon capacity forecasting, not remaining useful life prediction. Calendar age and future operating conditions are not modelled.

## Data
NASA PCoE cells B0005, B0006, B0007 (168 discharges each), B0018 (132): 636 rows. Only discharge operations are used. Capacity and current-cycle mean/maximum temperature are extracted directly. Invalid measurements cause training to fail instead of silently dropping cycles. The original source README and raw hashes are retained. No Tesla data is used.

## Features and training
Features are current capacity, trailing-ten capacity mean/slope/standard deviation, discharge-cycle index, and current-cycle mean/maximum temperature. All features are available at the forecast origin. Capacity is a measured diagnostic input, so the system does not estimate health solely from raw operational telemetry.

RandomForestRegressor: 200 trees, min_samples_leaf=8, max_features=1.0, seed=42. The regression target is future minus current capacity. Parameters were fixed before the reported evaluation. Future predictions add the predicted change to current capacity. No hyperparameter search or model selection on held-out folds was performed.

## Evaluation
Four leave-one-cell-out folds, 560 eligible windows. Each fold trains on three entire cells and tests on the fourth. The earliest forecast origin is discharge ten, and the last ten rows cannot be forecast origins because labels are unavailable. Test future values are used only for scoring. This tests transfer to another cell under related laboratory conditions, not deployment across calendar time. Overlapping windows share measurements, so row-level independence and narrow confidence claims would be inappropriate.

Persistence and a last-ten-cycle linear trend are reported on identical windows. Per-cell and pooled MAE/RMSE are in `docs/results.json`. Held-out permutation importance is exploratory: correlated predictors, temporal autocorrelation and the small cell count limit interpretation.

## Serving and safeguards
The final serving model is trained on all four cells after evaluation and exported to plain JSON. Browser tree traversal is numerically checked against sklearn predictions, including float32 feature comparisons. CSV stays on the device. Inputs outside any training feature range are rejected, but staying inside these marginal ranges does not establish that an input is in distribution. A user can provide the wrong units or another chemistry; the interface cannot independently establish sensor provenance.

## Limitations and next steps
Only four cells; no pack telemetry, thermal runaway labels, electric vehicle duty cycles or diverse temperatures. Different discharge cut-offs may confound comparisons. No calibrated prediction interval. No causal claims about temperature or charging. No battery replacement, warranty, safety or financial recommendations. Quantify transfer across chemistry/pack designs with a much larger dataset, add chronological external validation, benchmark more models using nested tuning, calibrate intervals on separate cells and establish monitoring before operational use.
