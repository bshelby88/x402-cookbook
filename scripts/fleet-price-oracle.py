#!/usr/bin/env python3
"""RAEN fleet price oracle — read-only live-402 decoder (Tiffany Innovation #18).

Sends ONE unpaid request per paid wall, base64-decodes the HTTP 402
`payment-required` header, parses the x402 v2 envelope, and emits a
machine-readable price sheet. NEVER signs, NEVER moves funds, NEVER retries
with a payment header. Safe for any agent to run.

Exit: 0 = all decoded walls canonical, 1 = payTo/contract drift detected,
      2 = no wall could be decoded (transport outage, not a trust failure).
"""
import argparse
import base64
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

CANONICAL = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f"
USDC_BASE = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"

# Curated from the cookbook registry + master service list. POST = canonical
# challenge (GET quote handlers on some services omit payment-required).
WALLS = [
    {"service": "royal-ruby", "url": "https://royal-ruby-x402.fly.dev/api/law-lookup",
     "body": {"topic": "FCRA", "statute": "15 U.S.C. 1681a"}},
    {"service": "royal-ruby-ping", "url": "https://royal-ruby-x402.fly.dev/api/ping", "body": None},
    {"service": "contract-eye", "url": "https://contract-eye-x402.fly.dev/api/analyze-contract",
     "body": {"contract_text": "Sample services agreement for risk analysis."}},
    {"service": "nanobanana", "url": "https://nanobanana-x402.fly.dev/api/generate-image",
     "body": {"prompt": "a cyan circle"}},
    {"service": "dispute-forge", "url": "https://dispute-forge-x402.fly.dev/api/dispute-pack",
     "body": {"topic": "FCRA", "violation": "1681i"}},
    {"service": "escrow", "url": "https://escrow-x402.fly.dev/api/create",
     "body": {"amount": 1000}},
    {"service": "dispatch", "url": "https://dispatch-x402.fly.dev/api/route",
     "body": {"intent": "summarize this document"}},
    {"service": "nft-alpha", "url": "https://nft-alpha-x402.fly.dev/api/signals",
     "body": {"collection": "base"}},
    {"service": "mcp-gateway", "url": "https://raen-mcp-gateway.fly.dev/mcp",
     "body": {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
              "params": {"name": "health", "arguments": {}}}},
]


def decode_header(raw):
    if not raw:
        return None
    try:
        pad = "=" * (-len(raw) % 4)
        return json.loads(base64.urlsafe_b64decode(raw + pad).decode("utf-8"))
    except Exception:
        try:
            return json.loads(base64.b64decode(raw + "==").decode("utf-8"))
        except Exception:
            return None


def probe(wall):
    data = json.dumps(wall["body"]).encode() if wall["body"] is not None else b""
    req = urllib.request.Request(
        wall["url"], data=data if data else None, method="POST" if data else "GET",
        headers={"Content-Type": "application/json", "User-Agent": "raen-price-oracle/1.0"},
    )
    rec = {"service": wall["service"], "url": wall["url"], "http": None,
           "envelope": False, "amount_atomic": None, "amount_usd": None,
           "network": None, "scheme": None, "payto": None,
           "payto_canonical": False, "note": ""}
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            rec["http"] = resp.status
            rec["note"] = "unexpected 2xx (route may be free/frozen)"
            return rec
    except urllib.error.HTTPError as e:
        rec["http"] = e.code
        headers = e.headers
    except Exception as e:
        rec["note"] = "transport: " + str(e)[:80]
        return rec
    if rec["http"] != 402:
        rec["note"] = "no 402 challenge (status %s)" % rec["http"]
        return rec
    env = decode_header(headers.get("payment-required") or headers.get("Payment-Required"))
    if not env:
        rec["note"] = "402 without decodable payment-required header"
        return rec
    accepts = env.get("accepts") or []
    if not accepts:
        rec["note"] = "envelope has no accepts[]"
        return rec
    a = accepts[0]
    rec["envelope"] = True
    amt = a.get("amount")
    try:
        amt_i = int(amt) if amt is not None else None
    except (ValueError, TypeError):
        amt_i = None
    rec["amount_atomic"] = amt_i
    if amt_i is not None:
        rec["amount_usd"] = round(amt_i / 1_000_000, 6)
    rec["network"] = a.get("network")
    rec["scheme"] = a.get("scheme")
    payto = a.get("payTo") or (a.get("extra") or {}).get("payTo")
    rec["payto"] = payto
    rec["payto_canonical"] = bool(payto) and str(payto).lower() == CANONICAL.lower()
    bad = []
    if not rec["payto_canonical"]:
        bad.append("payTo not canonical")
    if rec["scheme"] != "exact":
        bad.append("scheme != exact")
    if rec["network"] != "eip155:8453":
        bad.append("network != eip155:8453")
    if amt_i is None or amt_i <= 0:
        bad.append("bad amount")
    rec["note"] = "OK" if not bad else "; ".join(bad)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="write JSON sheet to this path")
    args = ap.parse_args()
    results = [probe(w) for w in WALLS]
    decoded = [r for r in results if r["envelope"]]
    drift = [r for r in decoded if not r["payto_canonical"] or r["scheme"] != "exact"
             or r["network"] != "eip155:8453"]
    sheet = {
        "tool": "raen-fleet-price-oracle",
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "live HTTP 402 payment-required header, base64-decoded (x402 v2)",
        "canonical_payto": CANONICAL,
        "settlement_asset": "USDC " + USDC_BASE + " on Base (eip155:8453)",
        "read_only": True,
        "walls_probed": len(results),
        "walls_decoded": len(decoded),
        "drift_count": len(drift),
        "walls": results,
    }
    text = json.dumps(sheet, indent=2)
    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    if not decoded:
        return 2
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main())
