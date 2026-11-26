import argparse
import asyncio
import base64
import csv
import importlib.util
import json
import os
import signal
import statistics
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from rich.align import Align
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()
MAX_LATENCY_SAMPLES = 50_000
HAS_H2 = importlib.util.find_spec("h2") is not None


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def print_banner() -> None:
    banner = """[bold white]
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⣀⣀⣀⠀⠀⠀⠀⠀⠀  [bright_yellow]╔══════════════════════════════╗[/]
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣴⣾⣿⣿⣿⣿⣿⣿⣶⣄⠀⠀⠀  [bright_yellow]║[/]       [bold cyan]BasicDOS Framework[/]     [bright_yellow]║[/]
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣾⣿⣿⣿⣿⣿⠿⢿⣿⣿⣿⣿⣆⠀⠀  [bright_yellow]║[/]      [bold red]Made by TrionixDev[/]      [bright_yellow]║[/]
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣴⣿⣿⣿⣿⣿⣿⠁⠀⠿⢿⣿⡿⣿⣿⡆⠀  [bright_yellow]╚══════════════════════════════╝[/]
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣴⣿⣿⣿⣿⣿⣿⣿⣿⣦⣤⣴⣿⠃⠀⠿⣿⡇⠀  [bright_yellow][[/][bold red]WARNING[/][bright_yellow]][/] [bold white]Authorized Testing Only[/]
⠀⠀⠀⠀⠀⠀⠀⠀⣠⣾⣿⣿⣿⣿⣿⣿⡿⠋⠁⣿⠟⣿⣿⢿⣧⣤⣴⣿⡇⠀  [bright_yellow][[/][bold cyan]INFO[/][bright_yellow]][/] [bold white]Press Ctrl+C to Stop[/]
⠀⠀⠀⠀⢀⣠⣴⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⠀⠀⠀⠀⠘⠁⢸⠟⢻⣿⡿⠀⠀  [bright_yellow][[/][bold green]MODE[/][bright_yellow]][/] [bold white]Async HTTPS | HTTP/2 | Stats[/]
⠀⠀⠙⠻⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣴⣇⢀⣤⠀⠀⠀⠀⠘⣿⠃⠀⠀
⠀⠀⠀⠀⠀⢈⣽⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣴⣿⢀⣴⣾⠇⠀⠀⠀
⠀⠀⣀⣤⣶⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠏⠀⠀⠀⠀
⠀⠀⠉⠉⠉⠉⣡⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠃⠀⠀⠀⠀⠀
⠀⠀⠀⠀⣠⣾⣿⣿⣿⣿⡿⠟⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠟⠁⠀⠀⠀⠀⠀⠀
⠀⠀⣴⡾⠿⠿⠿⠛⠋⠉⠀⢸⣿⣿⣿⣿⠿⠋⢸⣿⡿⠋⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⣿⡿⠟⠋⠁⠀⠀⡿⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠀⠀⠀⠀⠀⠀⠈⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]"""
    console.print(Align.center(banner))


def prompt_choice(title: str, options: list[tuple[str, str]], default_idx: int = 1) -> str:
    table = Table(title=f"[bold cyan]{title}[/]", border_style="bright_yellow", show_header=True)
    table.add_column("Opção", style="bold bright_yellow", justify="center", width=8)
    table.add_column("Escolha", style="bold white")
    table.add_column("Detalhe", style="dim white")

    for idx, (label, detail) in enumerate(options, start=1):
        marker = " (padrão)" if idx == default_idx else ""
        table.add_row(str(idx), f"{label}{marker}", detail)

    console.print()
    console.print(table)

    valid_numbers = {str(i): options[i - 1][0] for i in range(1, len(options) + 1)}
    default_value = options[default_idx - 1][0]

    while True:
        raw = console.input(
            f"[bright_yellow][[/][bold white]1-{len(options)}[/][bright_yellow]][/] "
            f"[bold cyan]Escolhe o número (Enter = {default_idx}):[/] "
        ).strip()
        if raw == "":
            return default_value
        if raw in valid_numbers:
            return valid_numbers[raw]
        console.print(f"[bold red]Opção inválida. Escolhe um número de 1 a {len(options)}.[/]")


def interactive_wizard() -> argparse.Namespace:
    console.print()
    raw_url = console.input(
        "[bright_yellow][[/][bold white]TARGET[/][bright_yellow]][/] "
        "[bold cyan]Cola ou escreve o URL alvo (HTTP/HTTPS):[/] "
    ).strip()

    method = prompt_choice(
        "Método HTTP",
        [
            ("GET", "Pedido padrão de leitura"),
            ("POST", "Envio de dados / formulário / JSON"),
            ("PUT", "Atualização completa de recurso"),
            ("DELETE", "Remoção de recurso"),
            ("HEAD", "Apenas cabeçalhos HTTP/HTTPS sem corpo"),
        ],
        default_idx=1,
    )

    concurrency_str = prompt_choice(
        "Nível de Concorrência (Workers Async)",
        [
            ("25", "Leve (25 workers)"),
            ("100", "Médio (100 workers)"),
            ("250", "Alto (250 workers)"),
            ("500", "Intensivo (500 workers)"),
        ],
        default_idx=2,
    )

    requests_str = prompt_choice(
        "Quantidade de Pedidos (-n)",
        [
            ("0", "Sem limite fixo (corre até duração ou Ctrl+C)"),
            ("1000", "1.000 pedidos"),
            ("5000", "5.000 pedidos"),
            ("20000", "20.000 pedidos"),
        ],
        default_idx=1,
    )

    duration_str = prompt_choice(
        "Duração Máxima",
        [
            ("0", "Sem limite de tempo (até terminar pedidos ou Ctrl+C)"),
            ("15", "15 segundos"),
            ("30", "30 segundos"),
            ("60", "60 segundos"),
        ],
        default_idx=3,
    )

    warmup_str = prompt_choice(
        "Fase de Warmup (Aquecimento TLS/HTTP2)",
        [
            ("0", "Sem warmup"),
            ("3", "3 segundos de warmup"),
            ("5", "5 segundos de warmup"),
        ],
        default_idx=1,
    )

    timeout_str = prompt_choice(
        "Timeout por Pedido",
        [
            ("2.0", "2.0 segundos"),
            ("5.0", "5.0 segundos"),
            ("10.0", "10.0 segundos"),
        ],
        default_idx=2,
    )

    max_rps_str = prompt_choice(
        "Limite Global de RPS",
        [
            ("0", "Sem limite (máximo do pool)"),
            ("100", "Até ~100 req/s"),
            ("500", "Até ~500 req/s"),
            ("1000", "Até ~1.000 req/s"),
        ],
        default_idx=1,
    )

    http2_str = prompt_choice(
        "Protocolo HTTPS / HTTP/2",
        [
            ("true", "Ativar HTTP/2 sobre HTTPS (multiplexing + keep-alive)"),
            ("false", "Usar apenas HTTP/1.1"),
        ],
        default_idx=1,
    )

    preset_choice = prompt_choice(
        "Cabeçalhos e Corpo Extra",
        [
            ("none", "Sem headers extra nem corpo"),
            ("json_ping", 'Content-Type: application/json + corpo {"ping":1}'),
            ("browser_ua", "User-Agent padrão de navegador"),
        ],
        default_idx=1,
    )

    headers: list[str] = []
    data: str | None = None
    if preset_choice == "json_ping":
        headers = ["Content-Type: application/json"]
        data = '{"ping":1}'
    elif preset_choice == "browser_ua":
        headers = [
            "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ]

    follow_redirects_str = prompt_choice(
        "Seguir Redirecionamentos (301/302/307)",
        [
            ("false", "Não seguir"),
            ("true", "Seguir redirecionamentos"),
        ],
        default_idx=1,
    )

    insecure_str = prompt_choice(
        "Validação TLS / SSL",
        [
            ("false", "Validar certificado SSL/TLS (recomendado)"),
            ("true", "Ignorar validação SSL/TLS (apenas testes locais)"),
        ],
        default_idx=1,
    )

    output_choice = prompt_choice(
        "Guardar Relatório",
        [
            ("none", "Não guardar ficheiro"),
            ("json", "Guardar em load_report.json"),
            ("csv", "Guardar em load_report.csv"),
            ("both", "Guardar em JSON e CSV"),
        ],
        default_idx=1,
    )

    return argparse.Namespace(
        url=raw_url,
        method=method,
        concurrency=int(concurrency_str),
        requests=int(requests_str),
        timeout=float(timeout_str),
        duration=float(duration_str),
        warmup=float(warmup_str),
        max_rps=float(max_rps_str),
        http2=(http2_str == "true"),
        header=headers,
        bearer=None,
        basic_auth=None,
        data=data,
        data_file=None,
        follow_redirects=(follow_redirects_str == "true"),
        insecure=(insecure_str == "true"),
        quiet=False,
        output="load_report.json" if output_choice in {"json", "both"} else None,
        csv="load_report.csv" if output_choice in {"csv", "both"} else None,
    )


class TokenBucketRateLimiter:
    """Rate limiter assíncrono global para limitar RPS aproximado."""

    def __init__(self, rate_per_sec: float) -> None:
        self.rate = rate_per_sec
        self.capacity = max(1.0, rate_per_sec)
        self.tokens = self.capacity
        self.updated_at = time.perf_counter()
        self._lock = asyncio.Lock()

    async def acquire(self, stop_event: asyncio.Event) -> None:
        while not stop_event.is_set():
            async with self._lock:
                now = time.perf_counter()
                elapsed = max(0.0, now - self.updated_at)
                self.updated_at = now
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)

                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return

                wait_time = (1.0 - self.tokens) / self.rate

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=min(wait_time, 0.25))
            except asyncio.TimeoutError:
                continue


@dataclass
class Metrics:
    total_requests: int = 0
    success_2xx: int = 0
    redirect_3xx: int = 0
    client_4xx: int = 0
    server_5xx: int = 0
    timeouts: int = 0
    conn_errors: int = 0
    other_errors: int = 0
    bytes_received: int = 0
    status_codes: dict[int, int] = field(default_factory=dict)
    min_latency_ms: float | None = None
    max_latency_ms: float | None = None
    _latency_sum_ms: float = 0.0
    latencies_ms: deque[float] = field(default_factory=lambda: deque(maxlen=MAX_LATENCY_SAMPLES))
    start_perf: float = field(default_factory=time.perf_counter)
    last_http_version: str = "-"
    last_event_code: str = "init"
    last_event_detail: str = "A iniciar..."

    def reset(self) -> None:
        self.total_requests = 0
        self.success_2xx = 0
        self.redirect_3xx = 0
        self.client_4xx = 0
        self.server_5xx = 0
        self.timeouts = 0
        self.conn_errors = 0
        self.other_errors = 0
        self.bytes_received = 0
        self.status_codes.clear()
        self.min_latency_ms = None
        self.max_latency_ms = None
        self._latency_sum_ms = 0.0
        self.latencies_ms.clear()
        self.start_perf = time.perf_counter()
        self.last_event_code = "init"
        self.last_event_detail = "Medição iniciada"

    def record_response(self, status_code: int, elapsed_ms: float, num_bytes: int, http_version: str) -> None:
        self.total_requests += 1
        self._latency_sum_ms += elapsed_ms
        self.latencies_ms.append(elapsed_ms)
        self.bytes_received += num_bytes
        self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1

        if self.min_latency_ms is None or elapsed_ms < self.min_latency_ms:
            self.min_latency_ms = elapsed_ms
        if self.max_latency_ms is None or elapsed_ms > self.max_latency_ms:
            self.max_latency_ms = elapsed_ms

        if http_version:
            self.last_http_version = http_version

        if 200 <= status_code < 300:
            self.success_2xx += 1
        elif 300 <= status_code < 400:
            self.redirect_3xx += 1
        elif 400 <= status_code < 500:
            self.client_4xx += 1
        elif 500 <= status_code < 600:
            self.server_5xx += 1

        self.last_event_code = "ok" if 200 <= status_code < 400 else "http_err"
        self.last_event_detail = f"{http_version} {status_code} ({elapsed_ms:.1f} ms)"

    def record_timeout(self) -> None:
        self.total_requests += 1
        self.timeouts += 1
        self.last_event_code = "timeout"
        self.last_event_detail = "Timeout"

    def record_conn_error(self) -> None:
        self.total_requests += 1
        self.conn_errors += 1
        self.last_event_code = "conn_err"
        self.last_event_detail = "Erro de ligação / TLS"

    def record_other_error(self, msg: str) -> None:
        self.total_requests += 1
        self.other_errors += 1
        self.last_event_code = "other_err"
        self.last_event_detail = msg.strip().splitlines()[0][:45] if msg.strip() else "Erro desconhecido"

    def _percentiles_ms(self) -> tuple[float, float, float]:
        samples = list(self.latencies_ms)
        if not samples:
            return 0.0, 0.0, 0.0

        sorted_lat = sorted(samples)
        p50 = statistics.median(sorted_lat)
        if len(sorted_lat) >= 2:
            quantiles = statistics.quantiles(sorted_lat, n=100, method="inclusive")
            p95 = quantiles[94]
            p99 = quantiles[98]
        else:
            p95 = p99 = sorted_lat[0]
        return p50, p95, p99

    def summary(self) -> dict[str, Any]:
        elapsed = max(time.perf_counter() - self.start_perf, 1e-6)
        rps = self.total_requests / elapsed
        mb_received = self.bytes_received / (1024 * 1024)
        mb_per_sec = mb_received / elapsed
        success_rate = (self.success_2xx / self.total_requests * 100.0) if self.total_requests else 0.0
        avg_ms = (self._latency_sum_ms / len(self.latencies_ms)) if self.latencies_ms else 0.0
        min_ms = self.min_latency_ms if self.min_latency_ms is not None else 0.0
        max_ms = self.max_latency_ms if self.max_latency_ms is not None else 0.0
        p50_ms, p95_ms, p99_ms = self._percentiles_ms()

        return {
            "total_requests": self.total_requests,
            "success_2xx": self.success_2xx,
            "redirect_3xx": self.redirect_3xx,
            "client_4xx": self.client_4xx,
            "server_5xx": self.server_5xx,
            "timeouts": self.timeouts,
            "conn_errors": self.conn_errors,
            "other_errors": self.other_errors,
            "status_codes": dict(sorted(self.status_codes.items())),
            "elapsed_sec": round(elapsed, 2),
            "rps": round(rps, 2),
            "data_mb": round(mb_received, 2),
            "throughput_mb_s": round(mb_per_sec, 2),
            "success_rate_pct": round(success_rate, 2),
            "min_ms": round(min_ms, 2),
            "avg_ms": round(avg_ms, 2),
            "max_ms": round(max_ms, 2),
            "p50_ms": round(p50_ms, 2),
            "p95_ms": round(p95_ms, 2),
            "p99_ms": round(p99_ms, 2),
            "http_version": self.last_http_version,
            "last_event_code": self.last_event_code,
            "last_event": self.last_event_detail,
        }


def normalize_url(raw_url: str) -> str:
    url = raw_url.strip()
    if not url:
        raise ValueError("URL vazio.")
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    parsed = urlparse(url)
    if not parsed.netloc:
        raise ValueError("URL inválido.")
    return url


def parse_headers(raw_headers: list[str]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for item in raw_headers:
        if ":" not in item:
            raise ValueError(f"Header inválido (usa Chave:Valor): {item}")
        key, value = item.split(":", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Nome de header vazio em: {item}")
        headers[key] = value.strip()
    return headers


def apply_auth_headers(
    headers: dict[str, str],
    bearer: str | None = None,
    basic_auth: str | None = None,
) -> dict[str, str]:
    if bearer and basic_auth:
        raise ValueError("Usa apenas --bearer ou --basic-auth, não ambos em simultâneo.")
    result = dict(headers)
    if bearer:
        token = bearer.strip()
        if not token:
            raise ValueError("Token --bearer vazio.")
        result["Authorization"] = f"Bearer {token}"
    elif basic_auth:
        if ":" not in basic_auth:
            raise ValueError("--basic-auth deve estar no formato 'utilizador:password'.")
        encoded = base64.b64encode(basic_auth.encode("utf-8")).decode("ascii")
        result["Authorization"] = f"Basic {encoded}"
    return result


def load_request_body(data: str | None, data_file: str | None) -> str | None:
    if data is not None and data_file is not None:
        raise ValueError("Usa apenas --data ou --data-file, não ambos em simultâneo.")
    if data_file is not None:
        path = Path(data_file)
        if not path.is_file():
            raise ValueError(f"Ficheiro --data-file não encontrado: {data_file}")
        return path.read_text(encoding="utf-8")
    return data


def export_csv(path: Path, result: dict[str, Any]) -> None:
    row: dict[str, Any] = {}
    for key, value in result.items():
        if isinstance(value, (dict, list)):
            row[key] = json.dumps(value, ensure_ascii=False)
        else:
            row[key] = value

    file_exists = path.exists() and path.stat().st_size > 0
    with path.open("a", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(row.keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def _format_last_event(data: dict[str, Any]) -> str:
    code = str(data.get("last_event_code", ""))
    detail = str(data.get("last_event", ""))
    if code == "timeout":
        return f"[yellow]{detail}[/]"
    if code in {"conn_err", "other_err"}:
        return f"[red]{detail}[/]"
    if code == "http_err":
        return f"[cyan]{detail}[/]"
    return f"[white]{detail}[/]"


def build_ui(data: dict[str, Any], progress: Progress) -> Layout:
    left = Table.grid(padding=1)
    left.add_column(style="bright_yellow", justify="right")
    left.add_column(style="bold white")
    left.add_row("Total Pedidos:", f"{int(data['total_requests']):,}")
    left.add_row("Sucesso (2xx):", f"[bold green]{int(data['success_2xx']):,}[/]")
    left.add_row(
        "3xx / 4xx / 5xx:",
        f"[cyan]{int(data['redirect_3xx']):,}[/] / [yellow]{int(data['client_4xx']):,}[/] / [red]{int(data['server_5xx']):,}[/]",
    )
    left.add_row("Timeouts:", f"[bold yellow]{int(data['timeouts']):,}[/]")
    left.add_row("Falhas Lig./TLS:", f"[bold red]{int(data['conn_errors']):,}[/]")
    left.add_row("Outros Erros:", f"[bold red]{int(data['other_errors']):,}[/]")
    left.add_row(
        "Transferido:",
        f"[bold cyan]{float(data['data_mb']):.2f} MB[/] ([white]{float(data['throughput_mb_s']):.2f} MB/s[/])",
    )

    right = Table.grid(padding=1)
    right.add_column(style="bright_yellow", justify="right")
    right.add_column(style="bold white")
    right.add_row("RPS Atual:", f"[bold cyan]{float(data['rps']):.2f}[/]")
    right.add_row("Taxa 2xx:", f"[bold green]{float(data['success_rate_pct']):.1f}%[/]")
    right.add_row(
        "Min / Méd / Máx:",
        f"[bold blue]{float(data['min_ms']):.1f} / {float(data['avg_ms']):.1f} / {float(data['max_ms']):.1f} ms[/]",
    )
    right.add_row(
        "p50 / p95 / p99:",
        f"[bold magenta]{float(data['p50_ms']):.1f} / {float(data['p95_ms']):.1f} / {float(data['p99_ms']):.1f} ms[/]",
    )
    right.add_row("Protocolo:", f"[bold white]{data['http_version']}[/]")
    right.add_row("Tempo:", f"[bold white]{float(data['elapsed_sec']):.1f}s[/]")
    right.add_row("Último Evento:", _format_last_event(data))

    layout = Layout()
    layout.split_column(
        Layout(name="main", size=14),
        Layout(name="footer", size=3),
    )
    layout["main"].split_row(
        Panel(left, title="[bold red]Contadores[/]", border_style="bright_yellow", padding=(1, 2)),
        Panel(right, title="[bold red]Latência & Throughput[/]", border_style="bright_yellow", padding=(1, 2)),
    )
    layout["footer"].update(Panel(progress, border_style="bright_yellow", padding=(0, 1)))
    return layout


async def worker_task(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    stop_event: asyncio.Event,
    warmup_done_event: asyncio.Event,
    metrics: Metrics,
    method: str,
    url: str,
    body: str | None,
    rate_limiter: TokenBucketRateLimiter | None,
    max_requests: int,
) -> None:
    while not stop_event.is_set():
        if warmup_done_event.is_set() and max_requests > 0 and metrics.total_requests >= max_requests:
            stop_event.set()
            break

        if rate_limiter is not None:
            await rate_limiter.acquire(stop_event)
            if stop_event.is_set():
                break

        async with semaphore:
            if stop_event.is_set() or (
                warmup_done_event.is_set() and max_requests > 0 and metrics.total_requests >= max_requests
            ):
                break

            t0 = time.perf_counter()
            try:
                async with client.stream(method, url, content=body) as resp:
                    payload = await resp.aread()
                    elapsed_ms = (time.perf_counter() - t0) * 1000.0
                    if warmup_done_event.is_set():
                        metrics.record_response(
                            resp.status_code,
                            elapsed_ms,
                            len(payload),
                            resp.http_version,
                        )
            except httpx.TimeoutException:
                if warmup_done_event.is_set():
                    metrics.record_timeout()
            except httpx.ConnectError:
                if warmup_done_event.is_set():
                    metrics.record_conn_error()
            except httpx.HTTPError as exc:
                if warmup_done_event.is_set():
                    metrics.record_other_error(str(exc))
            except Exception as exc:
                if warmup_done_event.is_set():
                    metrics.record_other_error(str(exc))


async def run_load_test(args: argparse.Namespace) -> dict[str, Any]:
    if args.concurrency < 1:
        raise ValueError("A concorrência (-c) deve ser >= 1.")
    if args.timeout <= 0:
        raise ValueError("O timeout (-t) deve ser > 0.")
    if args.max_rps < 0:
        raise ValueError("--max-rps não pode ser negativo.")
    if args.requests < 0:
        raise ValueError("--requests (-n) não pode ser negativo.")
    if args.warmup < 0:
        raise ValueError("--warmup não pode ser negativo.")

    url = normalize_url(args.url)
    headers = apply_auth_headers(
        parse_headers(args.header),
        bearer=getattr(args, "bearer", None),
        basic_auth=getattr(args, "basic_auth", None),
    )
    body = load_request_body(args.data, getattr(args, "data_file", None))
    method = args.method.upper()
    concurrency = args.concurrency
    quiet = bool(getattr(args, "quiet", False))
    rate_limiter = TokenBucketRateLimiter(args.max_rps) if args.max_rps > 0 else None

    use_http2 = bool(args.http2 and HAS_H2)
    if args.http2 and not HAS_H2 and not quiet:
        console.print("[yellow]Aviso: pacote 'h2' não instalado; a usar HTTP/1.1 (instala com pip install httpx[http2]).[/]")

    stop_event = asyncio.Event()
    warmup_done_event = asyncio.Event()
    if args.warmup == 0:
        warmup_done_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass

    limits = httpx.Limits(
        max_connections=concurrency,
        max_keepalive_connections=min(concurrency, 200),
        keepalive_expiry=30.0,
    )
    timeout = httpx.Timeout(args.timeout)
    metrics = Metrics()

    proto_label = "HTTPS/HTTP2" if use_http2 else "HTTP/HTTPS"
    progress = Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        BarColumn(pulse_style="red"),
        console=console,
    )
    initial_desc = (
        f"[bold yellow]A aquecer ligações ({args.warmup:.1f}s warmup)...[/]"
        if args.warmup > 0
        else f"[bold cyan]A executar carga assíncrona ({proto_label})... (Ctrl+C para parar)[/]"
    )
    progress_task_id = progress.add_task(initial_desc, total=None)

    semaphore = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient(
        headers=headers,
        limits=limits,
        timeout=timeout,
        follow_redirects=args.follow_redirects,
        verify=not args.insecure,
        http2=use_http2,
    ) as client:
        tasks = [
            asyncio.create_task(
                worker_task(
                    client,
                    semaphore,
                    stop_event,
                    warmup_done_event,
                    metrics,
                    method,
                    url,
                    body,
                    rate_limiter,
                    args.requests,
                )
            )
            for _ in range(concurrency)
        ]

        async def lifecycle_timer() -> None:
            if args.warmup > 0:
                await asyncio.sleep(args.warmup)
                metrics.reset()
                warmup_done_event.set()
                progress.update(
                    progress_task_id,
                    description=f"[bold cyan]A executar carga assíncrona ({proto_label})... (Ctrl+C para parar)[/]",
                )
            if args.duration and args.duration > 0:
                await asyncio.sleep(args.duration)
                stop_event.set()

        timer_task: asyncio.Task[None] | None = None
        if args.warmup > 0 or (args.duration and args.duration > 0):
            timer_task = asyncio.create_task(lifecycle_timer())

        try:
            if quiet:
                await stop_event.wait()
            else:
                with Live(build_ui(metrics.summary(), progress), console=console, refresh_per_second=12) as live:
                    while not stop_event.is_set():
                        live.update(build_ui(metrics.summary(), progress))
                        await asyncio.sleep(0.1)
                    live.update(build_ui(metrics.summary(), progress))
        except KeyboardInterrupt:
            stop_event.set()
        finally:
            stop_event.set()
            if timer_task is not None:
                timer_task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    final_data = metrics.summary()
    final_data.pop("last_event_code", None)
    final_data["target"] = url
    final_data["method"] = method
    final_data["concurrency"] = concurrency
    final_data["warmup_sec"] = args.warmup
    final_data["http2_enabled"] = use_http2
    final_data["author"] = "TrionixDev"
    final_data["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    return final_data


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="BasicDOS — Motor assíncrono de testes de carga HTTP/HTTPS (HTTP/2) — Made by TrionixDev."
    )
    parser.add_argument("url", nargs="?", help="URL alvo (ex.: https://exemplo.local/health)")
    parser.add_argument("-m", "--method", default="GET", help="Método HTTP (GET, POST, PUT, DELETE, HEAD)")
    parser.add_argument("-c", "--concurrency", type=int, default=100, help="Concorrência máxima (padrão: 100)")
    parser.add_argument("-n", "--requests", type=int, default=0, help="Número total de pedidos (0 = sem limite)")
    parser.add_argument("-t", "--timeout", type=float, default=5.0, help="Timeout por pedido em seg (padrão: 5.0)")
    parser.add_argument("-d", "--duration", type=float, default=0.0, help="Duração máxima em seg (0 = até Ctrl+C)")
    parser.add_argument("--warmup", type=float, default=0.0, help="Duração de aquecimento em seg antes de medir (padrão: 0)")
    parser.add_argument("--max-rps", type=float, default=0.0, help="Limite global aproximado de RPS (0 = sem limite)")
    parser.add_argument(
        "--http2",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Ativar/desativar HTTP/2 sobre HTTPS (padrão: ativado)",
    )
    parser.add_argument("-H", "--header", action="append", default=[], help="Cabeçalho extra 'Chave:Valor' (repetível)")
    parser.add_argument("--bearer", default=None, help="Token Bearer para cabeçalho Authorization")
    parser.add_argument("--basic-auth", default=None, help="Credenciais Basic Auth no formato 'utilizador:password'")
    parser.add_argument("--data", default=None, help="Corpo do pedido (ex.: '{\"ping\":1}')")
    parser.add_argument("--data-file", default=None, help="Caminho de ficheiro para carregar o corpo do pedido")
    parser.add_argument("--follow-redirects", action="store_true", help="Seguir redirecionamentos HTTP/HTTPS")
    parser.add_argument("--insecure", action="store_true", help="Desativar validação TLS/SSL (apenas testes locais)")
    parser.add_argument("-q", "--quiet", action="store_true", help="Modo silencioso sem painel interativo (ideal para CI)")
    parser.add_argument("-o", "--output", default=None, help="Guardar resumo em ficheiro JSON")
    parser.add_argument("--csv", default=None, help="Guardar/anexar resumo em ficheiro CSV")
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    if not args.quiet:
        clear_screen()
        print_banner()

    has_cli_flags = any(
        [
            args.url is not None,
            args.method != "GET",
            args.concurrency != 100,
            args.requests != 0,
            args.timeout != 5.0,
            args.duration != 0.0,
            args.warmup != 0.0,
            args.max_rps != 0.0,
            args.http2 is False,
            bool(args.header),
            args.bearer is not None,
            args.basic_auth is not None,
            args.data is not None,
            args.data_file is not None,
            args.follow_redirects,
            args.insecure,
            args.quiet,
            args.output is not None,
            args.csv is not None,
        ]
    )

    try:
        if not has_cli_flags:
            args = interactive_wizard()

        result = asyncio.run(run_load_test(args))
    except KeyboardInterrupt:
        if not args.quiet:
            console.print("\n[bold yellow]Interrompido pelo utilizador (Ctrl+C).[/]")
        sys.exit(0)
    except ValueError as exc:
        console.print(f"\n[bold red]Erro de configuração: {exc}[/]")
        sys.exit(1)
    except OSError as exc:
        console.print(f"\n[bold red]Erro de I/O: {exc}[/]")
        sys.exit(1)

    if args.quiet:
        print(json.dumps(result, ensure_ascii=False))
    else:
        console.print("\n[bold yellow]Teste concluído — Made by TrionixDev.[/]\n")
        summary_table = Table(title="Resumo Final (BasicDOS — TrionixDev)", border_style="bright_yellow")
        summary_table.add_column("Métrica", style="bright_yellow")
        summary_table.add_column("Valor", style="bold white")

        for key, val in result.items():
            if key == "status_codes" and isinstance(val, dict):
                formatted = ", ".join(f"{k}: {v}" for k, v in val.items()) or "-"
                summary_table.add_row(key, formatted)
            else:
                summary_table.add_row(key, str(val))
        console.print(summary_table)

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        if not args.quiet:
            console.print(f"\n[bold green]Relatório JSON guardado em:[/] {out_path.resolve()}")

    if args.csv:
        csv_path = Path(args.csv)
        export_csv(csv_path, result)
        if not args.quiet:
            console.print(f"[bold green]Relatório CSV guardado em:[/] {csv_path.resolve()}")


if __name__ == "__main__":
    main()
