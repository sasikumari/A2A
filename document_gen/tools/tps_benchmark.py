#!/usr/bin/env python3
import asyncio
import time
import argparse
import random
import string
from dataclasses import dataclass, asdict
from typing import List, Optional

try:
    import aiohttp
except ImportError:
    raise SystemExit("Please install aiohttp: pip install aiohttp")

DEFAULT_PAYER = "ramesh@payer"
DEFAULT_PAYEE = "merchant@benef"
DEFAULT_PIN = "1234"


def iso_ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def build_reqpay_xml(payer: str, payee: str, amount: float, note: str, pin: Optional[str] = None) -> str:
    ts = iso_ts()
    pin_block = f"<upi:Creds><upi:Cred><upi:Data code=\"{pin}\"/></upi:Cred></upi:Creds>" if pin else ""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<upi:ReqPay xmlns:upi="http://npci.org/upi/schema/">
  <upi:Head ver="1.0" ts="{ts}" orgId="PAYERPSP" msgId="REQUI" prodType="UPI"/>
  <upi:Txn id="REQ-{int(time.time()*1000)}" type="PAY" note="{note}"/>
  <upi:Payer addr="{payer}">
    <upi:Amount value="{amount:.2f}"/>
    {pin_block}
  </upi:Payer>
  <upi:Payees>
    <upi:Payee addr="{payee}"/>
  </upi:Payees>
</upi:ReqPay>""".strip()


def build_status_xml(rrn: str) -> str:
    return f'<?xml version="1.0" encoding="UTF-8"?><StatusRequest><RRN>{rrn}</RRN></StatusRequest>'


def rand_note(length: int = 6) -> str:
    return "perf-" + "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))


@dataclass
class Result:
    ok: bool
    latency_ms: float
    rrn: str = ""
    error: str = ""


@dataclass
class Summary:
    total: int
    success: int
    failed: int
    duration_s: float
    achieved_rps: float
    p50_ms: float
    p90_ms: float
    p95_ms: float
    p99_ms: float


def percentile(latencies: List[float], pct: float) -> float:
    if not latencies:
        return 0.0
    latencies_sorted = sorted(latencies)
    k = (len(latencies_sorted) - 1) * pct
    f = int(k)
    c = min(f + 1, len(latencies_sorted) - 1)
    if f == c:
        return latencies_sorted[int(k)]
    d0 = latencies_sorted[f] * (c - k)
    d1 = latencies_sorted[c] * (k - f)
    return d0 + d1


async def worker(name: str, session: aiohttp.ClientSession, queue: asyncio.Queue, results: List[Result], host: str, poll_status: bool, status_timeout_s: float):
    while True:
        try:
            item = await queue.get()
        except asyncio.CancelledError:
            return
        if item is None:
            queue.task_done()
            return
        payer, payee, amount, pin = item
        xml = build_reqpay_xml(payer, payee, amount, rand_note(), pin)
        t0 = time.perf_counter()
        try:
            async with session.post(f"{host}/reqpay", data=xml.encode("utf-8"), headers={"Content-Type": "application/xml"}) as resp:
                text = await resp.text()
                ok = resp.status == 202
                rrn = ""
                if ok:
                    # Expect JSON: {"rrn": "...", "status": "ACK"}
                    try:
                        data = await resp.json()
                        rrn = str(data.get("rrn", "")) if isinstance(data, dict) else ""
                    except Exception:
                        ok = False
                if ok and poll_status and rrn:
                    # best-effort poll until terminal or timeout
                    end_by = time.perf_counter() + status_timeout_s
                    status = "PENDING"
                    while time.perf_counter() < end_by and status == "PENDING":
                        s_xml = build_status_xml(rrn)
                        async with session.post(f"{host}/status", data=s_xml.encode("utf-8"), headers={"Content-Type": "application/xml"}) as s_resp:
                            s_text = await s_resp.text()
                            if s_resp.status == 200 and "<Status>" in s_text:
                                try:
                                    start = s_text.index("<Status>") + len("<Status>")
                                    end = s_text.index("</Status>")
                                    status = s_text[start:end].strip().upper()
                                except Exception:
                                    status = "PENDING"
                            else:
                                # keep pending on transient issues
                                status = "PENDING"
                        if status == "PENDING":
                            await asyncio.sleep(0.2)
                    ok = (status == "SUCCESS")
                latency_ms = (time.perf_counter() - t0) * 1000.0
                results.append(Result(ok=ok, latency_ms=latency_ms, rrn=rrn, error="" if ok else text[:200]))
        except Exception as e:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            results.append(Result(ok=False, latency_ms=latency_ms, rrn="", error=str(e)))
        finally:
            queue.task_done()


async def run_benchmark(host: str, rps: float, duration_s: float, concurrency: int, amount: float, payer: str, payee: str, pin: str, poll_status: bool, status_timeout_s: float) -> Summary:
    total_requests = int(rps * duration_s)
    queue: asyncio.Queue = asyncio.Queue(maxsize=concurrency * 2)
    results: List[Result] = []
    timeout = aiohttp.ClientTimeout(total=max(10.0, status_timeout_s + 10.0))
    connector = aiohttp.TCPConnector(limit=0)
    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        # Launch workers
        workers = [asyncio.create_task(worker(f"w{i}", session, queue, results, host, poll_status, status_timeout_s)) for i in range(concurrency)]

        # Producer: schedule requests at fixed interval
        interval = 1.0 / max(1.0, rps)
        start_time = time.perf_counter()
        for _ in range(total_requests):
            await queue.put((payer, payee, amount, pin))
            # Sleep to maintain target RPS
            t_next = start_time + (_ + 1) * interval
            now = time.perf_counter()
            if t_next > now:
                await asyncio.sleep(t_next - now)
        # Drain
        await queue.join()
        for _ in workers:
            await queue.put(None)
        await asyncio.gather(*workers, return_exceptions=True)

    # Summarize
    elapsed = time.perf_counter() - start_time
    latencies = [r.latency_ms for r in results if r.ok]
    success = sum(1 for r in results if r.ok)
    failed = len(results) - success
    achieved_rps = len(results) / max(1e-6, elapsed)
    summary = Summary(
        total=len(results),
        success=success,
        failed=failed,
        duration_s=elapsed,
        achieved_rps=achieved_rps,
        p50_ms=percentile(latencies, 0.50),
        p90_ms=percentile(latencies, 0.90),
        p95_ms=percentile(latencies, 0.95),
        p99_ms=percentile(latencies, 0.99),
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description="UPI Simulator TPS Benchmark (/reqpay)")
    parser.add_argument("--host", default="http://127.0.0.1:5000", help="Base URL of running API (default: http://127.0.0.1:5000)")
    parser.add_argument("--rps", type=float, default=50.0, help="Target requests per second (default: 50)")
    parser.add_argument("--duration", type=float, default=10.0, help="Test duration in seconds (default: 10)")
    parser.add_argument("--concurrency", type=int, default=100, help="Concurrent workers (default: 100)")
    parser.add_argument("--amount", type=float, default=1.00, help="Payment amount (default: 1.00)")
    parser.add_argument("--payer", default=DEFAULT_PAYER, help=f"Payer VPA (default: {DEFAULT_PAYER})")
    parser.add_argument("--payee", default=DEFAULT_PAYEE, help=f"Payee VPA (default: {DEFAULT_PAYEE})")
    parser.add_argument("--pin", default=DEFAULT_PIN, help=f"PIN (default: {DEFAULT_PIN})")
    parser.add_argument("--poll-status", action="store_true", help="Poll /status until terminal (affects throughput)")
    parser.add_argument("--status-timeout", type=float, default=8.0, help="Per-txn status polling timeout seconds (default: 8)")
    args = parser.parse_args()

    print("Starting TPS benchmark with:", {
        "host": args.host, "rps": args.rps, "duration": args.duration, "concurrency": args.concurrency,
        "amount": args.amount, "poll_status": args.poll_status
    })
    summary = asyncio.run(run_benchmark(
        host=args.host,
        rps=args.rps,
        duration_s=args.duration,
        concurrency=args.concurrency,
        amount=args.amount,
        payer=args.payer,
        payee=args.payee,
        pin=args.pin,
        poll_status=args.poll_status,
        status_timeout_s=args.status_timeout,
    ))
    print("\n=== Benchmark Summary ===")
    for k, v in asdict(summary).items():
        if isinstance(v, float):
            print(f"{k}: {v:.2f}")
        else:
            print(f"{k}: {v}")


if __name__ == "__main__":
    try:
        import uvloop  # type: ignore
        uvloop.install()
    except Exception:
        pass
    main()


