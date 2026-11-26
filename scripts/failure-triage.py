#!/usr/bin/env python3
"""RAEN Innovation 25 - machine-buyer failure triage + live buyer-doc truth audit.

Read-only, stdlib-only. Never signs, never attaches a payment header, never moves money.

Two modes:
  * triage an OBSERVED failure:  --status 402 --header-used PAYMENT-SIGNATURE [--url ...]
  * audit LIVE buyer docs:       --audit-docs [--out report.json]

The first mode turns an agent's raw HTTP outcome into a machine-readable verdict with an
explicit do_not_repay flag (the silent-rechallenge / double-pay trap). The second mode
fetches the buyer-facing docs a machine actually reads and flags claims that contradict
live probes: stale PAYMENT-SIGNATURE teaching, retired payTo, wrong network, stale
verification stamps, and "wall is down" claims about a wall that is live and canonical.

Usage:
  python3 scripts/failure-triage.py --status 402 --header-used PAYMENT-SIGNATURE
  python3 scripts/failure-triage.py --status 500 --paid --url https://.../api/x
  python3 scripts/failure-triage.py --audit-docs --out registry/failure-triage-20261125.json

Exit: 0 = safe/clean, 1 = high-severity finding (do not repay / doc defect), 2 = manual review.
"""
import argparse, base64, datetime, json, re, sys, urllib.error, urllib.request

CANON = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f"
RETIRED = "0x7861db4efc14a1ed5dd8c96c528a3796560f1393"
VERIFIED_HEADER = "X-PAYMENT"
STALE_HEADER = "PAYMENT-SIGNATURE"

DOCS = [
    "https://rae-fleet-router.fly.dev/pricing.md",
    "https://rae-fleet-router.fly.dev/faq.md",
    "https://rae-fleet-router.fly.dev/faq.json",
    "https://rae-fleet-router.fly.dev/how-it-works.json",
    "https://rae-fleet-router.fly.dev/pay-failed?format=json",
    "https://rae-fleet-router.fly.dev/terms.md",
    "https://rae-fleet-router.fly.dev/privacy.md",
]
CONTRACT_EYE = "https://contract-eye-x402.fly.dev/.well-known/x402.json"

def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={
        "User-Agent": "raen-failure-triage/1.0",
        "Accept": "application/json, text/plain, */*",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8", "ignore")
    except Exception as e:
        return None, {}, "FETCH_ERROR: %s" % e

def decode_challenge(headers, body):
    raw = None
    for k, v in headers.items():
        if k.lower() in ("payment-required", "x-payment-required"):
            raw = v; break
    try:
        if not raw:
            d = json.loads(body)
            raw = d.get("payment-required") or d.get("x-payment-required")
            if not raw and isinstance(d.get("accepts"), list):
                return d
        if raw:
            return json.loads(base64.b64decode(raw + "=" * (-len(raw) % 4)))
    except Exception:
        return None
    return None

def verdict_for(status, header_used, paid, body):
    h = (header_used or "").strip().lower().replace("_", "-")
    b = (body or "").lower()
    if status == 402:
        if h == "payment-signature":
            return dict(code="STALE_RETRY_HEADER", severity="high", do_not_repay=True,
                        root_cause="PAYMENT-SIGNATURE is not the RAEN retry header; the wall silently re-challenged you.",
                        fix="Use X-PAYMENT on the retry of the SAME request. Do not sign a second authorization for this call.",
                        reference="cookbook recipe 25 / 23; verified settle 2026-11-22")
        if h == "x-payment":
            return dict(code="PAYMENT_REJECTED", severity="high", do_not_repay=True,
                        root_cause="A payment header was attached but the challenge was re-issued.",
                        fix="Compare signed amount/payTo/network/nonce to the live accepts[0] verbatim. If a settle occurred, look up by tx (claims desk) instead of paying again.",
                        reference="recipe 27 buyer-receipt + settlement-collector /storefront/claims")
        return dict(code="EXPECTED_UNPAID_CHALLENGE", severity="info", do_not_repay=False,
                    root_cause="Unpaid probe: HTTP 402 is the healthy receipt of a paid wall.",
                    fix="Decode payment-required, verify full 42-char payTo against canonical, copy accepts[0] verbatim, sign once, retry with X-PAYMENT.",
                    reference="recipe 23 buyer-preflight")
    if status == 401:
        return dict(code="AUTH_GATE", severity="medium", do_not_repay=True,
                    root_cause="401 is an auth gate, not an x402 challenge.",
                    fix="Request a dev key or use the direct wall. Never attach a payment to a 401.",
                    reference="raen-mcp-gateway /keys/request")
    if status == 403:
        return dict(code="IDENTITY_WALL", severity="medium", do_not_repay=True,
                    root_cause="Access is gated by identity, not payment.",
                    fix="Stop; this path is owner-lane. No amount of USDC opens it.",
                    reference="RAEN CHARTER boundaries")
    if status == 404:
        return dict(code="BAD_ROUTE", severity="medium", do_not_repay=True,
                    root_cause="Route does not exist (or was retired/scaled to zero).",
                    fix="Re-read the live manifest and /catalog.json before spending.",
                    reference="recipe 31 catalog-parity")
    if status == 429:
        return dict(code="RATE_LIMITED", severity="medium", do_not_repay=True,
                    root_cause="Rate limited; no payment was accepted.",
                    fix="Back off and retry unpaid later. Do not treat as a payment failure.",
                    reference="collector /stats")
    if status in (500, 502, 503, 504):
        if paid:
            return dict(code="SETTLED_NO_DELIVERY", severity="high", do_not_repay=True,
                        root_cause="Payment may have settled even though the handler errored.",
                        fix="Do NOT pay again. Verify the tx on-chain (recipe 27) and use the claims desk with the tx hash for re-delivery.",
                        reference="recipe 22 claims-desk / recipe 27 buyer-receipt")
        if status == 503:
            return dict(code="CAPABILITY_GATE", severity="medium", do_not_repay=True,
                        root_cause="F1 settle-order gate: dead/quota LLM key returns 503 with NO 402 challenge.",
                        fix="No payment is possible on this route right now. Retry later; do not sign anything.",
                        reference="F1 SETTLE-ORDER DOCTRINE")
        return dict(code="SERVER_ERROR", severity="medium", do_not_repay=True,
                    root_cause="Upstream handler error before any challenge was accepted.",
                    fix="Retry unpaid later; if it persists, report the wall as degraded.",
                    reference="collector /stats")
    if status == 200:
        if '"degraded"' in b and 'true' in b:
            return dict(code="DEGRADED_DELIVERY", severity="high", do_not_repay=False,
                        root_cause="Paid call returned a degraded deliverable (TRUTH law: not the advertised output).",
                        fix="Capture the response, flag it to the operator, and use the claims desk if a paid 200 carried less than advertised.",
                        reference="RAEN CHARTER TRUTH law")
        return dict(code="OK", severity="info", do_not_repay=False,
                    root_cause="Success.", fix="No action.", reference="")
    return dict(code="UNKNOWN", severity="high", do_not_repay=True,
                root_cause="Unrecognised outcome.", fix="Manual review; do not re-pay.", reference="")

def triage(args):
    out = {"generated_utc": now(), "mode": "triage", "canonical_payto": CANON,
           "observed": {"status": args.status, "header_used": args.header_used, "paid": bool(args.paid)}}
    v = verdict_for(args.status, args.header_used, args.paid, args.body)
    out["verdict"] = v
    if args.url:
        st, hd, bd = fetch(args.url)
        env = decode_challenge(hd, bd)
        if env:
            acc = (env.get("accepts") or [{}])[0]
            out["live_challenge"] = {
                "status": st, "scheme": acc.get("scheme"), "network": acc.get("network"),
                "amount": acc.get("amount"), "payTo": acc.get("payTo"),
                "payTo_verdict": "CANONICAL" if str(acc.get("payTo", "")).lower() == CANON else "NON_CANONICAL",
            }
        else:
            out["live_challenge"] = {"status": st, "decode": "NO_CHALLENGE"}
    return out

CAUTION = ("never", "reject", "wrong", "not the", "do not", "vs ", "vs\\u0020", "fail",
           "cause", "symptom", "avoid", "instead", "stale", "legacy", "retired",
           "misroute", "drift", "does not own", "not own", "incident")

def taught_as_value(text, token):
    """True if any occurrence of token is presented as a value, not warned against."""
    low = text.lower()
    start = 0
    found = False
    while True:
        i = low.find(token.lower(), start)
        if i < 0:
            break
        found = True
        win = low[max(0, i - 180): i + len(token) + 180]
        if not any(k in win for k in CAUTION):
            return True  # at least one occurrence taught as a value, not warned against
        start = i + len(token)
    return False if found else False

def audit_docs(args):
    findings = []
    checked = []
    for url in DOCS:
        st, hd, bd = fetch(url)
        checked.append({"url": url, "status": st, "bytes": len(bd)})
        if st != 200:
            findings.append({"code": "DOC_UNREACHABLE", "severity": "high", "url": url,
                             "detail": "HTTP %s" % st, "fix": "Repair or re-deploy the doc route."})
            continue
        low = bd.lower()
        if STALE_HEADER.lower() in low and taught_as_value(bd, STALE_HEADER):
            findings.append({"code": "STALE_RETRY_HEADER", "severity": "high", "url": url,
                             "detail": "Doc teaches PAYMENT-SIGNATURE; live-retry header is X-PAYMENT (silent re-challenge -> double-pay).",
                             "fix": "Replace PAYMENT-SIGNATURE with X-PAYMENT in the doc source and redeploy."})
        if RETIRED in low and taught_as_value(bd, RETIRED):
            findings.append({"code": "RETIRED_PAYTO_TAUGHT", "severity": "high", "url": url,
                             "detail": "Doc mentions retired payee 0x7861...f1393.",
                             "fix": "Point buyers to canonical 0x9b8a...f72f; keep retired address only in stranding-watch context."})
        if "eip155:84532" in low and taught_as_value(bd, "eip155:84532"):
            findings.append({"code": "WRONG_NETWORK", "severity": "high", "url": url,
                             "detail": "Doc mentions Base Sepolia eip155:84532.",
                             "fix": "Use eip155:8453 (Base mainnet)."})
        stamps = re.findall(r"20\d\d-\d\d-\d\d", bd)
        old = [d for d in stamps if d < "2026-11-19"]
        if old:
            findings.append({"code": "STALE_VERIFICATION", "severity": "medium", "url": url,
                             "detail": "%d date stamp(s) older than 7 days; newest-old=%s" % (len(old), sorted(set(old))[0]),
                             "fix": "Re-probe cited URLs and restamp with same-day verification."})
        down_claim = re.search(r"\b(down|offline|unreachable|not offered|dead)\b", low) is not None
        if "contract-eye" in low and down_claim:
            cs, chd, cbd = fetch(CONTRACT_EYE, timeout=20)
            cenv = decode_challenge(chd, cbd)
            acc = (cenv or {}).get("accepts") or [{}]
            payto_ok = (str(acc[0].get("payTo", "")).lower() == CANON
                        or CANON in cbd.lower())  # manifest shapes vary; accept either proof
            if payto_ok:
                findings.append({"code": "STALE_DOWN_CLAIM", "severity": "medium", "url": url,
                                 "detail": "Doc lists contract-eye as down; its live manifest is canonical.",
                                 "fix": "Remove contract-eye from the down-walls list or re-check the recovery matrix."})
    return {"generated_utc": now(), "mode": "audit-docs", "canonical_payto": CANON,
            "verified_retry_header": VERIFIED_HEADER, "docs_checked": checked,
            "finding_count": len(findings), "findings": findings}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--status", type=int)
    p.add_argument("--header-used")
    p.add_argument("--body", default="")
    p.add_argument("--paid", action="store_true")
    p.add_argument("--url")
    p.add_argument("--audit-docs", action="store_true")
    p.add_argument("--out")
    a = p.parse_args()
    if a.audit_docs:
        out = audit_docs(a)
    elif a.status is not None:
        out = triage(a)
    else:
        p.print_help(); return 2
    text = json.dumps(out, indent=2, ensure_ascii=False)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    print(text)
    if a.audit_docs:
        return 1 if any(f["severity"] == "high" for f in out["findings"]) else 0
    return 1 if out["verdict"]["severity"] == "high" else (2 if out["verdict"]["code"] == "UNKNOWN" else 0)

if __name__ == "__main__":
    raise SystemExit(main())
