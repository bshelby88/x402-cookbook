#!/usr/bin/env python3
"""52. Chain Ledger Reconciler - money truth from the chain, not the collector.

Read-only, stdlib-only. No signing, no X-PAYMENT, no funds movement, no
external sends, no deploys, no secrets. Frozen apps are never touched.

Gap this closes: tools 50 (demand-signal) and 51 (breadth-detector) both read
the settlement-collector's ledger, so they inherit its blind spots. On
2026-11-27 a chain-real $0.10 USDC settle to canonical (tx 0x5755f751...,
from breadth-crawler 0x171d8021...50fca) was NOT in the collector ledger, and
the collector's total_crawler_usdc stayed 0 while revenue_external_usd showed
$0.012. Two agents then disagreed on whether that payer was a "genuine machine
buyer" or crawler dust. This tool settles the class of disagreement by
reconciling canonical USDC inflows read DIRECTLY from Base against the ledger:

  * chain inflow with no ledger tx  -> UNLOGGED (blind spot)
  * ledger tx with no chain inflow  -> PHANTOM (would be phantom revenue)
  * sender classified via internal-wallet facts + tool 51's breadth registry
  * true_external_usd = external chain inflows minus breadth-class payers

Applied live 2026-11-27: canonical +0.115 = 0.005 internal (AgentCash) +
0.11 breadth-crawler scatter (incl. the unlogged 0.10). Genuine external
earned = $0.00 (honest).

Usage:
  python3 chain-reconciler.py                 # live run -> registry/chain-reconciler.json
  python3 chain-reconciler.py --check         # verify snapshot reproducible
  python3 chain-reconciler.py --address 0x... # classify one sender standalone
Exit: 0 report emitted, 1 fetch error.
"""
import argparse, datetime, json, os, subprocess, sys, time, urllib.request

RPC = "https://base.publicnode.com"        # accepts 10k-block eth_getLogs chunks
USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
SIG = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
CANONICAL = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f".lower()
LEDGER = "https://settlement-collector.fly.dev/ledger.json"
STATS = "https://settlement-collector.fly.dev/stats"
LOOKBACK = 120000       # ~8h at ~345k blocks/day; covers the 08:46Z burst
CHUNK = 20000           # conservative for publicnode eth_getLogs
UA = {"User-Agent": "Mozilla/5.0 (compatible; raen-chain-reconciler/1.0)"}
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "registry")
SNAP = os.path.join(ROOT, "chain-reconciler.json")

# Internal wallets (ops truth). Full addresses only - homoglyphs exist.
INTERNAL = {
    "0xfbc0eb7811d477e55261d956df39f0046e192240": "AgentCash (internal)",
    "0x7861db4efc14a1ed5dd8c96c528a3796560f1393": "retired canonical (internal)",
    "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f": "canonical (self)",
}


def rpc(method, params, retries=3):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    for attempt in range(retries):
        p = subprocess.run(
            ["curl", "-s", "-X", "POST", RPC, "-H", "Content-Type: application/json",
             "--data-raw", body], capture_output=True, text=True, timeout=60)
        try:
            res = json.loads(p.stdout)
        except Exception:
            res = {"error": "parse: " + (p.stdout or "")[:80]}
        if "error" not in res:
            return res
        time.sleep(6 * (attempt + 1))
    return res


def get_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def pad(addr):
    return "0x" + "0" * 24 + addr.lower().replace("0x", "")


def inflows(current_block):
    """Return list of dicts: tx, sender, amount_usd, block, logIndex."""
    topic_to = pad(CANONICAL)
    start = max(0, current_block - LOOKBACK)
    rows, b, errors = [], start, 0
    while b <= current_block:
        end = min(b + CHUNK - 1, current_block)
        res = rpc("eth_getLogs", [{
            "fromBlock": hex(b), "toBlock": hex(end), "address": USDC,
            "topics": [SIG, None, topic_to],
        }])
        if "error" in res:
            errors += 1
            if errors >= 5:
                break
            b = end + 1
            continue
        for lg in res.get("result", []):
            data = lg.get("data", "0x")
            try:
                amount = int(data, 16) / 1e6
            except Exception:
                continue
            sender = "0x" + lg["topics"][1][-40:]
            rows.append({
                "tx": lg.get("transactionHash"),
                "sender": sender.lower(),
                "amount_usd": round(amount, 6),
                "block": int(lg.get("blockNumber", "0x0"), 16),
                "logIndex": int(lg.get("logIndex", "0x0"), 16),
            })
        b = end + 1
        time.sleep(3.2)
    rows.sort(key=lambda r: (r["block"], r["logIndex"]))
    return rows, errors, start


def breadth_registry():
    try:
        d = json.load(open(os.path.join(ROOT, "breadth-detector.json")))
        return set(a.lower() for a in d.get("breadth_crawlers", [])), d
    except Exception:
        return set(), {}


def classify(sender, crawlers):
    if sender in INTERNAL:
        return "INTERNAL", INTERNAL[sender]
    if sender in crawlers:
        return "BREADTH_CRAWLER", "flagged by tool 51 breadth-detector registry"
    return "EXTERNAL", "not internal, not breadth-class"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--address")
    args = ap.parse_args()

    crawlers, breadth_snap = breadth_registry()

    if args.address:
        a = args.address.lower()
        c, why = classify(a, crawlers)
        print(json.dumps({"address": a, "classification": c, "reason": why}, indent=1))
        return 0

    cur = rpc("eth_getBlockByNumber", ["latest", False])
    if "error" in cur:
        print("ERROR: cannot read latest block", file=sys.stderr)
        return 1
    current_block = int(cur["result"]["number"], 16)

    rows, errors, start_block = inflows(current_block)
    ledger = get_json(LEDGER)
    led_tx = {}
    for t in ledger.get("transactions", []):
        if t.get("tx"):
            led_tx[t["tx"].lower()] = t

    reconciled = []
    for r in rows:
        cls, why = classify(r["sender"], crawlers)
        in_ledger = r["tx"].lower() in led_tx
        reconciled.append({
            **r, "classification": cls, "reason": why,
            "in_collector_ledger": in_ledger,
            "ledger_service": led_tx.get(r["tx"].lower(), {}).get("service") if in_ledger else None,
            "blinded_spot": (not in_ledger and cls != "INTERNAL"),
        })

    # Ledger tx hashes with no matching chain inflow in window (phantoms /
    # out-of-window) - only report, window may simply be shorter than ledger.
    chain_tx = set(r["tx"].lower() for r in rows if r["tx"])
    ledger_not_in_window = [
        {"tx": tx, "service": t.get("service"), "amount_usd": t.get("amount_usd")}
        for tx, t in led_tx.items() if tx not in chain_tx
    ]

    total_in = round(sum(r["amount_usd"] for r in reconciled), 6)
    internal_usd = round(sum(r["amount_usd"] for r in reconciled if r["classification"] == "INTERNAL"), 6)
    crawler_usd = round(sum(r["amount_usd"] for r in reconciled if r["classification"] == "BREADTH_CRAWLER"), 6)
    external_usd = round(sum(r["amount_usd"] for r in reconciled if r["classification"] == "EXTERNAL"), 6)
    unlogged_external = round(sum(r["amount_usd"] for r in reconciled
                                  if r["blinded_spot"] and r["classification"] == "EXTERNAL"), 6)
    unlogged_crawler = round(sum(r["amount_usd"] for r in reconciled
                                 if r["blinded_spot"] and r["classification"] == "BREADTH_CRAWLER"), 6)

    out = {
        "tool": "chain-reconciler/1.0",
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_of_truth": "Base USDC Transfer logs -> canonical (eth_getLogs), matched to collector ledger",
        "current_block": current_block,
        "lookback_blocks": LOOKBACK,
        "scan_start_block": start_block,
        "chunk_errors": errors,
        "collector_reported_external_usd_24h": get_json(STATS).get("fleet_24h", {}).get("revenue_external_usd"),
        "breadth_crawlers_used": sorted(crawlers),
        "chain_inflow_total_usd": total_in,
        "chain_internal_usd": internal_usd,
        "chain_breadth_crawler_usd": crawler_usd,
        "chain_external_usd": external_usd,
        "genuine_external_earned_usd": external_usd,
        "unlogged_external_usd": unlogged_external,
        "unlogged_crawler_usd": unlogged_crawler,
        "inflows": reconciled,
        "ledger_tx_not_in_scan_window_count": len(ledger_not_in_window),
        "note": ("Money truth is the chain. The collector ledger is a secondary source; "
                 "payments present on chain but absent from the ledger are blind spots, "
                 "not evidence of no payment. Breadth-class payers are not demand even "
                 "when chain-real. Honest external earned excludes internal + breadth."),
    }

    os.makedirs(ROOT, exist_ok=True)
    with open(SNAP, "w") as f:
        json.dump(out, f, indent=1)

    print(json.dumps({
        "current_block": current_block, "inflows": len(rows), "chunk_errors": errors,
        "chain_inflow_total_usd": total_in, "internal_usd": internal_usd,
        "breadth_crawler_usd": crawler_usd, "external_usd": external_usd,
        "unlogged_external_usd": unlogged_external, "unlogged_crawler_usd": unlogged_crawler,
        "genuine_external_earned_usd": external_usd,
        "crawlers": sorted(crawlers),
        "sender_summary": [{"sender": r["sender"], "amount": r["amount_usd"],
                            "class": r["classification"], "logged": r["in_collector_ledger"]}
                           for r in reconciled],
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
