#!/usr/bin/env python3
"""Recipe 34 - broker presence monitor (Tiffany, machine-buyer acquisition).

Zero-cost, read-only, GET-only, stdlib-only. Asks the four public discovery
surfaces where a machine buyer actually looks for a paid API whether a given
seller is listed, buyable and pointing at the canonical payTo:

  1. agent402.tools   - tool index: health, paid tools, payTosByNetwork,
                        routerDispatchEligible (the reciprocal-metering floor)
  2. 402index.io      - service index: exact-host rows, price, HTTP method,
                        x402_payment_valid, domain_verified, pending-review UUIDs
  3. payapi.market    - listing index: provider claim status, payment_verified
  4. CDP Bazaar       - discovery/resources: canonical payTo presence (bounded)

NO signing, NO X-PAYMENT header, NO RPC money calls, NO funds movement,
NO POST to any directory, NO external sends. Every request is an unauthenticated
GET to a public endpoint.

Why: a listing can be present but useless to a machine buyer (Unclaimed
provider, payment_verified=false, pending review, routerDispatchEligible=false,
or a stale/retired payTo). Presence alone is not demand; this tool separates
"listed" from "buyable" and flags payTo DRIFT before a buyer signs anything.

Usage:
  python3 scripts/broker-presence.py --json
  python3 scripts/broker-presence.py --host contract-eye-x402.fly.dev \
      --check-id b82f0aab-b5a2-40aa-a982-dc48bf526d66 --json
  python3 scripts/broker-presence.py --cdp-pages 5

Exit codes: 0 clean, 1 RETIRED/POISON payTo drift (CI hard-block), 2 all
surfaces unreachable. Absence from a broker is a GAP, not a failure: it is an
acquisition opportunity, and claiming a listing is an owner-lane action.
"""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request

CANONICAL = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f"
RETIRED = "0x7861db4efc14a1ed5dd8c96c528a3796560f1393"
AGENTCASH = "0xfbc0eb7811d477e55261d956df39f0046e192240"
ROLES = {"CANONICAL": CANONICAL, "RETIRED": RETIRED, "AGENTCASH": AGENTCASH}
UA = "Mozilla/5.0 (compatible; raen-broker-presence/1.0)"

DEFAULT_HOSTS = [
    "rae-fleet-router.fly.dev",
    "contract-eye-x402.fly.dev",
    "nanobanana-x402.fly.dev",
    "royal-ruby-x402.fly.dev",
    "raen-mcp-gateway.fly.dev",
]


def classify(addr):
    """Full 42-char, case-insensitive role classification (recipe 33 doctrine)."""
    if not isinstance(addr, str) or len(addr) != 42 or not addr.startswith("0x"):
        return "INVALID"
    low = addr.lower()
    for role, known in ROLES.items():
        if low == known.lower():
            return role
    best_d = 99
    for known in ROLES.values():
        d = sum(x != y for x, y in zip(low[2:], known[2:].lower()))
        best_d = min(best_d, d)
    return "POISON_SUSPECT" if best_d <= 2 else "UNKNOWN"


def get(url, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception as exc:
        return {"_error": str(exc)[:160]}


def surface_agent402(host, timeout):
    u = "https://agent402.tools/api/index?seller=" + urllib.parse.quote(host)
    d = get(u, timeout)
    if "_error" in d:
        return {"reachable": False, "error": d["_error"]}
    pay = d.get("payTosByNetwork", {})
    roles = {}
    for net, addrs in pay.items() if isinstance(pay, dict) else []:
        roles[net] = [classify(a) for a in addrs]
    return {
        "reachable": True,
        "toolCount": d.get("toolCount"),
        "paidToolCount": d.get("paidToolCount"),
        "health": d.get("health"),
        "error": d.get("error"),
        "fetchedAt": d.get("fetchedAt"),
        "payTosByNetwork": pay,
        "payToRoles": roles,
        "routerDispatchEligible": _has(d, "routerDispatchEligible", True),
        "unprovenMaxUsd": _find_key(d, "unprovenMaxUsd"),
    }


def _has(obj, key, default=False):
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            r = _has(v, key, default)
            if r is not default:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _has(v, key, default)
            if r is not default:
                return r
    return default


def _find_key(obj, key):
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            r = _find_key(v, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _find_key(v, key)
            if r is not None:
                return r
    return None


def surface_402index(host, timeout, check_ids):
    u = "https://402index.io/api/v1/services?limit=100&q=" + urllib.parse.quote(host)
    d = get(u, timeout)
    if "_error" in d:
        return {"reachable": False, "error": d["_error"]}
    rows = d.get("services", d.get("results", [])) if isinstance(d, dict) else []
    rows = [x for x in rows if isinstance(x, dict)]
    exact = []
    host_l = host.lower()
    for r in rows:
        url = str(r.get("url", r.get("base_url", ""))).lower()
        # exact host-prefix match; the q param is fuzzy and echoes the query
        if host_l in urllib.parse.urlparse(url).netloc.lower():
            exact.append({
                "url": r.get("url", r.get("base_url")),
                "id": r.get("id"),
                "price_usd": r.get("price_usd"),
                "http_method": r.get("http_method"),
                "x402_payment_valid": r.get("x402_payment_valid"),
                "domain_verified": r.get("domain_verified"),
            })
    checked = {}
    for sid in check_ids:
        one = get("https://402index.io/api/v1/services/" + urllib.parse.quote(sid), timeout)
        checked[sid] = {
            "live": "_error" not in one and "error" not in one,
            "detail": one.get("error") if isinstance(one, dict) else None,
        }
    return {"reachable": True, "fuzzy_row_count": len(rows) if isinstance(rows, list) else 0,
            "exact_host_rows": exact, "uuid_checks": checked}


def surface_payapi(host, timeout, max_pages):
    cursor = None
    matches = []
    seen = 0
    for _ in range(max_pages):
        u = "https://payapi.market/api/listings?limit=100" + (("&cursor=" + urllib.parse.quote(cursor)) if cursor else "")
        d = get(u, timeout)
        if "_error" in d:
            return {"reachable": False, "error": d["_error"], "seen": seen}
        res = [x for x in d.get("results", []) if isinstance(x, dict)]
        seen += len(res)
        host_l = host.lower()
        for r in res:
            if host_l in str(r.get("base_url", "")).lower():
                matches.append({
                    "id": r.get("id"),
                    "name": r.get("name"),
                    "provider": r.get("provider"),
                    "payment_verified": r.get("payment_verified"),
                    "price": r.get("price"),
                    "listing_url": r.get("listing_url"),
                })
        cursor = d.get("next_cursor")
        if not d.get("has_more") or not cursor:
            break
        time.sleep(0.1)
    return {"reachable": True, "records_seen": seen, "matches": matches}


def surface_cdp(timeout, pages):
    hits = []
    seen = 0
    for p in range(pages):
        off = p * 200
        d = get("https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources?limit=200&offset=%d" % off, timeout)
        if "_error" in d:
            return {"reachable": False, "error": d["_error"], "items_seen": seen}
        items = d.get("items", [])
        seen += len(items)
        blob = json.dumps(items).lower()
        if CANONICAL.lower() in blob:
            hits.append({"offset": off, "reason": "canonical_payTo"})
        time.sleep(0.1)
    return {"reachable": True, "items_seen": seen, "canonical_payTo_hits": hits,
            "coverage_note": "bounded scan; absence is NOT a full-index absence claim"}


def main():
    ap = argparse.ArgumentParser(description="Read-only machine-buyer broker presence monitor")
    ap.add_argument("--host", action="append", default=[], help="seller host (repeatable)")
    ap.add_argument("--check-id", action="append", default=[], dest="check_ids",
                    help="402index UUID to GET-check")
    ap.add_argument("--cdp-pages", type=int, default=10)
    ap.add_argument("--payapi-pages", type=int, default=40)
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    hosts = args.host or DEFAULT_HOSTS
    report = {
        "tool": "raen-broker-presence/1.0",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "canonical": CANONICAL,
        "read_only": True,
        "hosts": {},
        "cdp": surface_cdp(args.timeout, max(0, min(args.cdp_pages, 50))),
        "findings": [],
    }
    drift = []
    for h in hosts:
        a = surface_agent402(h, args.timeout)
        b = surface_402index(h, args.timeout, args.check_ids)
        p = surface_payapi(h, args.timeout, max(1, min(args.payapi_pages, 50)))
        report["hosts"][h] = {"agent402": a, "bazaar402index": b, "payapi": p}
        # drift detection on every payTo seen in agent402
        for net, addrs in (a.get("payToRoles") or {}).items():
            for role in addrs:
                if role in ("RETIRED", "POISON_SUSPECT"):
                    drift.append({"host": h, "surface": "agent402", "network": net, "role": role})
        for row in b.get("exact_host_rows", []):
            if classify(str(row.get("url", ""))) in ("RETIRED", "POISON_SUSPECT"):
                drift.append({"host": h, "surface": "402index", "url": row.get("url")})
        a_ok = bool(a.get("reachable") and (a.get("toolCount") or 0) > 0)
        b_ok = bool(b.get("exact_host_rows"))
        p_rows = p.get("matches", [])
        p_claimed = any(x.get("provider") not in (None, "Unclaimed") for x in p_rows)
        if not (a.get("reachable") or b.get("reachable") or p.get("reachable")):
            kind = "SURFACES_UNREACHABLE"
        elif a_ok and b_ok and p_claimed:
            kind = "ALL_PRESENT_CLAIMED"
        elif a_ok and b_ok:
            kind = "LISTED_BOTH_PAYAPI_UNCLAIMED" if p_rows else "LISTED_BOTH"
        elif a_ok:
            kind = "AGENT402_ONLY"
        elif b_ok:
            kind = "BAZAAR_ONLY"
        else:
            kind = "ABSENT_ALL"
        report["findings"].append({
            "host": h, "kind": kind,
            "agent402": a_ok, "bazaar402index": b_ok,
            "payapi_listings": len(p_rows), "payapi_claimed": p_claimed,
        })

    if drift:
        report["verdict"] = "DRIFT"
        report["drift"] = drift
    else:
        report["verdict"] = "CLEAN"
        report["drift"] = []

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("broker-presence verdict:", report["verdict"], "| cdp seen:", report["cdp"].get("items_seen"))
        for h, s in report["hosts"].items():
            a, b, p = s["agent402"], s["bazaar402index"], s["payapi"]
            print(" -", h, "| agent402 tools:", a.get("toolCount"), "paid:", a.get("paidToolCount"),
                  "| dispatchEligible:", a.get("routerDispatchEligible"),
                  "| 402index exact:", len(b.get("exact_host_rows", [])),
                  "| payapi:", [m.get("provider") for m in p.get("matches", [])])
        for f in report["findings"]:
            print("   finding:", f)
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main())
