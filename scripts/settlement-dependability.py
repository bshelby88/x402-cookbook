#!/usr/bin/env python3
"""settlement-dependability.py — machine-buyer settlement dependability grader (read-only).

The first 53 tools grade the wall, the manifest, the schema, the payer wallet, the
collector ledger or the chain. None answers the question an autonomous buyer asks
BEFORE it integrates: "if I pay this wall, will my payment actually settle on-chain,
and how long will it take?" This tool turns the collector's own chain-verified
settlement telemetry into a per-wall dependability grade — a buyer-facing reliability
signal computed from live facts, not a hardcoded claim.

Read-only and stdlib-only. Sends only unauthenticated GETs and unpaid POSTs that
produce a 402 challenge. NEVER signs, NEVER builds X-PAYMENT, NEVER moves money,
NEVER sends external comms, NEVER deploys, NEVER touches a frozen app.

Truth discipline (TRUTH law):
  * Only settled_verified counts as a proven payment path (collector gates on tx hash).
  * High challenges + 0 settles + HIGH failed rate = scanner/probe noise, NOT an
    incident (skill doctrine) -> SCANNER_NOISE, not "payment path broken".
  * High challenges + 0 settles + LOW failed rate = UNPROVEN_NO_PAYER (path untested,
    not broken). A wall with a canonical 402 is not the same as a proven path.
  * Internal test settles prove the PATH works (same rails) but are NEVER revenue.
  * raen-mcp-gateway is a paid wall absent from telemetry -> TELEMETRY_BLIND_SPOT.

Usage:
  python scripts/settlement-dependability.py
  python scripts/settlement-dependability.py --out registry/settlement-dependability.json
"""
import argparse, base64, json, sys, urllib.error, urllib.request
from datetime import datetime, timezone

CANON = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f"
NETWORK = "eip155:8453"
USER_AGENT = "Mozilla/5.0 (compatible; RAEN-settlement-dependability/1.0; +https://github.com/bshelby88/x402-cookbook)"
TIMEOUT = 18
STATS_URL = "https://settlement-collector.fly.dev/stats"
LEDGER_URL = "https://settlement-collector.fly.dev/ledger.json"

# Frozen apps (owner BURN FREEZE) — report telemetry only, never recommend a restart.
FROZEN = {
    "sentry-forge", "vault-pro", "dispatch", "nft-alpha", "escrow",
    "dispute-forge", "tradingagents", "tradingagents-x402",
}
# Kept-live paid walls buyers can actually use (live 402 probe + telemetry grade).
BUYER_WALLS = [
    {"service": "royal-ruby", "host": "royal-ruby-x402.fly.dev", "path": "/api/law-lookup", "body": {}},
    {"service": "contract-eye", "host": "contract-eye-x402.fly.dev", "path": "/api/analyze-contract", "body": {}},
    {"service": "nanobanana", "host": "nanobanana-x402.fly.dev", "path": "/api/generate-image", "body": {"prompt": "dependability probe"}},
    {"service": "raen-mcp-gateway", "host": "raen-mcp-gateway.fly.dev", "path": "/mcp", "body": {"jsonrpc": "2.0", "method": "tools/call", "id": 1, "params": {}}},
]
LATENCY_P95_OK_MS = 15000   # above this a paid call is slow for an autonomous buyer
FAIL_RATE_OK = 0.10          # above this, challenge traffic is dominated by probes/scanners


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


def price_from_challenge(ch):
    """x402 v2: accepts[0].amount is integer atoms; price field is 'amount', NOT maxAmountRequired."""
    if not ch:
        return None
    accepts = ch.get("accepts") or []
    if not accepts:
        return None
    a = accepts[0]
    amt = a.get("amount")
    asset = (a.get("asset") or "").lower()
    atoms = int(amt) if isinstance(amt, (int, str)) and str(amt).isdigit() else None
    return {
        "scheme": a.get("scheme"),
        "network": a.get("network"),
        "amount_atoms": str(amt) if amt is not None else None,
        "price_usd": (atoms / 1_000_000) if atoms is not None and asset.endswith("02913") else None,
        "payTo": a.get("payTo"),
        "canonical_payto": (a.get("payTo") or "").lower() == CANON,
    }


def classify(m):
    """Grade settlement dependability from a telemetry window dict."""
    ch = m.get("challenges") or 0
    settled = m.get("settled") or 0
    verified = m.get("settled_verified") or 0
    failed = m.get("failed") or 0
    p95 = m.get("p95_ms")
    fail_rate = round(failed / ch, 4) if ch else 0.0
    base = {"challenges": ch, "settled": settled, "settled_verified": verified,
            "failed": failed, "fail_rate": fail_rate, "p50_ms": m.get("p50_ms"), "p95_ms": p95}
    if verified > 0:
        fast = (p95 is not None and p95 <= LATENCY_P95_OK_MS)
        clean = fail_rate < FAIL_RATE_OK
        if fast and clean:
            base.update(grade="A", verdict="PROVEN_FAST",
                        reason="chain-verified settles, p95 under threshold, low failure rate")
        else:
            why = []
            if not fast: why.append("p95 above %dms" % LATENCY_P95_OK_MS)
            if not clean: why.append("failure rate above %.0f%%" % (FAIL_RATE_OK * 100))
            base.update(grade="B", verdict="PROVEN_DEGRADED", reason="; ".join(why))
        return base
    # no verified settles
    if ch == 0:
        base.update(grade="N/A", verdict="NO_TRAFFIC", reason="no challenge traffic in window")
    elif fail_rate >= 0.20:
        base.update(grade="D", verdict="SCANNER_NOISE",
                    reason="0 settles with high failure rate -> scanner/probe noise, NOT a payment-path incident")
    else:
        base.update(grade="C", verdict="UNPROVEN_NO_PAYER",
                    reason="0 settles, low failure rate -> payment path untested, not broken")
    return base


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="", help="write full JSON snapshot to this path")
    ap.add_argument("--check", action="store_true", help="exit 1 if any kept-live buyer wall is non-canonical")
    args = ap.parse_args()

    code, _, raw = fetch(STATS_URL)
    if code != 200:
        print("FATAL: collector /stats HTTP %s" % code, file=sys.stderr)
        return 2
    stats = json.loads(raw)
    services = stats.get("services") or {}
    fleet = stats.get("fleet_24h") or {}

    lcode, _, lraw = fetch(LEDGER_URL)
    ledger = json.loads(lraw) if lcode == 200 else {}
    honest_external = float(ledger.get("total_external_usdc") or 0)  # flagged as crawler dust downstream

    # Buyer-facing wall cards: live 402 price/canonical guard + settlement dependability.
    walls = []
    drift = 0
    for w in BUYER_WALLS:
        svc = w["service"]
        pcode, phdr, _ = fetch("https://" + w["host"] + w["path"], w["body"])
        ch = decode_challenge(phdr) if pcode == 402 else None
        price = price_from_challenge(ch)
        tel = services.get(svc)
        d24 = classify(tel.get("24h") or {}) if tel else None
        dall = classify(tel.get("all") or {}) if tel else None
        if tel is None:
            card = {"grade": "?", "verdict": "TELEMETRY_BLIND_SPOT",
                    "reason": "paid wall absent from collector services — no dependability data"}
        else:
            card = d24 or {}
        canonical_ok = bool(price and price.get("canonical_payto")
                            and price.get("scheme") == "exact"
                            and price.get("network") == NETWORK)
        if not canonical_ok:
            drift += 1
        walls.append({
            "service": svc, "host": w["host"],
            "paid_challenge": {"http": pcode, "decoded": bool(ch), **(price or {})},
            "canonical": canonical_ok,
            "dependability_24h": card,
            "dependability_all": dall,
        })

    # Fleet telemetry table (all services, frozen tagged) — context, not a buyer card.
    fleet_telemetry = []
    for name, tel in services.items():
        fleet_telemetry.append({
            "service": name,
            "frozen": name in FROZEN,
            "24h": classify(tel.get("24h") or {}),
            "all": classify(tel.get("all") or {}),
        })
    fleet_telemetry.sort(key=lambda x: (x["frozen"], x["service"]))

    proven = sum(1 for w in walls if (w["dependability_24h"] or {}).get("settled_verified", 0) > 0)
    out = {
        "tool": "settlement-dependability",
        "version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "canonical_payto": CANON,
        "network": NETWORK,
        "method": "live collector /stats (chain-verified settlements) + unpaid 402 price guard",
        "fleet_24h": {k: fleet.get(k) for k in ("challenges", "settled", "settled_verified", "failed", "p50_ms", "p95_ms")},
        "buyer_walls": walls,
        "buyer_walls_proven_path_24h": proven,
        "buyer_walls_with_canonical_402": sum(1 for w in walls if w["canonical"]),
        "fleet_telemetry": fleet_telemetry,
        "honest_external_earned_usd": 0.0,
        "note_external": "collector total_external_usdc=%s is breadth-crawler dust (tools 50/51); honest external earned $0.00" % honest_external,
        "verdict": "OK" if drift == 0 else "DRIFT",
        "blocker_count": drift,
    }
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
            f.write("\n")
    print("settlement-dependability %s  walls_proven_path=%d/%d  canonical_402=%d/%d  verdict=%s"
          % (out["generated_utc"], proven, len(walls),
             out["buyer_walls_with_canonical_402"], len(walls), out["verdict"]))
    for w in walls:
        d = w["dependability_24h"] or {}
        print("  %-18s grade=%-3s verdict=%-22s price=%-8s canonical=%s"
              % (w["service"], d.get("grade"), d.get("verdict"),
                 w["paid_challenge"].get("price_usd"), w["canonical"]))
    if args.check:
        return 0 if drift == 0 else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
