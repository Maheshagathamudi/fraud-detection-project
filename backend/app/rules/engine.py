from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class RuleResult:
    rule_id: str
    points: int
    reason: str


def evaluate_rules(
    *,
    amount: Decimal,
    recent_customer_count: int,
    recent_instrument_count: int,
    high_amount_threshold: Decimal,
    customer_velocity_limit: int,
    instrument_velocity_limit: int,
) -> list[RuleResult]:
    """Apply deterministic, explainable rules to a transaction."""
    results: list[RuleResult] = []
    if amount >= high_amount_threshold:
        results.append(RuleResult("high_amount", 40, "Amount exceeds the configured high-value threshold"))
    if recent_customer_count >= customer_velocity_limit:
        results.append(RuleResult("customer_velocity", 30, "Customer token has exceeded the recent transaction limit"))
    if recent_instrument_count >= instrument_velocity_limit:
        results.append(RuleResult("instrument_velocity", 35, "Payment instrument token has exceeded the recent transaction limit"))
    return results
