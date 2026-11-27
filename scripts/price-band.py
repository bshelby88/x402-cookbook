#!/usr/bin/env python3
"""RAEN Innovation 61 - Machine-Buyer Price-Band Conformance Auditor.

The owner's MAIN OBJECTIVE is to get autonomous agents to our platforms to
create revenue, and new challenges must be compared to ACQUIRED DATA before
acting. The consolidated world audit (Library artifact
operations/MEMORY-AND-WORLD-REVENUE-AUDIT-2026-11-26) established, from
88,788 Bazaar resources and dollar-verified earners, that the ONLY proven
machine-buyer winners sell per-call consumables in the machine band:
  p25/median/p75 = $0.003 / $0.003 / $0.005; winner band $0.003-$0.01.
Per call, an autonomous agent has a micro-budget; a wall priced in the
"dead zone" (>$0.01, below human willingness-to-pay) is a silent lost sale.

This tool is READ-ONLY and stdlib-only. For each kept-live paid wall it
probes the paid route with an UNPAID body (no X-PAYMENT), decodes the live
402 challenge, and grades accepts[0].amount against the data-derived band.
It never signs, never attaches a payment header, never pays, never moves
money, and never changes a price (pricing is owner-gated).

Usage:
  python3 scripts/price-band.py
  python3 scripts/price-band.py --out registry/price-band.json
  python3 scripts/price-band.py --check    # exit 1 ONLY on hard gate defects

Exit: 0 = clean, 1 = gate defect (noncanonical/no 402/unreachable), 2 = fetch error.
Band drift (below/above band) is a WARN + owner handoff, NEVER a --check failure.
"""
import argparse, base64, json, sys, urllib.error, urllib.request

CANON = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f".lower()
# Data-derived from the consolidated audit (see docstring). Base units, 6dp.
BAND_LO = 3000   # $0.003  proven p25 / winner floor
BAND_HI = 10000  # $0.010  proven winner ceiling
PROVEN_MEDIAN = 5000  # $0.005 p75 / median seen in real repeat buyers
USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
UA = {"User-Agent": "RAEN-PriceBand-Auditor/1.0 (acquired-data conformance)",
      "Accept": "application/json"}
TIMEOUT = 25

# name, base, paid route, method, unpaid body
TARGETS = [
    {"name": "royal-ruby", "base": "https://royal-ruby-x402.fly.dev",
     "route": "/api/law-lookup", "method": "POST", "body": {"topic": "price-band probe"}},
    {"name": "contract-eye", "base": "https://contract-eye-x402.fly.dev",
     "route": "/api/analyze-contract", "method": "POST", "body": {"text": "price-band probe"}},
    {"name": "nanobanana", "base": "https://nanobanana-x402.fly.dev",
     "route": "/api/generate-image", "method": "POST", "body": {"prompt": "price-band probe"}},
    {"name": "gateway:law", "base": "https://raen-mcp-gateway.fly.dev", "route": "/mcp", "method": "POST",
     "body": {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
              "params": {"name": "raen_law_lookup", "arguments": {"topic": "price-band probe"}}}},
    {"name": "gateway:ticker", "base": "https://raen-mcp-gateway.fly.dev", "route": "/mcp", "method": "POST",
     "body": {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
              "params": {"name": "raen_ticker_analysis", "arguments": {"topic": "price-band probe"}}}},
    {"name": "gateway:dispute_letter", "base": "https://raen-mcp-gateway.fly.dev", "route": "/mcp", "method": "POST",
     "body": {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
              "params": {"name": "raen_dispute_letter", "arguments": {"topic": "price-band probe"}}}},
    {"name": "gateway:image", "base": "https://raen-mcp-gateway.fly.dev", "route": "/mcp", "method": "POST",
     "body": {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
              "params": {"name": "raen_image_generate", "arguments": {"prompt": "price-band probe"}}}},
    {"name": "gateway:contract", "base": "https://raen-mcp-gateway.fly.dev", "route": "/mcp", "method": "POST",
     "body": {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
              "params": {"name": "raen_contract_analysis", "arguments": {"text": "price-band probe"}}}},
]


def fetch(url, method, body):
    data = json.dumps(body).encode("utf-8")
    hdr = dict(UA); hdr["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=hdr, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, dict(r.headers), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, {}, "ERR:" + str(e)[:120]


def decode_challenge(headers, body):
    for key, val in headers.items():
        if key.lower() in ("payment-required", "x-payment-required"):
            raw = val.strip()
            try:
                return json.loads(base64.b64decode(raw + "=" * (-len(raw) % 4)).decode())
            except Exception:
                return None
    try:
        cand = json.loads(body.strip())
        if any(k in cand for k in ("accepts", "payTo", "x402Version")):
            return cand
    except Exception:
        pass
    return None


def grade(t):
    url = t["base"] + t["route"]
    code, headers, body = fetch(url, t["method"], t["body"])
    rec = {"name": t["name"], "url": url, "http": code}
    if code == 0:
        rec.update(verdict="UNREACHABLE", amount_base=None, amount_usd=None, note=body); return rec
    chal = decode_challenge(headers, body)
    if code != 402 or not chal or not isinstance(chal.get("accepts"), list) or not chal["accepts"]:
        rec.update(verdict="NO_402", amount_base=None, amount_usd=None,
                   note="http=%s no decodable accepts[]" % code); return rec
    a = chal["accepts"][0]
    payto = str(a.get("payTo", "")).lower()
    net = str(a.get("network", "")).lower()
    scheme = str(a.get("scheme", "")).lower()
    asset = str(a.get("asset", a.get("token", ""))).lower()
    try:
        amt = int(a.get("amount", a.get("maxAmountRequired", -1)))
    except Exception:
        amt = -1
    rec.update(payto_canonical=(payto == CANON), network=net, scheme=scheme,
               asset=asset, amount_base=amt if amt >= 0 else None,
               amount_usd=round(amt / 1e6, 6) if amt >= 0 else None)
    if payto != CANON:
        rec.update(verdict="NONCANON", note="payTo not canonical" + (" (RETIRED!)" if payto == "0x7861db4efc14a1ed5dd8c96c528a3796560f1393" else "")); return rec
    if net != "eip155:8453" or scheme != "exact":
        rec.update(verdict="GATE_DRIFT", note="network/scheme drift"); return rec
    if amt < 0:
        rec.update(verdict="NO_402", note="no amount"); return rec
    if amt < BAND_LO:
        rec.update(verdict="BELOW_BAND", note="below proven winner floor $0.003 (owner-gated WARN)")
    elif amt > BAND_HI:
        rec.update(verdict="ABOVE_BAND", note="above winner ceiling $0.01, dead-zone risk (owner-gated WARN)")
    else:
        rec.update(verdict="IN_BAND", note="within data-derived winner band $0.003-$0.01")
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    results = [grade(t) for t in TARGETS]
    in_band = sum(1 for r in results if r["verdict"] == "IN_BAND")
    below = [r["name"] + " $" + str(r["amount_usd"]) for r in results if r["verdict"] == "BELOW_BAND"]
    above = [r["name"] + " $" + str(r["amount_usd"]) for r in results if r["verdict"] == "ABOVE_BAND"]
    hard = [r for r in results if r["verdict"] in ("NONCANON", "GATE_DRIFT", "NO_402", "UNREACHABLE")]
    doc = {"tool": "price-band", "version": 1,
           "band_usd": {"lo": BAND_LO / 1e6, "hi": BAND_HI / 1e6, "proven_median": PROVEN_MEDIAN / 1e6,
                        "source": "consolidated world audit 2026-11-26 (p25/median/p75=$0.003/$0.003/$0.005)"},
           "usdc_base": USDC_BASE, "canonical_payto": CANON,
           "summary": {"probed": len(results), "in_band": in_band, "below_band": below,
                       "above_band": above, "hard_defects": len(hard)},
           "results": results}
    text = json.dumps(doc, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    for r in results:
        print("%-22s %-12s $%s  %s" % (r["name"], r["verdict"], r.get("amount_usd"), r.get("note", "")))
    print("SUMMARY: %d/%d in band; below=%s; above=%s; hard_defects=%d" %
          (in_band, len(results), below, above, len(hard)))
    if args.check:
        sys.exit(1 if hard else 0)
    return 0


if __name__ == "__main__":
    main()
