#!/usr/bin/env python3
"""RAEN Innovation 50 - x402 Demand Signal / Repeat-Buyer Monitor.

Closes the KPI gap no other cookbook tool covers. The owner KPI is
"repeat buyers x calls/payer" and money truth is the chain, yet every
existing tool grades the wall/docs/wallet/receipt. NONE turns the
settlement-collector's OWN verified ledger into a demand signal that
separates genuine external payers from internal test traffic and
breadth-class crawler dust. This tool does exactly that.

READ-ONLY, stdlib-only. No signing, no X-PAYMENT header, no funds
movement, no external sends, no directory POSTs, no deploys, no secrets.
It reads only public GET surfaces (collector /stats, /ledger.json) plus
optional UNPAID 402 probes of kept-live paid walls for a price/demand
cross-reference. Frozen apps are never touched.

Usage:
  python3 scripts/demand-signal.py
  python3 scripts/demand-signal.py --out registry/demand-signal.json
  python3 scripts/demand-signal.py --no-live

Exit: 0 = report emitted, 1 = fetch error, 2 = no ledger transactions.
"""
import argparse
import base64
import datetime
import json
import sys
import urllib.error
import urllib.request

VERSION = "demand-signal/1.0"
STATS_URL = "https://settlement-collector.fly.dev/stats"
LEDGER_URL = "https://settlement-collector.fly.dev/ledger.json"
CANONICAL = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept": "application/json"}

# Breadth-class / crawler payers recorded in Library artifacts (TIFF-BUYER-05).
# A payment from one of these is a real on-chain transfer but NOT demand:
# these wallets scatter dust across hundreds of payees at p50 $0.003.
KNOWN_NON_BUYERS = {
    "0xc9c7b38c0942914fc8ea12063bc92dcd3b581670": "breadth-crawler TIFF-BUYER-05 (recWIQUYkLMfYRAw7)",
}

# Kept-live paid walls for the optional price/demand cross-reference.
# (service, url, method, body) - body None => GET. Unpaid probe only.
LIVE_WALLS = [
    ("royal-ruby", "https://royal-ruby-x402.fly.dev/api/law-lookup", "POST", {"text": "probe"}),
    ("contract-eye", "https://contract-eye-x402.fly.dev/api/analyze-contract", "POST", {"text": "probe"}),
    ("nanobanana", "https://nanobanana-x402.fly.dev/api/generate-image", "POST", {"prompt": "probe"}),
    ("shipgate402", "https://shipgate402.fly.dev/v1/ship-check/batch", "POST", {"urls": ["https://example.com"]}),
]


def get_json(url, timeout=20):
    req = urllib.request.Request(url, headers=UA, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def live_price(url, method, body):
    """UNPAID probe -> decoded x402 v2 challenge price. No payment header, ever."""
    data = json.dumps(body).encode() if body is not None else None
    headers = dict(UA)
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return {"status": r.status, "note": "paid route answered without 402"}
    except urllib.error.HTTPError as e:
        if e.code != 402:
            return {"status": e.code, "note": "not a 402"}
        raw = e.headers.get("payment-required", "")
        if not raw:
            return {"status": 402, "note": "402 without payment-required header"}
        try:
            pad = "=" * (-len(raw) % 4)
            env = json.loads(base64.urlsafe_b64decode(raw + pad))
            acc = (env.get("accepts") or [{}])[0]
            amt = acc.get("amount")
            try:
                amt_int = int(amt)
                price_usd = amt_int / 1e6
            except (TypeError, ValueError):
                amt_int, price_usd = None, None
            return {
                "status": 402,
                "x402Version": env.get("x402Version"),
                "scheme": acc.get("scheme"),
                "network": acc.get("network"),
                "asset": acc.get("asset"),
                "payTo": acc.get("payTo"),
                "amount_atomic": amt_int,
                "price_usd": price_usd,
                "canonical": str(acc.get("payTo", "")).lower() == CANONICAL.lower(),
            }
        except Exception as ex:
            return {"status": 402, "note": "challenge decode failed: " + str(ex)[:50]}
    except Exception as ex:
        return {"status": None, "note": "unreachable: " + str(ex)[:50]}


def analyze(ledger, stats):
    txs = ledger.get("transactions", [])
    by_class = {"internal": 0, "external": 0, "crawler": 0, "other": 0}
    genuine = {}   # payer -> {count, usd, services}
    crawlers = {}  # payer -> {count, usd, label}
    per_service = {}
    for t in txs:
        payer = str(t.get("payer", "")).lower()
        usd = float(t.get("amount_usd") or 0)
        svc = t.get("service", "unknown")
        cls = t.get("classification", "other")
        if payer in KNOWN_NON_BUYERS:
            by_class["crawler"] += 1
            c = crawlers.setdefault(payer, {"count": 0, "usd": 0.0, "label": KNOWN_NON_BUYERS[payer]})
            c["count"] += 1
            c["usd"] += usd
        elif cls == "external":
            by_class["external"] += 1
            g = genuine.setdefault(payer, {"count": 0, "usd": 0.0, "services": set()})
            g["count"] += 1
            g["usd"] += usd
            g["services"].add(svc)
        elif cls == "internal":
            by_class["internal"] += 1
        else:
            by_class["other"] += 1
        ps = per_service.setdefault(svc, {"genuine_external_tx": 0, "genuine_external_usd": 0.0, "all_tx": 0})
        ps["all_tx"] += 1
        if cls == "external" and payer not in KNOWN_NON_BUYERS:
            ps["genuine_external_tx"] += 1
            ps["genuine_external_usd"] += usd

    genuine_out = []
    for payer, g in sorted(genuine.items(), key=lambda kv: -kv[1]["usd"]):
        genuine_out.append({
            "payer": payer, "calls": g["count"], "usd": round(g["usd"], 6),
            "services": sorted(g["services"]),
        })
    repeat = [g for g in genuine_out if g["calls"] > 1]
    honest_external_usd = round(sum(g["usd"] for g in genuine_out), 6)
    f = stats.get("fleet_24h", {})
    if not genuine_out:
        verdict = "EVIDENCE_DEAD"
    elif repeat:
        verdict = "REPEAT_SIGNAL"
    else:
        verdict = "SINGLE_BUYER"

    return {
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "verdict": verdict,
        "honest_external_earned_usd": honest_external_usd,
        "kpi": {
            "distinct_genuine_external_payers": len(genuine_out),
            "repeat_buyers": len(repeat),
            "calls_per_payer": {g["payer"]: g["calls"] for g in genuine_out},
        },
        "classification_counts": by_class,
        "crawler_dust_usd": round(sum(c["usd"] for c in crawlers.values()), 6),
        "crawlers": crawlers,
        "genuine_external_payers": genuine_out,
        "per_service": per_service,
        "collector_24h": {
            "challenges": f.get("challenges"), "settled": f.get("settled"),
            "settled_verified": f.get("settled_verified"), "failed": f.get("failed"),
            "revenue_external_usd_reported": f.get("revenue_external_usd"),
        },
        "note": ("Collector revenue_external_usd counts any non-internal payer; this tool "
                 "re-excludes recorded breadth-class crawlers. Honest earned = chain-verified "
                 "external payments from genuine (non-crawler) payers only."),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", default=STATS_URL)
    ap.add_argument("--ledger", default=LEDGER_URL)
    ap.add_argument("--out", default=None, help="write JSON report here")
    ap.add_argument("--no-live", action="store_true", help="skip unpaid 402 cross-reference")
    args = ap.parse_args()
    try:
        ledger = get_json(args.ledger) if args.ledger.startswith("http") else json.load(open(args.ledger))
        stats = get_json(args.stats) if args.stats.startswith("http") else json.load(open(args.stats))
    except Exception as e:
        print("FETCH ERROR:", e, file=sys.stderr)
        return 1
    if not ledger.get("transactions"):
        print("No ledger transactions; nothing to analyze.", file=sys.stderr)
        return 2
    report = analyze(ledger, stats)
    if not args.no_live:
        walls = []
        for svc, url, method, body in LIVE_WALLS:
            walls.append({"service": svc, "url": url, "method": method, "challenge": live_price(url, method, body)})
        report["live_wall_cross_reference"] = walls
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print("wrote", args.out)
    k = report["kpi"]
    print("VERDICT:", report["verdict"])
    print("honest external earned USD: $%.6f" % report["honest_external_earned_usd"])
    print("genuine external payers:", k["distinct_genuine_external_payers"],
          "| repeat buyers:", k["repeat_buyers"])
    print("crawler dust USD (excluded): $%.6f" % report["crawler_dust_usd"])
    print("classification counts:", report["classification_counts"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
