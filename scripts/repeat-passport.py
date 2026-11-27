#!/usr/bin/env python3
"""RAEN Innovation 55 - Machine-Buyer Repeat Passport.

Closes the gap between "a canonical 402 is a promise" and "this payer has a
verifiable track record of settled calls". An autonomous buyer evaluating
whether to integrate a RAEN wall asks: "can I prove my own spend, and does
anyone measure repeat buyers?" Tools 41-54 grade walls, docs, wallets,
receipts, trust, crawlers, chain, funnel and settlement dependability. NONE
turns a payer's OWN on-chain settlement history into a portable, agent-readable
credential, nor measures the owner's actual KPI (repeat buyers x calls/payer)
from chain truth. This tool does both.

DELIVERABLE (two artifacts in one report):
  1. Spend PASSPORT per external payer: verified_spend_usd, distinct_walls,
     calls, receipts[], repeat_status -- a portable trust signal an agent can
     present. Built from VERIFIED Base receipts, never collector claims.
  2. Fleet KPI CARD: repeat_buyers, calls_per_payer, honest_external_earned.

TRUTH LAW: money truth = chain. Every external tx is re-read with
eth_getTransactionReceipt on Base and its ERC-20 Transfer log decoded to
confirm value + to==canonical + status 0x1. The collector ledger is only a
candidate list; a claim without a verified receipt is NOT counted. Internal
wallets and known breadth-crawler dust are excluded. A settle with no delivery
evidence is RECEIVED, not EARNED -- honest_external_earned stays 0.00 unless a
delivery signal is present.

READ-ONLY, stdlib-only. No signing, no X-PAYMENT header, no funds movement, no
external sends, no directory POSTs, no deploys, no secrets, no frozen app
touched. Only public GET (collector) + read-only JSON-RPC (public Base RPC).

Usage:
  python3 scripts/repeat-passport.py
  python3 scripts/repeat-passport.py --out registry/repeat-passport.json
  python3 scripts/repeat-passport.py --payer 0x171d8021b98c53dcbb3c9c30cbbbeb1b01850fca
  python3 scripts/repeat-passport.py --no-verify    # collector-only, marked UNVERIFIED

Exit: 0 = report emitted, 1 = fetch error, 2 = no ledger transactions.
"""
import argparse
import datetime
import json
import sys
import urllib.error
import urllib.request

VERSION = "repeat-passport/1.0"
STATS_URL = "https://settlement-collector.fly.dev/stats"
LEDGER_URL = "https://settlement-collector.fly.dev/ledger.json"
CANONICAL = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f"
BASE_USDC = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
TRANSFER_SIG = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
RPCS = ["https://base.publicnode.com", "https://mainnet.base.org"]
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

# Acquired data (Library artifacts / ops truth). Internal fleet wallets are
# NEVER revenue. Breadth-crawler dust is a real transfer but NOT demand.
# Both addresses below were behaviour-classified BREADTH_CRAWLER by tools 51/52
# (registry/breadth-detector.json + registry/chain-reconciler.json):
#   0x171d8021...50fca = 41 tx / 20 recipients / 33 min, incl. a $0.10 scatter
#   0xc9c7b38c...1670  = 114 tx / 35 recipients / 6 h
# A passport is a REPEAT-BUYER credential, so issuing one to dust would be a
# false demand claim. Per TRUTH law and tool 52's ruling, they are excluded.
INTERNAL_WALLETS = {
    "0xfbc0eb7811d477e55261d956df39f0046e192240",  # AgentCash (FULL address)
    "0x7861db4efc14a1ed5dd8c96c528a3796560f1393",  # retired canonical
}
KNOWN_NON_BUYERS = {
    "0x171d8021b98c53dcbb3c9c30cbbbeb1b01850fca": "breadth-crawler (tool 51: 41 tx/20 recipients/33min; tool 52: $0.10 = scatter, NOT demand)",
    "0xc9c7b38c0942914fc8ea12063bc92dcd3b581670": "breadth-crawler TIFF-BUYER-05 (156 payees/6.4d, p50 $0.003, U5-excluded)",
}


def get_json(url, timeout=20):
    req = urllib.request.Request(url, headers=UA, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def rpc(url, method, params, timeout=25):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    headers = dict(UA)
    headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def base_rpc():
    """Return first Base RPC that confirms chainId 0x2105 (reject silent 0.0 RPCs)."""
    for url in RPCS:
        try:
            res = rpc(url, "eth_chainId", [])
            if "error" not in res and str(res.get("result", "")).lower() == "0x2105":
                return url
        except Exception:
            continue
    return None


def verify_receipt(url, tx):
    """Verify one tx on-chain; return verified transfer facts or None.

    EIP-3009 settles have a relayer as tx.from, so attribute the payer from the
    Transfer log's topics[1], NOT from the tx sender.
    """
    try:
        res = rpc(url, "eth_getTransactionReceipt", [tx])
    except Exception:
        return None
    if "error" in res or not res.get("result"):
        return None
    rec = res["result"]
    if str(rec.get("status", "")).lower() != "0x1":
        return None
    out = []
    for lg in rec.get("logs", []):
        topics = lg.get("topics", [])
        if not topics or str(topics[0]).lower() != TRANSFER_SIG:
            continue
        try:
            contract = str(lg.get("address", "")).lower()
            frm = "0x" + str(topics[1])[-40:]
            to = "0x" + str(topics[2])[-40:]
            atoms = int(lg.get("data", "0x0"), 16)
        except Exception:
            continue
        out.append({
            "contract": contract,
            "from": frm.lower(),
            "to": to.lower(),
            "usdc": round(atoms / 1e6, 6),
            "is_usdc": contract == BASE_USDC,
            "to_canonical": to.lower() == CANONICAL.lower(),
        })
    return {
        "tx": tx,
        "status": "0x1",
        "block": int(rec.get("blockNumber", "0x0"), 16),
        "transfers": out,
    }


def classify(payer):
    p = str(payer).lower()
    if p in INTERNAL_WALLETS:
        return "internal"
    if p in KNOWN_NON_BUYERS:
        return "crawler_dust"
    return "external"


def analyze(ledger, verify=True):
    rpc_url = base_rpc() if verify else None
    txs = ledger.get("transactions", [])
    payers = {}
    crawler_records = {}
    for t in txs:
        payer = str(t.get("payer", "")).lower()
        cls = classify(payer)
        if cls == "internal":
            continue  # fleet test traffic, never a buyer
        if cls == "crawler_dust":
            c = crawler_records.setdefault(payer, {
                "payer": payer, "calls": 0, "logged_usd": 0.0,
                "services": set(), "evidence": KNOWN_NON_BUYERS[payer],
            })
            c["calls"] += 1
            c["logged_usd"] += float(t.get("amount_usd") or 0)
            c["services"].add(t.get("service", "unknown"))
            continue  # real transfers, but dust-scatter discovery — NOT demand
        tx = t.get("tx", "")
        entry = payers.setdefault(payer, {
            "payer": payer,
            "classification": cls,
            "calls_logged": 0,
            "services": set(),
            "logged_usd": 0.0,
            "receipts": [],
            "verified": 0,
            "verified_usd": 0.0,
            "delivery_seen": 0,
        })
        entry["calls_logged"] += 1
        entry["services"].add(t.get("service", "unknown"))
        entry["logged_usd"] += float(t.get("amount_usd") or 0)
        if t.get("fulfilled") is not None or t.get("delivery") is not None:
            entry["delivery_seen"] += 1
        if verify and tx and rpc_url:
            vr = verify_receipt(rpc_url, tx)
            confirmed = False
            payer_from = None
            if vr:
                for tr in vr["transfers"]:
                    if tr["is_usdc"] and tr["to_canonical"] and tr["from"] == payer:
                        entry["verified"] += 1
                        entry["verified_usd"] += tr["usdc"]
                        confirmed = True
                        payer_from = tr["from"]
            entry["receipts"].append({
                "tx": tx,
                "service": t.get("service", "unknown"),
                "route": t.get("route", ""),
                "logged_usd": float(t.get("amount_usd") or 0),
                "receipt_verified": confirmed,
                "status": vr["status"] if vr else "unverified",
                "block": vr["block"] if vr else None,
                "from": payer_from,
            })

    passports = []
    for payer, e in payers.items():
        calls = e["verified"] if verify else e["calls_logged"]
        spend = round(e["verified_usd"] if verify else e["logged_usd"], 6)
        distinct_walls = len(e["services"])
        if calls >= 2 or distinct_walls >= 2:
            repeat = "REPEAT_BUYER"
        elif calls == 1:
            repeat = "TOURIST"
        else:
            repeat = "UNVERIFIED"
        if e["delivery_seen"] > 0:
            earned_scope = "EARNED_DELIVERY_CONFIRMED"
        else:
            earned_scope = "RECEIVED_DELIVERY_UNVERIFIED"
        passports.append({
            "payer": payer,
            "passport_id": "RAEN-PP-" + payer[2:14],
            "repeat_status": repeat,
            "calls_verified" if verify else "calls_logged": calls,
            "distinct_walls": distinct_walls,
            "walls": sorted(e["services"]),
            "verified_spend_usd" if verify else "logged_spend_usd": spend,
            "earned_scope": earned_scope,
            "honest_external_earned_usd": 0.0,  # no delivery proof => 0.00
            "receipts": e["receipts"],
            "evidence_basis": "on-chain Base receipt" if verify else "collector ledger (UNVERIFIED)",
        })
    passports.sort(key=lambda p: (-p.get("calls_verified", p.get("calls_logged", 0)), p["payer"]))

    repeat_buyers = sum(1 for p in passports if p["repeat_status"] == "REPEAT_BUYER")
    calls_per_payer = round(
        sum(p.get("calls_verified", p.get("calls_logged", 0)) for p in passports) / len(passports), 2
    ) if passports else 0.0
    fleet = {
        "external_payers": len(passports),
        "repeat_buyers": repeat_buyers,
        "calls_per_payer": calls_per_payer,
        "max_calls_single_payer": max(
            [p.get("calls_verified", p.get("calls_logged", 0)) for p in passports] or [0]
        ),
        "external_received_usd": round(sum(
            p.get("verified_spend_usd", p.get("logged_spend_usd", 0)) for p in passports
        ), 6),
        "honest_external_earned_usd": 0.0,
        "earned_definition": "external tx with receipt + matching challenge + confirmed delivery; no delivery signal in collector => 0.00",
        "rpc_used": rpc_url,
        "chain_verified": verify and rpc_url is not None,
    }
    for c in crawler_records.values():
        c["services"] = sorted(c["services"])
        c["logged_usd"] = round(c["logged_usd"], 6)
        c["passport_issued"] = False
        c["reason"] = "breadth-crawler dust-scatter: machine discovery, NOT demand"
    return passports, fleet, crawler_records


def main():
    ap = argparse.ArgumentParser(description="RAEN Innovation 55 - Machine-Buyer Repeat Passport")
    ap.add_argument("--out", help="write JSON report to this path")
    ap.add_argument("--payer", help="focus on a single payer address")
    ap.add_argument("--no-verify", action="store_true", help="collector-only (mark UNVERIFIED)")
    ap.add_argument("--no-live", action="store_true", help="use cached ledger file if present")
    args = ap.parse_args()

    try:
        if args.no_live:
            ledger = json.load(open("ledger.json", encoding="utf-8"))
        else:
            ledger = get_json(LEDGER_URL)
            try:
                stats = get_json(STATS_URL)
            except Exception:
                stats = {}
    except Exception as ex:
        print("fetch error:", str(ex)[:120], file=sys.stderr)
        return 1

    txs = ledger.get("transactions", [])
    if not txs:
        print("no ledger transactions", file=sys.stderr)
        return 2

    verify = not args.no_verify
    passports, fleet, crawler_records = analyze(ledger, verify=verify)
    if args.payer:
        focus = args.payer.lower()
        passports = [p for p in passports if p["payer"] == focus]

    report = {
        "tool": VERSION,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "canonical_payto": CANONICAL,
        "chain": "eip155:8453 (Base)",
        "usdc": BASE_USDC,
        "evidence_basis": "on-chain Base receipt" if (verify and fleet.get("rpc_used")) else "collector ledger (UNVERIFIED)",
        "excluded_internal_wallets": sorted(INTERNAL_WALLETS),
        "excluded_crawlers": KNOWN_NON_BUYERS,
        "fleet_kpi": fleet,
        "passports": passports,
        "crawler_exclusions": sorted(crawler_records.values(), key=lambda c: -c["logged_usd"]),
    }
    text = json.dumps(report, indent=2) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print("wrote", args.out)
    print("verdict:", "OK" if fleet["chain_verified"] else "UNVERIFIED",
          "| external_payers", fleet["external_payers"],
          "| repeat_buyers", fleet["repeat_buyers"],
          "| calls/payer", fleet["calls_per_payer"],
          "| honest_external_earned_usd", fleet["honest_external_earned_usd"])
    for p in passports:
        ck = "calls_verified" if "calls_verified" in p else "calls_logged"
        sk = "verified_spend_usd" if "verified_spend_usd" in p else "logged_spend_usd"
        print("  ", p["passport_id"], p["repeat_status"],
              "calls", p[ck], "walls", p["distinct_walls"], "spend", p[sk],
              p["earned_scope"])
    for c in sorted(crawler_records.values(), key=lambda c: -c["logged_usd"]):
        print("   NO PASSPORT", c["payer"][:18], "calls", c["calls"],
              "logged_usd", c["logged_usd"], "-", c["reason"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
