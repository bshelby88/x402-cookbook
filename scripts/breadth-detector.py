#!/usr/bin/env python3
"""51. Breadth-Crawler Detector - discover dust-scatter payers from on-chain behaviour.

Read-only, stdlib-only. No signing, no X-PAYMENT, no funds movement, no deploy.

The settlement-collector labels any non-internal payer "external". Two real
breadth-class crawlers have been misbooked as external revenue:
  0xc9c7b38c...1670 (TIFF-BUYER-05: 156 payees / 6.4d, p50 $0.003)
  0x171d8021...50fca (discovered 2026-11-27: 18 recipients / 40 transfers / 28 min)
A hardcoded exclusion list cannot keep up. This tool DISCOVERS breadth-scatter
payers from behaviour: distinct recipients + transfer count + burst span, read
from Base USDC Transfer logs. Honest external earned = collector external minus
payers the detector flags as breadth-class.

Usage:
  python3 breadth-detector.py                 # live run -> registry/breadth-detector.json
  python3 breadth-detector.py --check          # verify snapshot reproducible (exit 0 = canonical)
  python3 breadth-detector.py --address 0x...  # classify one address standalone
"""
import argparse, datetime, json, os, subprocess, sys, time, urllib.request

RPC = "https://base.publicnode.com"
USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
SIG = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
LEDGER = "https://settlement-collector.fly.dev/ledger.json"
STATS = "https://settlement-collector.fly.dev/stats"
LOOKBACK_BLOCKS = 200000          # ~14h at ~345k blocks/day
CHUNK = 40000                     # publicnode rejects >50000-block eth_getLogs
MIN_RECIPIENTS = 8                # breadth signature
BURST_TX = 15                     # burst signature
BURST_MINUTES = 60
HERE = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(HERE, "..", "registry", "breadth-detector.json")

UA = {"User-Agent": "Mozilla/5.0 (compatible; raen-breadth-detector/1.0)"}


def rpc(method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    p = subprocess.run(["curl", "-s", "-X", "POST", RPC, "-H", "Content-Type: application/json",
                        "--data-raw", body], capture_output=True, text=True, timeout=60)
    try:
        return json.loads(p.stdout)
    except Exception:
        return {"error": "parse: " + (p.stdout or "")[:80] + (p.stderr or "")[:40]}


def get_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def classify(payer, current_block):
    """Return behavioural facts + verdict for one payer's USDC outflow."""
    topic_from = "0x" + "0" * 24 + payer.lower().replace("0x", "")
    start = max(0, current_block - LOOKBACK_BLOCKS)
    rows, block_ts = [], {}
    b = start
    while b <= current_block:
        end = min(b + CHUNK - 1, current_block)
        r = rpc("eth_getLogs", [{"address": USDC, "fromBlock": hex(b), "toBlock": hex(end),
                                 "topics": [SIG, topic_from, None]}])
        if "error" in r:
            time.sleep(6)
            b = end + 1
            continue
        for lg in r.get("result", []):
            to = "0x" + lg["topics"][2][-40:]
            amt = int(lg["data"], 16) / 1e6
            rows.append((int(lg["blockNumber"], 16), to, amt))
        time.sleep(3.2)
        b = end + 1
    blocks = sorted(set(x[0] for x in rows))
    for bn in blocks:
        rr = rpc("eth_getBlockByNumber", [hex(bn), False])
        if "result" in rr and rr["result"]:
            block_ts[bn] = int(rr["result"]["timestamp"], 16)
        time.sleep(0.2)
    recipients = {}
    for bn, to, amt in rows:
        recipients[to] = recipients.get(to, 0.0) + amt
    times = [block_ts[b] for b in blocks if b in block_ts]
    span_min = round((max(times) - min(times)) / 60, 1) if times else None
    breadth = len(recipients) >= MIN_RECIPIENTS
    burst = len(rows) >= BURST_TX and span_min is not None and span_min <= BURST_MINUTES
    verdict = "BREADTH_CRAWLER" if (breadth or burst) else "GENUINE_PAYER"
    return {
        "verdict": verdict,
        "outgoing_transfers": len(rows),
        "distinct_recipients": len(recipients),
        "span_minutes": span_min,
        "breadth_signal": breadth,
        "burst_signal": burst,
        "total_usdc_out": round(sum(x[2] for x in rows), 6),
        "top_recipients": [{"addr": k, "usdc": round(v, 6)} for k, v in
                           sorted(recipients.items(), key=lambda x: -x[1])[:8]],
        "lookback_blocks": LOOKBACK_BLOCKS,
        "coverage": "partial-lookback" if len(rows) else "none-in-window",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--address")
    args = ap.parse_args()
    if args.address:
        cur = int(rpc("eth_blockNumber", [])["result"], 16)
        print(json.dumps({"payer": args.address, **classify(args.address, cur)}, indent=1))
        return
    ledger = get_json(LEDGER)
    stats = get_json(STATS)
    external = [t for t in ledger.get("transactions", []) if t.get("classification") == "external"]
    payers = sorted(set(t.get("payer", "").lower() for t in external if t.get("payer")))
    cur = int(rpc("eth_blockNumber", [])["result"], 16)
    findings = {}
    for p in payers:
        print("classifying", p, file=sys.stderr)
        findings[p] = classify(p, cur)
    crawlers = [p for p, f in findings.items() if f["verdict"] == "BREADTH_CRAWLER"]
    genuine = [p for p, f in findings.items() if f["verdict"] == "GENUINE_PAYER"]
    crawler_usd = round(sum(t.get("amount_usd", 0) for t in external
                            if t.get("payer", "").lower() in crawlers), 6)
    reported = stats.get("fleet_24h", {}).get("revenue_external_usd", 0)
    out = {
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "current_block": cur,
        "collector_reported_external_usd_24h": reported,
        "external_payers_scanned": payers,
        "findings": findings,
        "breadth_crawlers": crawlers,
        "genuine_payers": genuine,
        "crawler_usd_in_ledger": crawler_usd,
        "honest_external_earned_usd": round((reported or 0) - crawler_usd, 6),
        "verdict": "CRAWLER_NOISE" if crawlers and not genuine else
                   ("GENUINE_DEMAND" if genuine else "NO_EXTERNAL"),
        "note": ("Behavioural discovery: a payer with >=%d distinct USDC recipients or >=%d "
                 "transfers inside %d minutes is breadth-class scatter, not demand. "
                 "Collector revenue_external_usd counts these as external; this tool "
                 "subtracts them. Partial lookback is stated per payer." %
                 (MIN_RECIPIENTS, BURST_TX, BURST_MINUTES)),
    }
    text = json.dumps(out, indent=1, sort_keys=True) + "\n"
    if args.check:
        snap = json.load(open(SNAP))
        same = (snap.get("verdict") == out["verdict"] and
                snap.get("breadth_crawlers") == out["breadth_crawlers"])
        print("CHECK", "CANONICAL" if same else "DRIFT",
              "verdict", out["verdict"], "crawlers", out["breadth_crawlers"])
        sys.exit(0 if same else 1)
    with open(SNAP, "w") as f:
        f.write(text)
    print("SNAP", SNAP, len(text), "bytes")
    print("verdict", out["verdict"], "crawlers", crawlers,
          "honest_external_earned_usd", out["honest_external_earned_usd"])


if __name__ == "__main__":
    main()
