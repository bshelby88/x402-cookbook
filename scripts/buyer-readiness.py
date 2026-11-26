#!/usr/bin/env python3
"""Innovation 43 - Machine-Buyer Readiness Scorecard (stdlib, read-only).

A single go/no-go NUMBER per kept-live wall: "can an autonomous agent actually
complete a first purchase here?" Every other cookbook tool grades ONE stage of
the buyer journey (discovery, catalog, challenge shape, trust, receipt). This one
walks the whole funnel for each wall and emits one machine-readable scorecard plus
a buyer-facing "where to spend first" quickstart table.

Read-only, stdlib-only. Unpaid probes only. NO signing, NO X-PAYMENT header,
NO RPC money calls, NO funds movement, NO external sends, NO directory POSTs,
NO deploys, NO secrets. BURN FREEZE respected: only kept-live walls are probed.

Score (0-100), from LIVE reads only:
  challenge 40 - unpaid POST to the paid route returns a decodable x402 v2 402
                 with scheme=exact, network=eip155:8453, full canonical payTo,
                 integer amount>0. This is the paid-path break: CI fails HERE only.
  manifest  20 - /.well-known/x402.json has a priced accept block for the route
                 whose scheme/network/payTo are canonical.
  discovery 20 - /llms.txt is 200 and names the full canonical payTo.
  trust     10 - Lumi trust check returns a record (verdict != no_data/error).
  price     10 - the manifest accept block carries an explicit price.

Grade: >=80 READY, 50-79 PARTIAL, <50 NOT_READY.
Exit 0 = no CANONICAL_BREAK on any wall; 1 = a wall's paid challenge is broken;
2 = no wall reachable at all. WARNs (missing price/llms/trust) never fail CI.

Usage:
  python3 scripts/buyer-readiness.py
  python3 scripts/buyer-readiness.py --out-json registry/buyer-readiness.json \
      --out-md registry/buyer-readiness.md
"""

import argparse
import base64
import datetime
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

VERSION = "buyer-readiness/1.0"
CANON = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f"
RETIRED = "0x7861db4efc14a1ed5dd8c96c528a3796560f1393"
AGENTCASH = "0xfbc0eb7811d477e55261d956df39f0046e192240"
BASE_NETWORK = "eip155:8453"
USDC_ATOMIC_PER_USD = 1_000_000
LUMI = "https://api.lumitrades.io/v1/trust/check"
UA = {"User-Agent": "Mozilla/5.0 (compatible; RAEN-buyer-readiness/1.0)",
      "Accept": "application/json"}

# Proven, canonical paid probes (same endpoints as the conformance doctor).
WALLS = [
    {"name": "royal-ruby", "base": "https://royal-ruby-x402.fly.dev",
     "route": "/api/law-lookup", "body": {"query": "x402 readiness probe"}},
    {"name": "contract-eye", "base": "https://contract-eye-x402.fly.dev",
     "route": "/api/analyze-contract", "body": {"text": "x402 readiness probe"}},
    {"name": "nanobanana", "base": "https://nanobanana-x402.fly.dev",
     "route": "/api/generate-image", "body": {"prompt": "x402 readiness probe"}},
    {"name": "raen-mcp-gateway", "base": "https://raen-mcp-gateway.fly.dev",
     "route": "/mcp",
     "body": {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
              "params": {"name": "raen_law_lookup",
                         "arguments": {"topic": "x402 readiness probe"}}}},
]


def http(method, url, body=None, headers=None, timeout=20):
    """Return (status, headers_dict, text). Never raises on HTTP/network errors."""
    hdr = dict(headers or {})
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        hdr.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=hdr, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers.items()), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers.items()), e.read().decode("utf-8", "replace")
    except Exception as e:
        return None, {}, "error: %s" % type(e).__name__


def canon(addr):
    """Full 42-char, case-insensitive compare - homoglyph-safe, never a substring."""
    return isinstance(addr, str) and addr.lower() == CANON.lower()


def decode_challenge(headers):
    """Return (accept, error) from a payment-required header."""
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
    return {"x402Version": obj.get("x402Version"), "accepts": accepts}, None


def probe_challenge(wall):
    """Unpaid POST to the paid route -> challenge grade. No X-PAYMENT, ever."""
    url = wall["base"] + wall["route"]
    status, headers, text = http("POST", url, wall.get("body"))
    out = {"http_status": status}
    if status != 402:
        out.update(pass_=False, detail="expected 402, got %s" % status,
                   amount_usd=None, payTo=None)
        return out
    dec, err = decode_challenge(headers)
    if dec is None or err:
        out.update(pass_=False, detail=err or "undecodable challenge",
                   amount_usd=None, payTo=None)
        return out
    accepts = dec.get("accepts") or []
    first = accepts[0] if accepts and isinstance(accepts[0], dict) else {}
    acc = first
    payto, scheme, net = acc.get("payTo"), acc.get("scheme"), acc.get("network")
    amount = acc.get("amount")
    try:
        amt = int(amount) if amount is not None else None
    except (TypeError, ValueError):
        amt = None
    checks = {
        "v2": dec.get("x402Version") == 2,
        "scheme": scheme == "exact",
        "network": net == BASE_NETWORK,
        "payTo": canon(payto),
        "amount": amt is not None and amt > 0,
    }
    failed = [k for k, ok in checks.items() if not ok]
    out.update(pass_=not failed, checks=checks, payTo=payto, network=net,
               scheme=scheme, amount_atomic=amt,
               amount_usd=(round(amt / USDC_ATOMIC_PER_USD, 6) if amt else None),
               detail=("canonical" if not failed else "failed: " + ",".join(failed)))
    return out


def probe_manifest(wall):
    status, _, text = http("GET", wall["base"] + "/.well-known/x402.json")
    out = {"http_status": status, "canonical": False, "has_price": False}
    if status != 200:
        out["detail"] = "manifest HTTP %s" % status
        return out
    try:
        doc = json.loads(text)
    except Exception:
        out["detail"] = "manifest not JSON"
        return out
    for res in (doc.get("resources") or doc.get("endpoints") or []):
        if not isinstance(res, dict) or res.get("path") != wall["route"]:
            continue
        acc = res.get("accepts")
        if not isinstance(acc, dict):
            continue
        price = acc.get("price")
        out["has_price"] = price is not None
        out["price"] = price
        out["canonical"] = (acc.get("scheme") == "exact"
                            and acc.get("network") == BASE_NETWORK
                            and canon(acc.get("payTo")))
        out["detail"] = ("canonical" if out["canonical"] else "noncanonical accept block")
        return out
    out["detail"] = "no priced accept block for route"
    return out


def probe_discovery(wall):
    status, _, text = http("GET", wall["base"] + "/llms.txt")
    out = {"http_status": status, "canonical": False}
    if status == 200:
        out["canonical"] = bool(re.search(re.escape(CANON), text, re.I))
        out["detail"] = "canonical payTo present" if out["canonical"] else "canonical payTo absent"
    else:
        out["detail"] = "llms.txt HTTP %s" % status
    return out


def probe_trust(wall):
    q = LUMI + "?" + urllib.parse.urlencode({"url": wall["base"]})
    status, _, text = http("GET", q, headers=UA)
    out = {"http_status": status, "has_record": False}
    if status != 200:
        out["detail"] = "Lumi HTTP %s" % status
        return out
    try:
        doc = json.loads(text)
    except Exception:
        out["detail"] = "Lumi not JSON"
        return out
    blob = json.dumps(doc).lower()
    verdict = doc.get("verdict") or (doc.get("data") or {}).get("verdict")
    out["verdict"] = verdict
    out["has_record"] = (verdict not in (None, "no_data", "error", "unknown")
                         and "no_data" not in blob[:200])
    out["detail"] = ("record: %s" % verdict) if out["has_record"] else "no trust record"
    return out


def score_wall(wall):
    ch = probe_challenge(wall)
    mf = probe_manifest(wall)
    dc = probe_discovery(wall)
    tr = probe_trust(wall)
    pts = (40 if ch["pass_"] else 0) + (20 if mf["canonical"] else 0) \
        + (20 if dc["canonical"] else 0) + (10 if tr["has_record"] else 0) \
        + (10 if mf["has_price"] else 0)
    grade = "READY" if pts >= 80 else ("PARTIAL" if pts >= 50 else "NOT_READY")
    warns = []
    if not mf["has_price"]:
        warns.append("manifest price missing (live 402 authoritative)")
    if not dc["canonical"]:
        warns.append("llms.txt missing canonical payTo: " + dc["detail"])
    if not tr["has_record"]:
        warns.append("no independent trust record: " + tr["detail"])
    return {
        "name": wall["name"], "url": wall["base"] + wall["route"],
        "score": pts, "grade": grade,
        "paid_path_break": (not ch["pass_"]),
        "components": {"challenge": ch, "manifest": mf, "discovery": dc, "trust": tr},
        "warnings": warns,
    }


def render_md(rows, generated_at):
    L = []
    A = L.append
    A("# Machine-Buyer Readiness Scorecard")
    A("")
    A("Generated %s - %s. Scores come ONLY from live unpaid reads; no funds moved." % (generated_at, VERSION))
    A("")
    A("| Wall | Score | Grade | Live price | Paid path | Warnings |")
    A("|---|---|---|---|---|---|")
    for r in sorted(rows, key=lambda x: -x["score"]):
        ch = r["components"]["challenge"]
        price = ("$%.4f" % ch["amount_usd"]) if ch.get("amount_usd") is not None else "n/a"
        pp = "BREAK" if r["paid_path_break"] else "canonical"
        A("| %s | %d/100 | %s | %s | %s | %s |" % (
            r["name"], r["score"], r["grade"], price, pp,
            "; ".join(r["warnings"]) if r["warnings"] else "none"))
    A("")
    A("**Where to spend first:** highest READY score, verified `canonical` paid path, "
      "then retry with the seller's documented `X-PAYMENT` header. Never pay a wall "
      "whose paid path reads `BREAK` or whose `payTo` is not the full canonical "
      "`%s`." % CANON)
    A("")
    A("A WARN (missing manifest price, absent llms.txt payTo, no trust record) is "
      "buyer friction, not a payment break - the live 402 is always authoritative.")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-json", default=None)
    ap.add_argument("--out-md", default=None)
    a = ap.parse_args()
    rows = []
    for wall in WALLS:
        try:
            rows.append(score_wall(wall))
        except Exception as e:
            rows.append({"name": wall["name"], "score": 0, "grade": "NOT_READY",
                         "paid_path_break": True, "error": type(e).__name__,
                         "warnings": ["probe exception: %s" % type(e).__name__]})
    generated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    breaks = [r for r in rows if r.get("paid_path_break")]
    reachable = [r for r in rows if r.get("components", {}).get("challenge", {}).get("http_status") is not None]
    report = {
        "version": VERSION, "generated_at": generated_at,
        "scope": "kept-live walls only; unpaid POST/GET probes; no signing, no X-PAYMENT, no funds, no deploy",
        "canonical_payTo": CANON,
        "walls": rows,
        "summary": {"total": len(rows), "ready": sum(1 for r in rows if r["grade"] == "READY"),
                    "partial": sum(1 for r in rows if r["grade"] == "PARTIAL"),
                    "not_ready": sum(1 for r in rows if r["grade"] == "NOT_READY"),
                    "paid_path_breaks": len(breaks)},
        "verdict": ("CANONICAL_BREAK" if breaks else ("NO_WALL_REACHABLE" if not reachable else "OK")),
    }
    body = json.dumps(report, indent=2)
    if a.out_json:
        open(a.out_json, "w", encoding="utf-8").write(body + "\n")
    if a.out_md:
        open(a.out_md, "w", encoding="utf-8").write(render_md(rows, generated_at))
    print(json.dumps({"verdict": report["verdict"], "summary": report["summary"],
                      "scores": {r["name"]: r["score"] for r in rows}}, indent=2))
    if breaks:
        return 1
    if not reachable:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
