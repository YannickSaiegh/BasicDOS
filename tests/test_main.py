import asyncio
import csv
import json
from pathlib import Path

import pytest

import main


def test_normalize_url_defaults_to_https() -> None:
    assert main.normalize_url("example.com/health") == "https://example.com/health"
    assert main.normalize_url("http://localhost:8000/ping") == "http://localhost:8000/ping"
    assert main.normalize_url("https://api.example.com") == "https://api.example.com"


def test_normalize_url_rejects_empty_or_invalid() -> None:
    with pytest.raises(ValueError):
        main.normalize_url("   ")
    with pytest.raises(ValueError):
        main.normalize_url("https://")


def test_parse_headers_valid_and_invalid() -> None:
    parsed = main.parse_headers(["Content-Type: application/json", "X-Custom: a:b"])
    assert parsed == {"Content-Type": "application/json", "X-Custom": "a:b"}

    with pytest.raises(ValueError):
        main.parse_headers(["InvalidHeaderWithoutColon"])
    with pytest.raises(ValueError):
        main.parse_headers([": missing-key"])


def test_apply_auth_headers_bearer_and_basic() -> None:
    h_bearer = main.apply_auth_headers({"Accept": "*/*"}, bearer="secret-token")
    assert h_bearer["Authorization"] == "Bearer secret-token"

    h_basic = main.apply_auth_headers({}, basic_auth="user:pass")
    assert h_basic["Authorization"] == "Basic dXNlcjpwYXNz"

    with pytest.raises(ValueError):
        main.apply_auth_headers({}, bearer="tok", basic_auth="user:pass")
    with pytest.raises(ValueError):
        main.apply_auth_headers({}, basic_auth="missing-colon")


def test_load_request_body(tmp_path: Path) -> None:
    assert main.load_request_body('{"ping":1}', None) == '{"ping":1}'

    payload_file = tmp_path / "payload.json"
    payload_file.write_text('{"hello":"world"}', encoding="utf-8")
    assert main.load_request_body(None, str(payload_file)) == '{"hello":"world"}'

    with pytest.raises(ValueError):
        main.load_request_body("inline", str(payload_file))
    with pytest.raises(ValueError):
        main.load_request_body(None, str(tmp_path / "missing.json"))


def test_metrics_status_codes_min_max_percentiles_and_reset() -> None:
    m = main.Metrics()
    m.record_response(200, 10.0, 100, "HTTP/2")
    m.record_response(200, 20.0, 200, "HTTP/2")
    m.record_response(404, 50.0, 50, "HTTP/2")
    m.record_response(503, 100.0, 10, "HTTP/2")
    m.record_timeout()

    summary = m.summary()
    assert summary["total_requests"] == 5
    assert summary["success_2xx"] == 2
    assert summary["client_4xx"] == 1
    assert summary["server_5xx"] == 1
    assert summary["timeouts"] == 1
    assert summary["status_codes"] == {200: 2, 404: 1, 503: 1}
    assert summary["min_ms"] == 10.0
    assert summary["max_ms"] == 100.0
    assert summary["avg_ms"] == 45.0
    assert summary["http_version"] == "HTTP/2"

    m.reset()
    after_reset = m.summary()
    assert after_reset["total_requests"] == 0
    assert after_reset["status_codes"] == {}
    assert after_reset["min_ms"] == 0.0
    assert after_reset["max_ms"] == 0.0


def test_export_csv_creates_and_appends(tmp_path: Path) -> None:
    csv_file = tmp_path / "report.csv"
    row1 = {"total_requests": 10, "status_codes": {200: 10}, "rps": 50.0}
    row2 = {"total_requests": 20, "status_codes": {200: 19, 500: 1}, "rps": 75.0}

    main.export_csv(csv_file, row1)
    main.export_csv(csv_file, row2)

    with csv_file.open("r", encoding="utf-8", newline="") as fp:
        rows = list(csv.DictReader(fp))

    assert len(rows) == 2
    assert rows[0]["total_requests"] == "10"
    assert json.loads(rows[1]["status_codes"]) == {"200": 19, "500": 1}


def test_token_bucket_rate_limiter() -> None:
    async def run() -> int:
        limiter = main.TokenBucketRateLimiter(100.0)
        stop_event = asyncio.Event()
        for _ in range(3):
            await limiter.acquire(stop_event)
        return 3

    assert asyncio.run(run()) == 3


def test_build_arg_parser_flags() -> None:
    parser = main.build_arg_parser()
    args = parser.parse_args(
        [
            "https://example.com",
            "-m",
            "POST",
            "-c",
            "50",
            "--warmup",
            "2.5",
            "--bearer",
            "abc",
            "--no-http2",
            "--quiet",
            "--csv",
            "out.csv",
        ]
    )
    assert args.url == "https://example.com"
    assert args.method == "POST"
    assert args.concurrency == 50
    assert args.warmup == 2.5
    assert args.bearer == "abc"
    assert args.http2 is False
    assert args.quiet is True
    assert args.csv == "out.csv"
