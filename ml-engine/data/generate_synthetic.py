"""Create clearly synthetic labeled transactions for the model workflow."""
import argparse
import csv
import math
import random
from pathlib import Path


def generate(row_count: int, seed: int):
    rng = random.Random(seed)
    for _ in range(row_count):
        amount = round(min(rng.lognormvariate(4.1, 1.15), 25000), 2)
        customer_velocity = min(rng.expovariate(0.7), 14)
        instrument_velocity = min(rng.expovariate(0.55), 14)
        hour = rng.randrange(24)
        weekend = int(rng.random() < 0.28)
        night = int(hour <= 5 or hour >= 23)
        logit = -5.1 + 0.00018 * amount + 0.23 * customer_velocity + 0.32 * instrument_velocity + 0.65 * night + 0.15 * weekend
        probability = 1 / (1 + math.exp(-logit))
        yield {
            "amount": amount,
            "customer_velocity_10m": round(customer_velocity, 2),
            "instrument_velocity_10m": round(instrument_velocity, 2),
            "hour_utc": hour,
            "is_weekend": weekend,
            "fraud_label": int(rng.random() < probability),
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("synthetic_transactions.csv"))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = ["amount", "customer_velocity_10m", "instrument_velocity_10m", "hour_utc", "is_weekend", "fraud_label"]
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(generate(args.rows, args.seed))
    print(f"Wrote {args.rows:,} synthetic rows to {args.output}")
    print("These labels are simulated and must not be treated as real-world fraud evidence.")


if __name__ == "__main__":
    main()
