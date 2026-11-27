#!/usr/bin/env python3
"""acquisition-funnel.py — machine-buyer acquisition funnel auditor (read-only).

The 52 prior tools grade a single face of the fleet (wall, docs, payer, ledger,
chain). None answers the acquisition question end to end: for each kept-live
paid wall, can an autonomous agent DISCOVER it, UNDERSTAND it, PAY it, and
come back (repeat-buyer KPI)? This tool fuses four evidence stages per wall and
names the single biggest acquisition blocker.

Read-only and stdlib-only. Sends only unauthenticated GETs and unpaid POSTs that
produce a 402 challenge. NEVER signs, NEVER builds X-PAYMENT, NEVER moves money,
NEVER sends external comms, NEVER deploys, NEVER touches a frozen app.

Stages (truth order: live challenge > manifest > catalog > collector ledger):
  DISCOVER   wall appears in the live rae-fleet-router /catalog.json
  UNDERSTAND /.well-known/x402.json is canonical and declares request fields
  PAY        live unpaid 402 decodes: exact / eip155:8453 / canonical payTo
  REPEAT     collector ledger shows a genuine external settle for this service
             (internal wallets and behaviour-discovered breadth-crawlers excluded)

Usage:
  python scripts/acquisition-funnel.py
  python scripts/acquisition-funnel.py --out registry/acquisition-funnel.json
"""
import argparse, base64, json, sys, urllib.error, urllib.request
from datetime import datetime, timezone

CANON = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f"
NETWORK = "eip155:8453"
USER_AGENT = "Mozilla/5.0 (compatible; RAEN-acquisition-funnel/1.0; +https://github.com/bshelby88/x402-cookbook)"
TIMEOUT = 18
CATALOG_URL = "https://rae-fleet-router.fly.dev/catalog.json"
LEDGER_URL = "https://settlement-collector.fly.dev/ledger.json"

# Full-form addresses only — shorthand caused a false census on 2026-11-21.
INTERNAL = {
    "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f".lower(),   # canonical
    "0x7861db4efc14a1ed5dd8c96c528a3796560f1393".lower(),   # retired
    "0xfbc0eb7811d477e55261d956df39f0046e192240".lower(),   # AgentCash
}
# Behaviour-discovered breadth-class crawlers (tools 51/52) — NOT demand.
BREADTH_CRAWLERS = {
    "0xc9c7b38c0942914fc8ea12063bc92dcd3b581670".lower(),
    "0x171d8021b98c53dcbb3c9c30cbbbeb1b01850fca".lower(),
}

WALLS = [
    {"service": "royal-ruby", "host": "royal-ruby-x402.fly.dev", "path": "/api/law-lookup", "body": {}},
    {"service": "contract-eye", "host": "contract-eye-x402.fly.dev", "path": "/api/analyze-contract", "body": {}},
    {"service": "nanobanana", "host": "nanobanana-x402.fly.dev", "path": "/api/generate-image", "body": {"prompt": "funnel probe"}},
    {"service": "raen-mcp-gateway", "host": "raen-mcp-gateway.fly.dev", "path": "/mcp", "body": {"jsonrpc": "2.0", "method": "tools/call", "id": 1, "params": {}}},
]


def fetch(url, data=None):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers={
        "User-Agent": USER_AGENT, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, dict(r.headers), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8", "replace")
    except Exception as e:
        return None, {}, str(e)


def decode_challenge(headers):
    for k, v in headers.items():
        if k.lower() == "payment-required":
            try:
                return json.loads(base64.b64decode(v + "=" * (-len(v) % 4)))
            except Exception:
                return None
    return None


def stage_discover(catalog_raw):
    return "listed" if catalog_raw and any(w["host"] in catalog_raw for w in WALLS) else None


def host_in_catalog(catalog_raw, host):
    return bool(catalog_raw) and host in catalog_raw


def stage_understand(host):
    code, _, raw = fetch("https://" + host + "/.well-known/x402.json")
    if code != 200:
        return {"ok": False, "reason": "manifest HTTP %s" % code}
    try:
        m = json.loads(raw)
    except Exception:
        return {"ok": False, "reason": "manifest not JSON"}
    s = json.dumps(m)
    canon_ok = CANON.lower() in s.lower()
    # request fields advertised somewhere in the manifest
    has_fields = ("inputSchema" in s or "requestBody" in s or "fields" in s
                  or "schema" in s or "bodySchema" in s)
    return {"ok": bool(canon_ok), "canonical_payto": canon_ok,
            "declares_request_fields": has_fields,
            "reason": "canonical manifest" if canon_ok else "NON-CANONICAL payTo in manifest"}


def stage_pay(w):
    url = "https://" + w["host"] + w["path"]
    code, hdrs, raw = fetch(url, w["body"])
    obj = decode_challenge(hdrs)
    if code not in (402, None) or not obj:
        return {"ok": False, "reason": "no 402 challenge (HTTP %s)" % code}
    accepts = obj.get("accepts", []) or []
    if not accepts:
        return {"ok": False, "reason": "402 with no accepts[]"}
    a = accepts[0]
    payto = str(a.get("payTo", ""))
    ok = (a.get("scheme") == "exact" and a.get("network") == NETWORK
          and payto.lower() == CANON.lower())
    return {"ok": bool(ok), "scheme": a.get("scheme"), "network": a.get("network"),
            "amount": a.get("amount"), "payTo": payto,
            "reason": "canonical live 402" if ok else "DRIFT in live 402"}


def load_ledger():
    code, _, raw = fetch(LEDGER_URL)
    if code != 200:
        return [], {"error": "ledger HTTP %s" % code}
    try:
        d = json.loads(raw)
        return d.get("transactions", []), d
    except Exception as e:
        return [], {"error": str(e)}


def stage_repeat(txs, service):
    genuine = []
    for t in txs:
        if str(t.get("service", "")).lower() != service.lower():
            continue
        payer = str(t.get("payer", "")).lower()
        if payer in INTERNAL or payer in BREADTH_CRAWLERS or not payer:
            continue
        genuine.append({"payer": payer, "amount_usd": t.get("amount_usd"),
                        "fulfilled": t.get("fulfilled")})
    return {"ok": bool(genuine), "genuine_external_settles": len(genuine),
            "payers": genuine,
            "reason": "genuine external settle(s)" if genuine else "no genuine external payer"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    cat_code, _, cat_raw = fetch(CATALOG_URL)
    catalog_raw = cat_raw if cat_code == 200 else ""
    txs, ledger_top = load_ledger()

    results = []
    for w in WALLS:
        host = w["host"]
        discover = {"ok": host_in_catalog(catalog_raw, host),
                    "reason": "in router catalog" if host_in_catalog(catalog_raw, host)
                              else "ABSENT from router catalog"}
        understand = stage_understand(host)
        pay = stage_pay(w)
        repeat = stage_repeat(txs, w["service"])
        stages = {"DISCOVER": discover, "UNDERSTAND": understand,
                  "PAY": pay, "REPEAT": repeat}
        first_fail = next((k for k, v in stages.items() if not v.get("ok")), None)
        verdict = "READY" if first_fail is None else "BLOCKED_AT_" + first_fail
        results.append({"service": w["service"], "host": host,
                        "stages": stages, "verdict": verdict,
                        "blocker": first_fail})

    # Honest external earned: exclude internal + breadth crawlers from the ledger.
    honest = 0.0
    for t in txs:
        payer = str(t.get("payer", "")).lower()
        if payer in INTERNAL or payer in BREADTH_CRAWLERS or not payer:
            continue
        try:
            honest += float(t.get("amount_usd") or 0)
        except Exception:
            pass

    report = {
        "tool": "acquisition-funnel", "version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "catalog_http": cat_code,
        "ledger_note": ledger_top.get("note"),
        "canonical_payto": CANON, "network": NETWORK,
        "walls": results,
        "walls_ready": sum(1 for r in results if r["verdict"] == "READY"),
        "honest_external_earned_usd": round(honest, 6),
        "read_only": True,
    }
    out = json.dumps(report, indent=2)
    print(out)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
