"""Tests for usage tracking module and usage command."""

import json
from pathlib import Path

from click.testing import CliRunner

from ralph_swarm.cli import main
from ralph_swarm.usage import (
    UsageRecord,
    calculate_cost,
    load_usage,
    parse_stream_json_usage,
    save_usage,
)


class TestCalculateCost:
    """Tests for cost calculation."""

    def test_sonnet_basic(self) -> None:
        cost = calculate_cost("sonnet", 1_000_000, 1_000_000)
        # 1M * $3/MTok + 1M * $15/MTok = $18
        assert cost == 18.0

    def test_opus_basic(self) -> None:
        cost = calculate_cost("opus", 1_000_000, 1_000_000)
        # 1M * $15/MTok + 1M * $75/MTok = $90
        assert cost == 90.0

    def test_haiku_basic(self) -> None:
        cost = calculate_cost("haiku", 1_000_000, 1_000_000)
        # 1M * $0.80/MTok + 1M * $4/MTok = $4.80
        assert cost == 4.8

    def test_zero_tokens(self) -> None:
        cost = calculate_cost("sonnet", 0, 0)
        assert cost == 0.0

    def test_unknown_model(self) -> None:
        cost = calculate_cost("unknown-model", 1000, 1000)
        assert cost == 0.0

    def test_cache_read_discount(self) -> None:
        # Cache reads at 10% of input price
        cost_no_cache = calculate_cost("sonnet", 1_000_000, 0)
        cost_cache_read = calculate_cost("sonnet", 0, 0, cache_read_input_tokens=1_000_000)
        assert abs(cost_cache_read - cost_no_cache * 0.10) < 0.000001

    def test_cache_creation_premium(self) -> None:
        # Cache creation at 125% of input price
        cost_no_cache = calculate_cost("sonnet", 1_000_000, 0)
        cost_cache_create = calculate_cost(
            "sonnet", 0, 0, cache_creation_input_tokens=1_000_000
        )
        assert cost_cache_create == cost_no_cache * 1.25

    def test_mixed_tokens(self) -> None:
        cost = calculate_cost(
            "sonnet",
            input_tokens=10000,
            output_tokens=5000,
            cache_creation_input_tokens=2000,
            cache_read_input_tokens=8000,
        )
        assert cost > 0
        # Input: 10000 * 3/1M = 0.03
        # Output: 5000 * 15/1M = 0.075
        # Cache create: 2000 * 3/1M * 1.25 = 0.0075
        # Cache read: 8000 * 3/1M * 0.10 = 0.0024
        expected = 0.03 + 0.075 + 0.0075 + 0.0024
        assert abs(cost - expected) < 0.000001


class TestParseStreamJsonUsage:
    """Tests for parsing stream-json output."""

    def test_parse_result_line(self) -> None:
        result_line = json.dumps({
            "type": "result",
            "usage": {
                "input_tokens": 1500,
                "output_tokens": 300,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 500,
            },
            "model": "claude-sonnet-4-20250514",
            "duration_seconds": 12.5,
        })
        output = f'{{"type":"assistant","message":"hello"}}\n{result_line}\n'
        result = parse_stream_json_usage(output)
        assert result["input_tokens"] == 1500
        assert result["output_tokens"] == 300
        assert result["cache_read_input_tokens"] == 500
        assert result["model"] == "claude-sonnet-4-20250514"
        assert result["duration_seconds"] == 12.5

    def test_empty_output(self) -> None:
        result = parse_stream_json_usage("")
        assert result == {}

    def test_no_result_line(self) -> None:
        output = '{"type":"assistant","message":"hello"}\n'
        result = parse_stream_json_usage(output)
        assert result == {}

    def test_malformed_json(self) -> None:
        output = "not json at all\n{broken\n"
        result = parse_stream_json_usage(output)
        assert result == {}

    def test_result_with_missing_usage(self) -> None:
        output = '{"type":"result","model":"sonnet"}\n'
        result = parse_stream_json_usage(output)
        assert result["input_tokens"] == 0
        assert result["output_tokens"] == 0

    def test_multiple_result_lines_uses_last(self) -> None:
        output = (
            '{"type":"result","usage":{"input_tokens":100,"output_tokens":50},"model":"sonnet"}\n'
            '{"type":"result","usage":{"input_tokens":200,"output_tokens":100},"model":"opus"}\n'
        )
        result = parse_stream_json_usage(output)
        assert result["input_tokens"] == 200
        assert result["model"] == "opus"


class TestSaveLoadUsage:
    """Tests for save/load of usage records."""

    def test_save_and_load(self, tmp_path: Path) -> None:
        record = UsageRecord(
            timestamp="2025-01-31T10:00:00",
            command="build",
            worker_id="ralph-1",
            model="sonnet",
            input_tokens=15000,
            output_tokens=3000,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=5000,
            cost_usd=0.09,
            duration_seconds=45.0,
            issue_id="abc123",
        )
        save_usage(record, tmp_path)
        records = load_usage(tmp_path)
        assert len(records) == 1
        assert records[0].command == "build"
        assert records[0].worker_id == "ralph-1"
        assert records[0].input_tokens == 15000
        assert records[0].issue_id == "abc123"

    def test_append_multiple(self, tmp_path: Path) -> None:
        for i in range(3):
            record = UsageRecord(
                timestamp=f"2025-01-31T10:0{i}:00",
                command="build",
                worker_id=f"ralph-{i}",
                model="sonnet",
                input_tokens=1000 * (i + 1),
                output_tokens=500,
                cache_creation_input_tokens=0,
                cache_read_input_tokens=0,
                cost_usd=0.01,
                duration_seconds=10.0,
            )
            save_usage(record, tmp_path)

        records = load_usage(tmp_path)
        assert len(records) == 3
        assert records[0].worker_id == "ralph-0"
        assert records[2].worker_id == "ralph-2"

    def test_load_empty_dir(self, tmp_path: Path) -> None:
        records = load_usage(tmp_path)
        assert records == []

    def test_load_nonexistent_dir(self, tmp_path: Path) -> None:
        records = load_usage(tmp_path / "nonexistent")
        assert records == []

    def test_load_skips_bad_lines(self, tmp_path: Path) -> None:
        usage_file = tmp_path / "usage.json"
        usage_file.write_text(
            'bad json\n'
            '{"timestamp":"2025-01-31T10:00:00","command":"build","worker_id":"r1",'
            '"model":"sonnet","input_tokens":100,"output_tokens":50,'
            '"cache_creation_input_tokens":0,"cache_read_input_tokens":0,'
            '"cost_usd":0.01,"duration_seconds":5.0}\n'
            '\n'
        )
        records = load_usage(tmp_path)
        assert len(records) == 1
        assert records[0].input_tokens == 100

    def test_jsonl_format(self, tmp_path: Path) -> None:
        """Verify that usage.json is JSON Lines (one record per line)."""
        record = UsageRecord(
            timestamp="2025-01-31T10:00:00",
            command="plan",
            worker_id="planner",
            model="opus",
            input_tokens=5000,
            output_tokens=1000,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
            cost_usd=0.15,
            duration_seconds=30.0,
        )
        save_usage(record, tmp_path)
        save_usage(record, tmp_path)

        content = (tmp_path / "usage.json").read_text()
        lines = [line for line in content.splitlines() if line.strip()]
        assert len(lines) == 2
        # Each line should be valid JSON
        for line in lines:
            data = json.loads(line)
            assert data["command"] == "plan"


class TestUsageCommand:
    """Tests for the ralph usage CLI command."""

    def test_no_data(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["usage"])
            assert result.exit_code == 0
            assert "No usage data" in result.output

    def test_no_data_json(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["usage", "--json"])
            assert result.exit_code == 0
            assert "[]" in result.output

    def test_with_data(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            logs_dir = Path("logs")
            logs_dir.mkdir()
            record = UsageRecord(
                timestamp="2025-01-31T10:00:00",
                command="build",
                worker_id="ralph-1",
                model="sonnet",
                input_tokens=15000,
                output_tokens=3000,
                cache_creation_input_tokens=0,
                cache_read_input_tokens=0,
                cost_usd=0.09,
                duration_seconds=45.0,
                issue_id="abc123",
            )
            save_usage(record, logs_dir)

            result = runner.invoke(main, ["usage"])
            assert result.exit_code == 0
            assert "sonnet" in result.output
            assert "15,000" in result.output

    def test_json_output(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            logs_dir = Path("logs")
            logs_dir.mkdir()
            record = UsageRecord(
                timestamp="2025-01-31T10:00:00",
                command="build",
                worker_id="ralph-1",
                model="sonnet",
                input_tokens=15000,
                output_tokens=3000,
                cache_creation_input_tokens=0,
                cache_read_input_tokens=0,
                cost_usd=0.09,
                duration_seconds=45.0,
            )
            save_usage(record, logs_dir)

            result = runner.invoke(main, ["usage", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert len(data) == 1
            assert data[0]["model"] == "sonnet"

    def test_since_filter(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            logs_dir = Path("logs")
            logs_dir.mkdir()
            for ts in ["2025-01-01T10:00:00", "2025-06-15T10:00:00"]:
                record = UsageRecord(
                    timestamp=ts,
                    command="build",
                    worker_id="ralph-1",
                    model="sonnet",
                    input_tokens=1000,
                    output_tokens=500,
                    cache_creation_input_tokens=0,
                    cache_read_input_tokens=0,
                    cost_usd=0.01,
                    duration_seconds=10.0,
                )
                save_usage(record, logs_dir)

            result = runner.invoke(main, ["usage", "--json", "--since", "2025-06-01"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert len(data) == 1

    def test_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["usage", "--help"])
        assert result.exit_code == 0
        assert "cost report" in result.output.lower()

    def test_usage_in_help(self) -> None:
        """usage command should appear in main help."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "usage" in result.output
