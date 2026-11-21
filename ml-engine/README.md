# Model workflow

This workflow starts with a reproducible synthetic dataset so the feature path and evaluation code can be exercised without payment data. Synthetic labels are generated from known patterns and do not demonstrate real fraud detection quality.

From the repository root, after installing the backend ML extra:

```powershell
python ml-engine/data/generate_synthetic.py --rows 20000
python ml-engine/training/train.py --model sklearn
# Optional XGBoost baseline:
python ml-engine/training/train.py --model xgboost
```

The training script uses stratified train/validation/test splits. By default, it selects a cutoff on the validation split that maximizes F1, then reports precision, recall, F1, PR-AUC, false-positive rate, and test fraud prevalence. You can pass a fixed cutoff with `--threshold`. It writes a versioned `joblib` artifact and a JSON metrics report under `ml-engine/artifacts/`. Set `model_artifact_path=../ml-engine/artifacts/fraud_model.joblib` in `backend/.env` and restart the API to enable model scoring. Keep artifacts out of source control and only load trusted artifacts. Before using any real public dataset, review its license, documentation, data leakage risks, and label quality.
