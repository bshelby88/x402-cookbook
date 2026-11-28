#!/usr/bin/env python3
"""RAEN Innovation 64 - Acquisition-Offer Disclosure Auditor (stdlib, read-only).

Tools 1-63 grade the wall (#62 constructability), the docs (#48 parity), the
payer (#49), the ledger (#50/51/52), the funnel (#53) and even individual
offers (#58 volume tier). NONE grades the one surface an autonomous buyer reads
AT THE MOMENT OF SALE: the live, unpaid 402 response body. RAEN's own buyer
tooling (#44 client-bootstrap, #45 agent-skillcard) teaches agents to derive
every value from that 402. If a service advertises an acquisition offer in its
public manifest but omits it from the live 402, a 402-first buyer never learns
the hook exists and pays full price. This tool grades MANIFEST-PROMISED vs
LIVE-402-DISCLOSED acquisition offers.

Offers checked:
  first_call_free  - charge-and-rebate / x-payer-address / "first call free"
  bulk_volume      - bulk / volume-tier pricing
  redeem_recovery  - redemption path after a settled-but-undelivered call
  free_dev_key     - /keys/request or a free developer key

Read-only: one unpaid manifest GET + one unpaid paid-route POST per kept-live
wall. NEVER signs, NEVER sends X-PAYMENT, NEVER moves funds, NEVER uses a key,
NEVER posts anywhere, NEVER deploys. Burn freeze respected (kept-live only).

Usage:
  python3 scripts/offer-disclosure.py --check
  python3 scripts/offer-disclosure.py --out registry/offer-disclosure.json

Exit: 0 = all walls canonical and no disclosure gaps; 1 = gap or drift found;
      2 = no wall reachable.
"""

import argparse, base64, datetime, json, sys, urllib.error, urllib.request

CANON = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f"
RETIRED = "0x7861db4efc14a1ed5dd8c96c528a3796560f1393"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# kept-live walls only (burn freeze); (base, paid path, valid-shaped unpaid body)
WALLS = [
    ("royal-ruby", "https://royal-ruby-x402.fly.dev", "/api/law-lookup",
     {"topic": "credit report dispute rights"}),
    ("contract-eye", "https://contract-eye-x402.fly.dev", "/api/analyze-contract",
     {"text": "This agreement auto-renews every twelve months unless cancelled sixty days prior."}),
    ("nanobanana", "https://nanobanana-x402.fly.dev", "/api/generate-image",
     {"prompt": "A product hero image, neon terminal style", "aspectRatio": "16:9"}),
    ("raen-mcp-gateway", "https://raen-mcp-gateway.fly.dev", "/mcp",
     {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
      "params": {"name": "raen_law_lookup", "arguments": {"topic": "FCRA"}}}),
]

OFFER_SIGNATURES = {
    "first_call_free": ["first call free", "first-call-free", "charge-and-rebate",
                        "charge and rebate", "rebate", "x-payer-address"],
    "bulk_volume": ["bulk", "volume tier", "volume pricing", "per citation", "100-500"],
    "redeem_recovery": ["redeem", "already settled", "never got your result",
                        "never got the result", "claim it at"],
    "free_dev_key": ["/keys/request", "free dev key", "developer key"],
}


def _fetch(url, body=None, timeout=25):
    headers = dict(UA)
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()
    except Exception as e:  # noqa: BLE001 - read-only probe, report as unreachable
        return 0, {}, str(e).encode()


def decode_challenge(headers):
    raw = headers.get("payment-required") or headers.get("Payment-Required")
    if not raw:
        return None
    try:
        if raw.startswith("base64,"):
            raw = raw[7:]
        return json.loads(base64.b64decode(raw + "=" * (-len(raw) % 4)))
    except Exception:
        return None


def live_disclosure_text(body_obj):
    """The 402 body + its nested machine-readable surfaces a buyer actually reads."""
    parts = [json.dumps(body_obj)]
    for key in ("payment_instructions", "paymentInstructions", "extensions",
                "resource", "offers", "x-guidance"):
        v = body_obj.get(key) if isinstance(body_obj, dict) else None
        if v is not None:
            parts.append(json.dumps(v))
    return " ".join(parts).lower()


def audit_wall(name, base, path, body):
    mst, _, mraw = _fetch(base + "/.well-known/x402.json")
    cst, hdrs, craw = _fetch(base + path, body)
    out = {"wall": name, "manifest_status": mst, "challenge_status": cst}

    # canonical gate (no free backdoor: a 2xx on a paid call is a hard defect)
    chal = decode_challenge(hdrs)
    if cst == 200:
        out.update(canonical=False, defect="FREE_BACKDOOR_2XX")
        return out
    accepts = (chal or {}).get("accepts") or []
    a0 = accepts[0] if accepts else {}
    payto = str(a0.get("payTo", "")).lower()
    canon = (a0.get("scheme") == "exact" and a0.get("network") == "eip155:8453"
             and payto == CANON and str(a0.get("amount", "0")).isdigit()
             and int(a0.get("amount", "0")) > 0)
    out.update(canonical=bool(canon), scheme=a0.get("scheme"),
               network=a0.get("network"), payTo=a0.get("payTo"),
               amount=a0.get("amount"), x402Version=(chal or {}).get("x402Version"),
               accepts_count=len(accepts))

    manifest_text = mraw.decode("utf-8", "replace").lower()
    try:
        live_obj = json.loads(craw)
    except Exception:
        live_obj = {}
    live_text = live_disclosure_text(live_obj)

    offers = {}
    for key, sigs in OFFER_SIGNATURES.items():
        promised = any(s in manifest_text for s in sigs)
        disclosed = any(s in live_text for s in sigs)
        offers[key] = ("GAP" if promised and not disclosed else
                       "OK" if promised else "N/A")
    out["offers"] = offers
    out["gaps"] = [k for k, v in offers.items() if v == "GAP"]
    # retired payTo anywhere in the served challenge body is a hard drift signal
    out["retired_in_body"] = RETIRED in craw.decode("utf-8", "replace").lower()
    return out


def self_test():
    cases = []
    # GAP: promised in manifest, absent from live 402
    cases.append(({"first_call_free": True}, "charge-and-rebate x-payer-address",
                  {"accepts": [{"amount": "5000"}]}, "first_call_free", "GAP"))
    # OK: promised and disclosed
    cases.append(({"first_call_free": True}, "charge-and-rebate x-payer-address",
                  {"payment_instructions": "rebate via x-payer-address"},
                  "first_call_free", "OK"))
    # N/A: not advertised
    cases.append(({}, "just a wall", {}, "bulk_volume", "N/A"))
    # nested disclosure counts (extensions)
    cases.append(({"bulk": True}, "bulk tier",
                  {"extensions": {"info": "bulk 100-500"}}, "bulk_volume", "OK"))
    # redeem disclosed under snake_case payment_instructions
    cases.append(({"redeem": True}, "redeem",
                  {"payment_instructions": {"already_settled_redeem": "/api/redeem"}},
                  "redeem_recovery", "OK"))
    passed = 0
    for i, (mfake, mftext, live_obj, key, want) in enumerate(cases, 1):
        mt = (json.dumps(mfake) + " " + mftext).lower()
        lt = live_disclosure_text(live_obj)
        sigs = OFFER_SIGNATURES[key]
        got = ("GAP" if any(s in mt for s in sigs) and not any(s in lt for s in sigs)
               else "OK" if any(s in mt for s in sigs) else "N/A")
        ok = got == want
        print(f"  self-test {i}: want={want} got={got} {'PASS' if ok else 'FAIL'}")
        passed += int(ok)
    return passed, len(cases)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--out")
    args = ap.parse_args()

    p, t = self_test()
    print(f"self-test {p}/{t}\n")
    if p != t:
        return 1

    walls = [audit_wall(*w) for w in WALLS]
    reachable = [w for w in walls if w["challenge_status"] in (402,)]
    total_gaps = sum(len(w.get("gaps", [])) for w in walls)
    hard = [w["wall"] for w in walls if not w.get("canonical", False)
            or w.get("defect") or w.get("retired_in_body")]
    report = {
        "tool": "offer-disclosure", "innovation": 64,
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "verdict": ("NO_WALLS_REACHABLE" if not reachable else
                    "HARD_DRIFT" if hard else
                    "DISCLOSURE_GAPS" if total_gaps else "ALL_OFFERS_DISCLOSED"),
        "walls_reachable": len(reachable), "total_gaps": total_gaps,
        "hard_drift_walls": hard, "walls": walls,
        "method": "one unpaid manifest GET + one unpaid 402 POST per kept-live wall; read-only",
    }
    print(json.dumps(report, indent=1))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=1)
            f.write("\n")
    if args.check:
        return 2 if not reachable else 1 if (hard or total_gaps) else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
