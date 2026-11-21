"""Train/evaluate a baseline model on the synthetic CSV or an approved dataset."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score, confusion_matrix, precision_recall_curve
from sklearn.model_selection import train_test_split

FEATURES = ["amount", "customer_velocity_10m", "instrument_velocity_10m", "hour_utc", "is_weekend"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path(__file__).parents[1] / "data" / "synthetic_transactions.csv")
    parser.add_argument("--output", type=Path, default=Path(__file__).parents[1] / "artifacts" / "fraud_model.joblib")
    parser.add_argument("--model", choices=["sklearn", "xgboost"], default="sklearn")
    parser.add_argument("--threshold", type=float, default=None, help="Optional fixed cutoff; default selects the best F1 cutoff on a validation split")
    args = parser.parse_args()
    if args.threshold is not None and not 0.0 <= args.threshold <= 1.0:
        raise SystemExit("--threshold must be between 0 and 1")

    frame = pd.read_csv(args.data)
    missing = set(FEATURES + ["fraud_label"]) - set(frame.columns)
    if missing:
        raise SystemExit(f"Dataset is missing required columns: {', '.join(sorted(missing))}")
    x_train, x_holdout, y_train, y_holdout = train_test_split(
        frame[FEATURES], frame["fraud_label"].astype(int), test_size=0.30, random_state=42, stratify=frame["fraud_label"]
    )
    x_validation, x_test, y_validation, y_test = train_test_split(
        x_holdout, y_holdout, test_size=0.5, random_state=43, stratify=y_holdout
    )

    if args.model == "xgboost":
        from xgboost import XGBClassifier
        model = XGBClassifier(
            n_estimators=300, max_depth=5, learning_rate=0.05, subsample=0.85,
            colsample_bytree=0.85, eval_metric="logloss", random_state=42,
        )
        model_type = "xgboost"
    else:
        model = HistGradientBoostingClassifier(max_iter=180, learning_rate=0.08, max_leaf_nodes=24, random_state=42)
        model_type = "sklearn_hist_gradient_boosting"

    model.fit(x_train, y_train)
    validation_probabilities = model.predict_proba(x_validation)[:, 1]
    if args.threshold is None:
        val_precision, val_recall, cutoffs = precision_recall_curve(y_validation, validation_probabilities)
        f1_values = 2 * val_precision[:-1] * val_recall[:-1] / (val_precision[:-1] + val_recall[:-1] + 1e-12)
        threshold = float(cutoffs[int(f1_values.argmax())])
        threshold_source = "validation_max_f1"
    else:
        threshold = args.threshold
        threshold_source = "user_supplied"
    probabilities = model.predict_proba(x_test)[:, 1]
    predictions = (probabilities >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_test, predictions, labels=[0, 1]).ravel()
    metrics = {
        "precision": precision_score(y_test, predictions, zero_division=0),
        "recall": recall_score(y_test, predictions, zero_division=0),
        "f1": f1_score(y_test, predictions, zero_division=0),
        "pr_auc": average_precision_score(y_test, probabilities),
        "false_positive_rate": fp / max(1, fp + tn),
        "threshold": threshold,
        "threshold_source": threshold_source,
        "fraud_prevalence": float(y_test.mean()),
        "validation_rows": len(y_validation),
        "test_rows": len(y_test),
    }
    version = f"{model_type}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "features": FEATURES, "version": version, "model_type": model_type}, args.output)
    report_path = args.output.with_suffix(".metrics.json")
    report_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps({"version": version, "artifact": str(args.output), "metrics": metrics}, indent=2))
    print("Synthetic-data metrics demonstrate the workflow only; evaluate on a licensed, representative dataset before making decisions.")


if __name__ == "__main__":
    main()
