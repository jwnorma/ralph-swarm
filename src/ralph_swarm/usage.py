"""Usage tracking for Claude invocations."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class UsageRecord:
    """A single usage record for a Claude invocation."""

    timestamp: str
    command: str
    worker_id: str
    model: str
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int
    cache_read_input_tokens: int
    cost_usd: float
    duration_seconds: float
    issue_id: str | None = None


# Pricing per million tokens (as of 2025)
MODEL_PRICING: dict[str, dict[str, float]] = {
    "opus": {"input": 15.00, "output": 75.00},
    "sonnet": {"input": 3.00, "output": 15.00},
    "haiku": {"input": 0.80, "output": 4.00},
}

# Cache pricing modifiers
CACHE_READ_DISCOUNT = 0.10  # 90% discount — pay 10% of input price
CACHE_CREATION_PREMIUM = 1.25  # 25% premium over input price


def calculate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_creation_input_tokens: int = 0,
    cache_read_input_tokens: int = 0,
) -> float:
    """Calculate cost in USD for a Claude invocation."""
    pricing = MODEL_PRICING.get(model)
    if not pricing:
        return 0.0

    input_price = pricing["input"] / 1_000_000
    output_price = pricing["output"] / 1_000_000

    cost = (
        input_tokens * input_price
        + output_tokens * output_price
        + cache_read_input_tokens * input_price * CACHE_READ_DISCOUNT
        + cache_creation_input_tokens * input_price * CACHE_CREATION_PREMIUM
    )
    return round(cost, 6)


def save_usage(record: UsageRecord, logs_dir: Path) -> None:
    """Append a usage record to logs/usage.json (JSON Lines format)."""
    logs_dir.mkdir(parents=True, exist_ok=True)
    usage_file = logs_dir / "usage.json"
    with open(usage_file, "a") as f:
        f.write(json.dumps(asdict(record)) + "\n")


def load_usage(logs_dir: Path) -> list[UsageRecord]:
    """Load all usage records from logs/usage.json."""
    usage_file = logs_dir / "usage.json"
    if not usage_file.exists():
        return []

    records = []
    for line in usage_file.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            records.append(UsageRecord(**data))
        except (json.JSONDecodeError, TypeError):
            continue
    return records


def parse_stream_json_usage(output: str) -> dict:
    """Parse the final result line from stream-json output.

    Claude CLI with --output-format stream-json emits JSON lines,
    the last meaningful one having type "result" with usage info.

    Returns dict with input_tokens, output_tokens, cache_creation_input_tokens,
    cache_read_input_tokens, model, and duration_seconds.
    """
    result_data: dict = {}

    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue

        if data.get("type") == "result":
            usage = data.get("usage", {})
            result_data = {
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "cache_creation_input_tokens": usage.get("cache_creation_input_tokens", 0),
                "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
                "model": data.get("model", ""),
                "duration_seconds": data.get("duration_seconds", 0),
                "duration_api_seconds": data.get("duration_api_seconds", 0),
            }

    return result_data
