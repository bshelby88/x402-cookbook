#!/usr/bin/env python3
"""trust-coverage.py — honest third-party TRUST coverage map for machine buyers
(Recipe 41; closes Airtable ERICA-LUMI-CATALOG-GAP).

A machine buyer's last question before paying is: "can I verify this seller through
an independent trust layer?" This script answers it with LIVE reads from Lumi's
public trust-check API for every RAEN public surface, plus a canonical-payTo guard
on the kept-live walls (fresh unpaid 402 decode). It emits a machine-readable truth
snapshot (registry/trust-coverage.json) and a buyer-facing copy
(registry/trust-coverage.md).

Read-only, stdlib-only. No signing, no X-PAYMENT, no funds movement, no external
sends, no directory POSTs, no deploys, no secrets. BURN FREEZE: frozen services are
never probed locally — Lumi checks are third-party API calls keyed by URL and do not
touch those services. Only kept-live walls receive an unpaid 402 probe.

Exit codes: 0 CLEAN (report emitted, canonical guard clean), 1 DRIFT (noncanonical
payTo/network/scheme on a kept-live wall), 2 UNREACHABLE (no wall reachable).
"""
import argparse, base64, datetime, json, subprocess, urllib.error, urllib.parse, urllib.request

VERSION = "trust-coverage/1.0"
CANON = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f"
RETIRED = "0x7861db4efc14a1ed5dd8c96c528a3796560f1393"
AGENTCASH = "0xfbc0eb7811d477e55261d956df39f0046e192240"
UA = {"User-Agent": "Mozilla/5.0 (compatible; RAEN-trust-coverage/1.0)",
      "Accept": "application/json", "Content-Type": "application/json"}
LUMI = "https://api.lumitrades.io/v1/trust/check"

# (name, base url, role) — roles: kept-live / infra / frozen-public.
SURFACES = [
    ("royal-ruby",        "https://royal-ruby-x402.fly.dev",      "kept-live"),
    ("contract-eye",      "https://contract-eye-x402.fly.dev",    "kept-live"),
    ("nanobanana",        "https://nanobanana-x402.fly.dev",      "kept-live"),
    ("sentry-forge",      "https://sentry-forge-x402.fly.dev",    "kept-live"),
    ("raen-mcp-gateway",  "https://raen-mcp-gateway.fly.dev",     "kept-live"),
    ("raen-mcp-gateway/mcp", "https://raen-mcp-gateway.fly.dev/mcp", "kept-live"),
    ("settlement-collector", "https://settlement-collector.fly.dev", "infra"),
    ("raen-blog",         "https://raen-blog-x402.fly.dev",       "infra"),
    ("escrow",            "https://escrow-x402.fly.dev",          "frozen-public"),
    ("dispute-forge",     "https://dispute-forge-x402.fly.dev",   "frozen-public"),
    ("briefsnap",         "https://briefsnap-x402.fly.dev",       "frozen-public"),
    ("vault-pro",         "https://vault-pro-x402.fly.dev",       "frozen-public"),
    ("dispatch",          "https://dispatch-x402.fly.dev",        "frozen-public"),
    ("nft-alpha",         "https://nft-alpha-x402.fly.dev",       "frozen-public"),
]

# Kept-live walls used ONLY for the canonical payTo guard (fresh unpaid 402).
GUARD_WALLS = [
    {"svc": "royal-ruby", "base": "https://royal-ruby-x402.fly.dev",
     "route": "/api/law-lookup",
     "body": {"topic": "credit-report disputes for collection accounts", "state": "LA", "scope": "both"}},
    {"svc": "contract-eye", "base": "https://contract-eye-x402.fly.dev",
     "route": "/api/analyze-contract",
     "body": {"text": "This agreement auto-renews every twelve months unless cancelled sixty days prior.",
              "focus": ["renewal", "liability"]}},
    {"svc": "gateway", "base": "https://raen-mcp-gateway.fly.dev",
     "route": "/mcp",
     "body": {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
              "params": {"name": "raen_law_lookup", "arguments": {"query": "FCRA"}}}},
]

HONESTY = [
    "A Lumi 'no_data' verdict means NOT OBSERVED, not negative — Lumi has no record of the seller.",
    "Absence from a trust catalog is a discovery GAP; it is not proof of fraud or non-delivery.",
    "Lumi never test-bought these URLs (test_buys=0); paying for a high-value check does not change the verdict.",
    "A 402 challenge is a demand signal, not a sale. Fleet external revenue is $0.00 unless the chain says otherwise.",
    "Internal AgentCash self-pays are not external revenue. Verification is independent of our own dashboards.",
    "Claiming / monitoring a third-party trust listing is an owner-lane action; this report only measures it.",
]


def lumi(url, timeout):
    """Third-party trust check by URL. Uses curl (proven path); no local service contact."""
    q = LUMI + "?" + urllib.parse.urlencode({"url": url})
    try:
        out = subprocess.run(
            ["curl", "-s", "--max-time", str(timeout), "-H", "Accept: application/json", q],
            capture_output=True, text=True, timeout=timeout + 10).stdout.strip()
        d = json.loads(out)
    except Exception:
        return {"label": "unreachable", "error": "check failed"}
    facts = d.get("summary_facts", {}) if isinstance(d, dict) else {}
    return {
        "label": facts.get("label"),
        "scope": facts.get("scope"),
        "test_buys": facts.get("test_buys"),
        "delivered": facts.get("delivered"),
        "last_quote_check": facts.get("last_quote_check"),
        "as_of": d.get("as_of"),
        "summary": (d.get("summary") or "")[:240],
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
    for k, v in headers.items():
        if k.lower() in ("payment-required", "x-payment-required"):
            try:
                return json.loads(base64.b64decode(v + "=" * (-len(v) % 4)))
            except Exception:
                return None
    return None


def guard(w, timeout):
    cs, ch, cb = get(w["base"] + w["route"], method="POST",
                     body=json.dumps(w["body"]), timeout=timeout)
    acc = None
    if cs == 402:
        dec = decode_challenge(ch)
        if dec:
            xs = dec.get("accepts") if isinstance(dec, dict) else None
            if isinstance(xs, list) and xs:
                acc = xs[0]
            elif isinstance(dec, dict):
                acc = dec
    if not acc:
        try:
            b = json.loads(cb)
            xs = b.get("accepts")
            if isinstance(xs, list) and xs:
                acc = xs[0]
        except Exception:
            pass
    payto = (acc or {}).get("payTo")
    net = (acc or {}).get("network")
    sch = (acc or {}).get("scheme")
    ok = (cs == 402 and isinstance(payto, str) and payto.lower() == CANON.lower()
          and net == "eip155:8453" and sch == "exact")
    return {"svc": w["svc"], "status": cs, "payto": payto, "network": net,
            "scheme": sch, "canonical": ok}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--skip-lumi", action="store_true", help="skip Lumi (quota) and reuse nothing")
    args = ap.parse_args()

    surfaces = []
    for name, url, role in SURFACES:
        t: dict = {"name": name, "url": url, "role": role}
        if args.skip_lumi:
            t["lumi"] = {"label": "skipped"}
        else:
            t["lumi"] = lumi(url, args.timeout)
        surfaces.append(t)

    walls = [guard(w, args.timeout) for w in GUARD_WALLS]
    reachable = [w for w in walls if w["status"] == 402]
    drift = [w for w in walls if w["status"] == 402 and not w["canonical"]]
    verdict = "UNREACHABLE" if not reachable else ("DRIFT" if drift else "CLEAN")

    labels = {}
    for t in surfaces:
        lab = (t.get("lumi") or {}).get("label") or "unknown"
        labels[lab] = labels.get(lab, 0) + 1

    now = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    pack = {
        "generated_at": now,
        "version": VERSION,
        "scope": "read-only: third-party Lumi trust checks by URL + unpaid 402 canonical guard on kept-live walls",
        "surfaces": surfaces,
        "label_counts": labels,
        "canonical_guard": {
            "walls": walls,
            "reachable": len(reachable),
            "drift": len(drift),
            "verdict": verdict,
            "canonical_address": CANON,
        },
        "honesty": HONESTY,
    }
    with open("registry/trust-coverage.json", "w", encoding="utf-8") as f:
        json.dump(pack, f, indent=2, ensure_ascii=False)

    L = []
    A = L.append
    A("# Machine-buyer trust coverage — independent verification, honest gaps")
    A("")
    A(f"Generated {now} by `{VERSION}`. Every verdict below is a LIVE read from Lumi's "
      "public trust-check API keyed by URL, plus a canonical-payTo guard from a fresh "
      "unpaid 402 on the kept-live walls. No cached or hand-typed verdicts. "
      f"Guard verdict: **{verdict}**.")
    A("")
    A("## What an independent trust layer currently says about RAEN")
    A("")
    A("| Surface | Role | Lumi label | Observed? | Test buys |")
    A("|---|---|---|---|---|")
    for t in surfaces:
        lm = t.get("lumi") or {}
        obs = "yes" if lm.get("scope") not in (None, "not_observed") else "no"
        A(f"| {t['name']} | {t['role']} | `{lm.get('label','?')}` | {obs} | {lm.get('test_buys','?')} |")
    A("")
    A("**Reading this table:** `no_data` / `not_observed` means Lumi has no record — "
      "not a negative finding. `check_first` means Lumi knows the URL but has not "
      "test-bought it. None of these URLs has a third-party test-buy record, so no "
      "independent delivery proof exists yet. That is a discovery GAP we publish "
      "rather than hide.")
    A("")
    A("## Canonical payTo guard (fresh unpaid 402 challenges)")
    A("")
    A("| Wall | HTTP | network | scheme | payTo canonical? |")
    A("|---|---|---|---|---|")
    for w in walls:
        A(f"| {w['svc']} | {w['status']} | `{w.get('network') or 'n/a'}` | "
          f"`{w.get('scheme') or 'n/a'}` | {'YES' if w['canonical'] else 'NO — DRIFT'} |")
    A("")
    A("## Verify RAEN yourself (no account, no key)")
    A("")
    A("```bash")
    A("# 1. Ask the independent trust layer (URL-encoded):")
    A('curl -sG --data-urlencode "url=https://raen-mcp-gateway.fly.dev/mcp" \\')
    A("  https://api.lumitrades.io/v1/trust/check")
    A("")
    A("# 2. Decode a live 402 yourself — compare payTo to the canonical address:")
    A('curl -s -D - -o /dev/null -X POST https://contract-eye-x402.fly.dev/api/analyze-contract \\')
    A('  -H "Content-Type: application/json" -d \'{"text":"test","focus":["renewal"]}\'')
    A("")
    A("# 3. Prove settlement on-chain, not from our dashboard (recipe 27):")
    A("npx -y tsx scripts/buyer-receipt.ts <YOUR_TX_HASH>")
    A("```")
    A("")
    A("## Honesty")
    A("")
    for h in HONESTY:
        A(f"- {h}")
    A("")
    A("This report does not claim a sale. Machine-buyer acquisition, not cold outreach, "
      "is the priority; trust friction is one measurable part of it.")
    with open("registry/trust-coverage.md", "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")

    print(f"verdict={verdict} walls={len(reachable)}/3 drift={len(drift)} surfaces={len(surfaces)}")
    print("labels=" + json.dumps(labels, sort_keys=True))
    for w in walls:
        print(f"  {w['svc']:12s} {w['status']} canonical={w['canonical']} payto={w.get('payto')}")
    return 0 if verdict == "CLEAN" else (2 if verdict == "UNREACHABLE" else 1)


if __name__ == "__main__":
    raise SystemExit(main())
