#!/usr/bin/env python3
"""Innovation 46 - RAEN Budget Guard (spend-cap planner for autonomous buyers).

The cookbook's 45 tools grade and drive the buyer journey, but none gives an
autonomous agent a SPEND POLICY. Agents operate under a budget; before they sign
anything they need a deterministic answer to "can I afford this basket of calls
within my cap?" -- priced ONLY from live 402 challenges, never a hand-typed table.

This tool:
  * probes each kept-live paid wall with ONE unpaid POST (no X-PAYMENT, no signing),
  * base64-decodes the x402 v2 payment-required header for price / payTo / network,
  * enforces the FULL 42-char canonical payTo guard (poison-address safe),
  * takes a planned basket (--call wall=N) and a USDC budget (--budget),
  * emits go/no-go, the per-wall cost, the affordability frontier, and a
    copy-ready agent budget policy -- all from live facts.

NEVER signs, NEVER sends X-PAYMENT, NEVER makes an RPC money call, NEVER moves
funds, NEVER uses a key, NEVER deploys. BURN FREEZE respected (kept-live walls only).

Exit 0 = all walls canonical (verdict AFFORDABLE or OVER_BUDGET both exit 0 --
         affordability is a buyer decision, not a trust failure).
Exit 1 = a canonical break (drift).  Exit 2 = no wall reachable.
"""
import argparse
import base64
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

VERSION = "1.0"
CANON = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f"
BASE_NETWORK = "eip155:8453"
ATOMIC = 1_000_000

# Kept-live walls only -- exact unpaid POST probes used by Innovations 42-45.
WALLS = [
    {"name": "royal-ruby", "base": "https://royal-ruby-x402.fly.dev",
     "route": "/api/law-lookup", "body": {"query": "x402 budget-guard probe"}},
    {"name": "contract-eye", "base": "https://contract-eye-x402.fly.dev",
     "route": "/api/analyze-contract", "body": {"text": "x402 budget-guard probe"}},
    {"name": "nanobanana", "base": "https://nanobanana-x402.fly.dev",
     "route": "/api/generate-image", "body": {"prompt": "x402 budget-guard probe"}},
    {"name": "raen-mcp-gateway", "base": "https://raen-mcp-gateway.fly.dev",
     "route": "/mcp", "body": {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                               "params": {"name": "raen_law_lookup",
                                          "arguments": {"topic": "x402 budget-guard probe"}}}},
]
UA = {"User-Agent": "Mozilla/5.0 (compatible; RAEN-budget-guard/1.0)",
      "Accept": "application/json"}


def http(method, url, body=None, timeout=20):
    hdr = dict(UA)
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        hdr["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=hdr, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers.items())
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers.items())
    except Exception:
        return None, {}


def canon(addr):
    return isinstance(addr, str) and addr.lower() == CANON.lower()


def decode_challenge(headers):
    raw = None
    for k, v in headers.items():
        if k.lower() in ("payment-required", "x-payment-required"):
            raw = v
            break
    if not raw:
        return None, "no payment-required header"
    if "," in raw and not raw.lstrip().startswith("{"):
        raw = raw.split(",", 1)[1].strip()
    if "..." in raw:
        return None, "header truncated"
    try:
        obj = json.loads(base64.b64decode(raw + "=" * (-len(raw) % 4)).decode("utf-8"))
    except Exception as e:
        return None, "header decode failed: %s" % type(e).__name__
    accepts = obj.get("accepts") or []
    if not isinstance(accepts, list) or not accepts:
        return None, "empty accepts[]"
    return obj, None


def probe(wall):
    url = wall["base"] + wall["route"]
    status, headers = http("POST", url, wall.get("body"))
    out = {"name": wall["name"], "url": url, "http_status": status,
           "price_usdc": None, "price_atomic": None, "payto": None,
           "canonical": False, "scheme": None, "network": None, "note": ""}
    if status != 402:
        out["note"] = "expected 402, got %s" % status
        return out
    obj, err = decode_challenge(headers)
    if obj is None or err:
        out["note"] = err or "undecodable challenge"
        return out
    acc = (obj.get("accepts") or [{}])[0]
    if not isinstance(acc, dict):
        acc = {}
    payto, scheme, net = acc.get("payTo"), acc.get("scheme"), acc.get("network")
    raw_amt = acc.get("amount")
    try:
        amt = int(raw_amt) if raw_amt is not None else None
    except (TypeError, ValueError):
        amt = None
    out.update(payto=payto, scheme=scheme, network=net,
               price_atomic=amt,
               price_usdc=round(amt / ATOMIC, 6) if amt is not None else None,
               canonical=canon(payto))
    bad = []
    if not out["canonical"]:
        bad.append("payTo not canonical")
    if scheme != "exact":
        bad.append("scheme != exact")
    if net != BASE_NETWORK:
        bad.append("network != %s" % BASE_NETWORK)
    if amt is None or amt <= 0:
        bad.append("bad amount")
    out["note"] = "OK" if not bad else "; ".join(bad)
    return out


def money(v):
    return "$%.6f" % v if v is not None else "n/a"


def build_card(snap):
    lines = ["# RAEN Budget Guard - spend plan (%sZ)" % snap["generated_at"][:19].replace("T", " "),
             "",
             "- Budget: **%s USDC** (reserve %d%% -> usable **%s USDC**)" % (
                 money(snap["budget_usdc"]), snap["reserve_pct"], money(snap["usable_budget_usdc"])),
             "- Verdict: **%s** | planned total **%s** | drift %d/%d" % (
                 snap["verdict"], money(snap["total_planned_cost_usdc"]),
                 snap["drift_count"], snap["walls_priced"]),
             "- Prices are LIVE-READ from unpaid 402 challenges; the live 402 is authoritative.",
             "- Canonical payTo (full 42-char): `%s`" % CANON,
             "",
             "| wall | live price | plan | planned cost | max calls in usable budget |",
             "|---|---|---|---|---|"]
    for w in snap["walls"]:
        lines.append("| %s | %s | %d | %s | %d |" % (
            w["name"], money(w.get("price_usdc")), w.get("planned_calls", 0),
            money(w.get("planned_cost_usdc")), w.get("max_calls_in_budget", 0)))
    lines += ["", "## Copy-ready agent budget policy", "```json",
              json.dumps(snap["agent_policy"], indent=2), "```",
              "",
              "This tool never signs or sends X-PAYMENT. It only reads live 402 "
              "challenges. Signing is the buyer's own wallet step.",
              ""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="RAEN Budget Guard - live-priced spend cap")
    ap.add_argument("--budget", type=float, default=0.05, help="total USDC budget (default 0.05)")
    ap.add_argument("--reserve-pct", type=int, default=10,
                    help="percent of budget reserved for retries/claims (default 10)")
    ap.add_argument("--call", action="append", default=[], metavar="WALL=N",
                    help="planned calls for a wall, repeatable (default: 1 each)")
    ap.add_argument("--out-json", help="write JSON snapshot here")
    ap.add_argument("--out-md", help="write buyer card here")
    args = ap.parse_args()

    plan = {}
    for c in args.call:
        if "=" not in c:
            continue
        name, n = c.split("=", 1)
        try:
            plan[name.strip()] = max(0, int(n))
        except ValueError:
            pass

    probes = [probe(w) for w in WALLS]
    priced = [p for p in probes if p["price_usdc"] is not None and p["canonical"]]
    drift = [p for p in probes if p["price_usdc"] is not None and not p["canonical"]]

    usable = round(args.budget * (1 - args.reserve_pct / 100.0), 6)
    total = 0.0
    for p in probes:
        n = plan.get(p["name"], 1)  # default basket: one call per wall
        p["planned_calls"] = n
        p["planned_cost_usdc"] = round((p["price_usdc"] or 0) * n, 6) if p["price_usdc"] is not None else None
        if p["planned_cost_usdc"] is not None:
            total += p["planned_cost_usdc"]
        p["max_calls_in_budget"] = (int(usable // p["price_usdc"])
                                    if p["price_usdc"] and p["price_usdc"] > 0 else 0)
    total = round(total, 6)

    if drift:
        verdict = "DRIFT"
    elif not priced:
        verdict = "NO_DATA"
    elif total <= usable:
        verdict = "AFFORDABLE"
    else:
        verdict = "OVER_BUDGET"

    policy = {
        "currency": "USDC", "network": BASE_NETWORK,
        "payTo_allowlist": [CANON],
        "budget_usdc": args.budget, "usable_usdc": usable,
        "reserve_pct": args.reserve_pct,
        "max_per_call_usdc": {p["name"]: p["price_usdc"] for p in priced},
        "require_canonical_payto": True,
        "on_challenge_drift": "ABSTAIN",
        "signing": "buyer-supplied wallet only",
    }
    snap = {
        "tool": "raen-budget-guard", "version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "live HTTP 402 payment-required header, base64-decoded (x402 v2); unpaid POST only",
        "canonical_payto": CANON, "settlement": "USDC on Base (%s)" % BASE_NETWORK,
        "read_only": True, "no_signing": True, "no_funds_moved": True,
        "budget_usdc": args.budget, "reserve_pct": args.reserve_pct,
        "usable_budget_usdc": usable,
        "walls_probed": len(probes), "walls_priced": len(priced),
        "drift_count": len(drift), "total_planned_cost_usdc": total,
        "verdict": verdict, "walls": probes, "agent_policy": policy,
    }
    text = json.dumps(snap, indent=2)
    print(text)
    if args.out_json:
        with open(args.out_json, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    if args.out_md:
        with open(args.out_md, "w", encoding="utf-8") as f:
            f.write(build_card(snap))
    if drift:
        return 1
    if not priced:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
