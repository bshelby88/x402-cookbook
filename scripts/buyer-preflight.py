#!/usr/bin/env python3
"""RAEN buyer preflight — verify a 402 wall BEFORE you sign anything.

Read-only: sends one UNPAID request, decodes the HTTP 402 challenge, and checks
the payment contract (payTo / amount / network / asset / header). It never
signs, never sends funds, and never moves money.

Usage:
  python3 scripts/buyer-preflight.py https://royal-ruby-x402.fly.dev/api/ping
  python3 scripts/buyer-preflight.py https://dispute-forge-x402.fly.dev/api/dispute-pack \
      --method POST --body '{"creditor":"Acme","reason":"not mine"}' --expect-amount 10000

Exit codes: 0 = healthy RAEN wall (canonical payTo), 1 = not a valid 402 / bad contract,
2 = price mismatch against --expect-amount.
"""

import argparse
import base64
import json
import sys
import urllib.error
import urllib.request

CANONICAL_PAYTO = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f"
RETIRED_PAYTO = "0x7861db4efc14a1ed5dd8c96c528a3796560f1393"
BASE_USDC = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
BASE_NETWORK = "eip155:8453"
VERIFIED_RETRY_HEADER = "X-PAYMENT"  # real $0.001 settle, SDK v2.30
HEADER_NAMES = ("payment-required", "x-payment-required")


def fetch(url, method, body, timeout):
    data = body.encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"User-Agent": "raen-buyer-preflight/1.0", "Accept": "application/json"},
    )
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.status, dict(resp.headers), resp.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read().decode("utf-8", "ignore")


def decode_challenge(headers, body):
    for name in HEADER_NAMES:
        raw = None
        for key, value in headers.items():
            if key.lower() == name:
                raw = value
                break
        if raw:
            return json.loads(base64.b64decode(raw + "=" * (-len(raw) % 4)))
    stripped = body.strip()
    if stripped.startswith("{"):
        candidate = json.loads(stripped)
        if "accepts" in candidate or "payTo" in candidate or "x402Version" in candidate:
            return candidate
    raise ValueError("no payment-required header and no challenge JSON in body")


def accepts_from(challenge):
    # x402 v2 envelope: {x402Version:2, resource:{...}, accepts:[...]}
    if isinstance(challenge, dict) and isinstance(challenge.get("accepts"), list):
        return challenge["accepts"], "x402 v2 envelope (accepts[])"
    # older flat object or bare array of requirement objects
    if isinstance(challenge, dict) and "payTo" in challenge:
        return [challenge], "legacy flat requirement (upgrade docs)"
    if isinstance(challenge, list):
        return challenge, "legacy array requirement (upgrade docs)"
    raise ValueError("challenge has no recognizable accepts[] / requirement object")


def full_address_match(candidate, expected):
    """Full 42-char hex compare, case-insensitive. NEVER prefix/suffix shorthand."""
    return (
        isinstance(candidate, str)
        and len(candidate) == 42
        and candidate.lower() == expected.lower()
    )


def main():
    ap = argparse.ArgumentParser(description="Verify a RAEN x402 wall before paying.")
    ap.add_argument("url", help="Paid endpoint to probe (unpaid).")
    ap.add_argument("--method", default="GET", help="HTTP method (default GET).")
    ap.add_argument("--body", default=None, help="JSON request body (for POST).")
    ap.add_argument("--expect-amount", default=None, help="Expected atomic amount; mismatch = exit 2.")
    ap.add_argument("--timeout", type=int, default=20)
    args = ap.parse_args()

    status, headers, body = fetch(args.url, args.method, args.body, args.timeout)
    if status != 402:
        print(f"FAIL: expected HTTP 402, got {status}. Not a paid wall (or it is down).")
        return 1

    try:
        challenge = decode_challenge(headers, body)
        accepts, shape = accepts_from(challenge)
    except Exception as exc:
        print(f"FAIL: cannot decode challenge: {exc}")
        return 1

    print(f"HTTP 402 OK  |  shape: {shape}")
    print(f"retry header: {VERIFIED_RETRY_HEADER}  (RAEN-verified; PAYMENT-SIGNATURE is not)")
    ok = True
    for i, req in enumerate(accepts):
        payto = req.get("payTo", "")
        amount = str(req.get("amount", ""))
        network = req.get("network", "")
        asset = req.get("asset", "")
        scheme = req.get("scheme", "")
        usd = f"{int(amount) / 1e6:.6f}" if amount.isdigit() else "?"
        canonical = full_address_match(payto, CANONICAL_PAYTO)
        retired = full_address_match(payto, RETIRED_PAYTO)
        verdict = "CANONICAL" if canonical else ("RETIRED - DO NOT PAY" if retired else "FOREIGN - DO NOT PAY")
        print(f"\naccepts[{i}]: {scheme} / {network} / {amount} atomic (${usd}) / payTo={payto}")
        print(f"  payTo verdict: {verdict}")
        if not canonical:
            ok = False
        if scheme != "exact":
            print("  WARN: scheme is not 'exact'")
            ok = False
        if network != BASE_NETWORK:
            print("  WARN: network is not Base eip155:8453")
            ok = False
        if not full_address_match(asset, BASE_USDC):
            print("  WARN: asset is not canonical Base USDC")
            ok = False
        if args.expect_amount and amount != args.expect_amount:
            print(f"  PRICE MISMATCH: expected {args.expect_amount}, live challenge says {amount}")
            return 2
    print("\n" + ("PASS: canonical RAEN wall. The live challenge above is authoritative." if ok
                 else "FAIL: contract drift detected. Do NOT sign or send funds."))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
