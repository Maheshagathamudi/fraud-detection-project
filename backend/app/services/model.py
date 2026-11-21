from functools import lru_cache


@lru_cache(maxsize=4)
def _load_model(path: str):
    try:
        import joblib
    except ImportError as exc:
        raise RuntimeError("Install the backend 'ml' extra to load a model artifact") from exc
    artifact = joblib.load(path)
    return artifact


def score_features(features: dict[str, float], artifact_path: str | None) -> tuple[float | None, str | None]:
    """Score with an optional versioned artifact; no model is fabricated if absent."""
    if not artifact_path:
        return None, None
    artifact = _load_model(artifact_path)
    model = artifact["model"]
    probability = float(model.predict_proba([[features[name] for name in artifact["features"]]])[0][1])
    return probability, str(artifact["version"])
