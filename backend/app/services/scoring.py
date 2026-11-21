from dataclasses import dataclass
from decimal import Decimal

from app.rules.engine import RuleResult


@dataclass(frozen=True)
class RiskDecision:
    score: int
    action: str
    rule_reasons: list[RuleResult]
    model_probability: float | None
    policy_version: str


def decide(
    *,
    rules: list[RuleResult],
    model_probability: float | None,
    low_threshold: int,
    high_threshold: int,
) -> RiskDecision:
    """Combine deterministic rule points and an optional model probability."""
    if model_probability is not None and not 0.0 <= model_probability <= 1.0:
        raise ValueError("model_probability must be between 0 and 1")
    rule_points = sum(rule.points for rule in rules)
    ml_points = round(model_probability * 60) if model_probability is not None else 0
    score = min(100, max(0, rule_points + ml_points))
    action = "approve" if score < low_threshold else "review" if score < high_threshold else "decline"
    return RiskDecision(
        score=score,
        action=action,
        rule_reasons=rules,
        model_probability=model_probability,
        policy_version="risk-policy-v1",
    )
