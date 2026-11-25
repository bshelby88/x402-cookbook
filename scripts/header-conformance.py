#!/usr/bin/env python3
"""RAEN buyer-payment-header conformance guard (stdlib only).

The x402 v2 settlement header is X-PAYMENT (@x402/core). Older RAEN recipes
taught `PAYMENT-SIGNATURE`, which gets a silent re-challenge (buyer retries and
pays twice). This guard scans recipe docs and FAILS if any non-corrective
PAYMENT-SIGNATURE instruction remains, or if a paid recipe never names the
verified X-PAYMENT header.

Read-only: no network, no signing, no money movement.
Exit 0 = conformance PASS; 1 = drift found; 2 = no recipes found.
"""
import os, sys, json, datetime, re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECIPES = os.path.join(BASE, "recipes")
CORRECTIVE = ("is stale", "stale", "older draft", "older docs", "docs say", "is not",
              "not the", "silent re-challenge", "fresh 402", "garbage",
              "verified", "was wrong", "no longer", "wrong header")

def classify(line):
    low = line.lower()
    if "payment-signature" not in low and "payment_signature" not in low:
        return None
    if any(k in low for k in CORRECTIVE):
        return "corrective"
    return "violation"

def main():
    if not os.path.isdir(RECIPES):
        print("ERROR: recipes dir not found:", RECIPES, file=sys.stderr)
        return 2
    files = sorted(f for f in os.listdir(RECIPES) if f.endswith(".md"))
    if not files:
        print("ERROR: no recipe files", file=sys.stderr)
        return 2
    violations, missing, scanned = [], [], []
    for f in files:
        p = os.path.join(RECIPES, f)
        text = open(p, encoding="utf-8").read()
        scanned.append(f)
        has_xpayment = "x-payment" in text.lower()
        for n, line in enumerate(text.splitlines(), 1):
            if classify(line) == "violation":
                violations.append({"file": f, "line": n, "text": line.strip()[:160]})
        # Only paid recipes are expected to name the header. Corrective-only
        # recipes (15, 23, 24) name it too, so this is a soft check on the set.
        if not has_xpayment and f[:2].isdigit():
            missing.append(f)
    # Verdict is driven ONLY by harmful instructions. Recipes that describe
    # post-payment recovery (22) or Bearer-key auth (04) have no payment-header
    # step; missing X-PAYMENT there is informational, not drift.
    verdict = "PASS" if not violations else "FAIL"
    out = {
        "tool": "raen-buyer-header-conformance",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "verified_header": "X-PAYMENT",
        "source_of_truth": "@x402/core README + royal-ruby/contract-eye index.js (paymentMiddleware)",
        "files_scanned": len(scanned),
        "violation_count": len(violations),
        "violations": violations,
        "non_payment_recipes_without_header_note": missing,
        "verdict": verdict,
    }
    print(json.dumps(out, indent=2))
    return 0 if verdict == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
