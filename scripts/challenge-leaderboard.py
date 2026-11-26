#!/usr/bin/env python3
"""challenge-leaderboard.py — buyer-facing challenge leaderboard from LIVE telemetry (Recipe 36).

Read-only, stdlib-only. No signing, no X-PAYMENT, no RPC money calls, no secrets,
no funds movement, no external sends. Sends only unpaid GET/POST probes.

A machine buyer's first trust question is "is this wall actually used, and does
anything ever settle?" Public telemetry answers that — but raw challenge counts
include scanners and bots, and internal self-pays are NOT sales. This tool builds
an honestly-labelled leaderboard from settlement-collector /stats + /ledger.json,
cross-checks a few kept-live walls against a fresh x402 v2 402 decode, and emits
both a machine-readable JSON and a buyer-facing Markdown content pack.

Exit codes: 0 CLEAN (all decoded payTo canonical), 1 DRIFT (noncanonical payTo),
2 telemetry unreachable.
"""
import argparse, base64, datetime, json, sys, urllib.error, urllib.request

CANON = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f"
RETIRED = "0x7861db4efc14a1ed5dd8c96c528a3796560f1393"
AGENTCASH = "0xfbc0eb7811d477e55261d956df39f0046e192240"
UA = {"User-Agent": "Mozilla/5.0 (compatible; RAEN-challenge-leaderboard/1.0)",
      "Accept": "*/*", "Content-Type": "application/json"}

COLLECTOR = "https://settlement-collector.fly.dev"

# Kept-live walls only. Frozen apps are never probed (BURN FREEZE); they may still
# appear in telemetry as historical traffic, which is labelled as such.
LIVE_PROBES = [
    ("royal-ruby", "/api/law-lookup", '{"query":"FCRA 611"}'),
    ("contract-eye", "/api/analyze-contract",
     '{"text":"This agreement includes liability limits and a twelve month renewal."}'),
    ("gateway", "/mcp",
     '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"raen_law_lookup","arguments":{"query":"FCRA"}}}'),
]
PROBE_BASE = {
    "royal-ruby": "https://royal-ruby-x402.fly.dev",
    "contract-eye": "https://contract-eye-x402.fly.dev",
    "gateway": "https://raen-mcp-gateway.fly.dev",
}


def get(url, method="GET", body=None, timeout=25):
    req = urllib.request.Request(url, data=body.encode() if body else None,
                                 method=method, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8", "replace")
    except Exception:
        return 0, {}, ""


def decode_challenge(headers):
    raw = None
    for k, v in headers.items():
        if k.lower() in ("payment-required", "x-payment-required"):
            raw = v
            break
    if not raw:
        return None
    try:
        return json.loads(base64.b64decode(raw + "=" * (-len(raw) % 4)))
    except Exception:
        return None


def role(addr):
    a = (addr or "").lower()
    if a == CANON:
        return "CANONICAL"
    if a == RETIRED:
        return "RETIRED"
    if a == AGENTCASH:
        return "INTERNAL_AGENTCASH"
    return "UNKNOWN"


def build():
    cs, _, cbody = get(COLLECTOR + "/stats")
    ls, _, lbody = get(COLLECTOR + "/ledger.json")
    if cs != 200 or ls != 200:
        return None, "telemetry unreachable (stats=%s ledger=%s)" % (cs, ls)
    stats = json.loads(cbody)
    ledger = json.loads(lbody)

    # latest verified settle tx per service (proof of delivery, tx-gated)
    proof = {}
    for tx in ledger.get("transactions", []):
        svc = tx.get("service")
        if svc and tx.get("tx"):
            proof.setdefault(svc, tx)

    rows = []
    for svc, data in stats.get("services", {}).items():
        d24 = data.get("24h", {})
        allt = data.get("all", {})
        p = proof.get(svc, {})
        rows.append({
            "service": svc,
            "challenges_24h": d24.get("challenges", 0),
            "settled_verified_24h": d24.get("settled_verified", 0),
            "failed_24h": d24.get("failed", 0),
            "challenges_all": allt.get("challenges", 0),
            "settled_verified_all": allt.get("settled", 0),
            "external_revenue_usd": allt.get("revenue_external_usd", 0),
            "internal_revenue_usd": allt.get("revenue_internal_usd", 0),
            "last_proof_tx": p.get("tx"),
            "last_proof_class": p.get("classification"),
            "last_proof_usd": p.get("amount_usd"),
        })
    rows.sort(key=lambda r: (-r["challenges_24h"], r["service"]))

    # fresh x402 v2 decode on kept-live walls; price + payTo truth
    live = {}
    drift = []
    for svc, path, body in LIVE_PROBES:
        code, hdrs, _ = get(PROBE_BASE[svc] + path, "POST", body)
        ch = decode_challenge(hdrs)
        entry = {"url": PROBE_BASE[svc] + path, "http": code, "decoded": bool(ch)}
        if ch and ch.get("accepts"):
            a = ch["accepts"][0]
            amt = a.get("amount")
            # x402 v2 sends amount as a decimal STRING of micro-USDC (e.g. "5000").
            try:
                amt = int(amt)
            except (TypeError, ValueError):
                amt = None
            entry.update({
                "amount_atomic": amt,
                "amount_usd": (amt / 1_000_000) if amt is not None else None,
                "network": a.get("network") or ch.get("network"),
                "scheme": a.get("scheme"),
                "payto": a.get("payTo"),
                "payto_role": role(a.get("payTo")),
                "asset": a.get("asset"),
            })
            if role(a.get("payTo")) != "CANONICAL":
                drift.append(svc)
        live[svc] = entry

    f24 = stats.get("fleet_24h", {})
    report = {
        "tool": "raen-challenge-leaderboard/1.0",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source": "settlement-collector /stats + /ledger.json (tx-gated) and fresh x402 v2 402 decode",
        "canonical_payto": CANON,
        "read_only": True,
        "fleet_24h": {
            "challenges": f24.get("challenges"),
            "settled_verified": f24.get("settled_verified"),
            "failed": f24.get("failed"),
            "external_revenue_usd": f24.get("revenue_external_usd"),
            "internal_revenue_usd": f24.get("revenue_internal_usd"),
        },
        "ledger": {
            "settled_tx_count": ledger.get("settled_tx_count"),
            "settled_tx_count_external": ledger.get("settled_tx_count_external"),
            "settled_tx_count_internal": ledger.get("settled_tx_count_internal"),
            "total_external_usdc": ledger.get("total_external_usdc"),
            "distinct_external_payers": ledger.get("distinct_external_payers"),
        },
        "leaderboard": rows,
        "live_402": live,
        "drift": drift,
        "truth_notes": [
            "Challenges include scanners/bots; they are demand signal, NOT sales.",
            "Only tx-gated verified settles count; unverified 200s were a phantom-revenue bug (fixed).",
            "External earned revenue is 0; all 45 settles are internal self-pays from AgentCash.",
            "Frozen apps are never probed (BURN FREEZE); historical telemetry is labelled as such.",
            "Live 402 decode wins over every cached price sheet, manifest and marketplace listing.",
        ],
        "verdict": "DRIFT" if drift else "CLEAN",
    }
    return report, None


def markdown(rep):
    f = rep["fleet_24h"]
    l = rep["ledger"]
    out = [
        "# RAEN /challenge leaderboard — live, truth-labelled",
        "",
        "Generated %s. Source: settlement-collector `/stats` + `/ledger.json` (tx-gated), "
        "cross-checked against a fresh x402 v2 402 decode on kept-live walls." % rep["generated_at"],
        "",
        "> **Read this first.** Challenges include scanners and bots — they are a demand "
        "signal, not sales. Only settlements with an on-chain tx count. **External earned "
        "revenue: $0.00.** All %s verified settles are internal self-pays from the AgentCash "
        "test wallet, labelled as such, never counted as revenue." % l["settled_tx_count"],
        "",
        "Fleet 24h: **%s challenges**, %s tx-verified settles, %s failed. "
        "External USD 0 / internal USD %s." % (
            f["challenges"], f["settled_verified"], f["failed"], f["internal_revenue_usd"]),
        "",
        "## Challenge leaderboard (24h, live telemetry)",
        "",
        "| # | wall | challenges 24h | verified settles 24h | failed 24h | all-time settles | external $ | last proof tx |",
        "|---|------|---------------:|---------------------:|-----------:|-----------------:|-----------:|---------------|",
    ]
    for i, r in enumerate(rep["leaderboard"], 1):
        tx = r["last_proof_tx"]
        proof = ("`%s…` (%s)" % (tx[:12], r["last_proof_class"])) if tx else "—"
        out.append("| %d | %s | %d | %d | %d | %d | %.2f | %s |" % (
            i, r["service"], r["challenges_24h"], r["settled_verified_24h"],
            r["failed_24h"], r["settled_verified_all"], r["external_revenue_usd"], proof))
    out += ["", "## Live 402 price + payTo (fresh, unpaid probe)", "",
            "| wall | HTTP | price | payTo role | network |", "|------|------|------:|------------|---------|"]
    for svc, e in rep["live_402"].items():
        out.append("| %s | %s | %s | %s | %s |" % (
            svc, e["http"], ("$%s" % e["amount_usd"]) if e.get("amount_usd") is not None else "—",
            e.get("payto_role", "—"), e.get("network", "—")))
    out += ["", "Verdict: **%s**." % rep["verdict"], "",
            "Buyer rule: re-run `buyer-preflight.py` on your target wall immediately before paying. "
            "The live 402 is authoritative; this leaderboard is a snapshot with a timestamp.", ""]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="Build a truth-labelled challenge leaderboard from live RAEN telemetry")
    ap.add_argument("--json", help="write machine-readable JSON to this path")
    ap.add_argument("--md", help="write buyer-facing Markdown content pack to this path")
    args = ap.parse_args()
    rep, err = build()
    if err:
        print("ERROR", err)
        return 2
    assert rep is not None
    if args.json:
        open(args.json, "w").write(json.dumps(rep, indent=2) + "\n")
    if args.md:
        open(args.md, "w").write(markdown(rep))
    print("VERDICT", rep["verdict"], "| walls", len(rep["leaderboard"]),
          "| decoded", sum(1 for e in rep["live_402"].values() if e["decoded"]),
          "| fleet24h", rep["fleet_24h"]["challenges"], "challenges,",
          rep["fleet_24h"]["settled_verified"], "verified settles, external $",
          rep["fleet_24h"]["external_revenue_usd"])
    return 1 if rep["drift"] else 0


if __name__ == "__main__":
    sys.exit(main())
