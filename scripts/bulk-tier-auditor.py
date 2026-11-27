#!/usr/bin/env python3
"""Volume-Tier Truth Auditor - tool 58 (RAEN x402 cookbook).

Read-only, stdlib-only. Closes the gap none of tools 1-57 covered: a machine
buyer budgeting many calls needs the ADVERTISED volume price to be the price
the live 402 actually charges. Probes each kept-live paid wall unpaid at the
base call and at every documented bulk quantity, decodes payment-required,
and grades:

  * canonical envelope on EVERY tier (scheme=exact, network=eip155:8453,
    full canonical payTo, canonical USDC asset, integer amount)
  * monotonic price-per-unit (a larger tier never costs more per unit)
  * the documented floor (below the bulk minimum is the base price)
  * advertised tier (from the wall's OWN manifest) vs the live 402
  * cookbook-advertised tiers with NO manifest/live support -> DOC_DRIFT

NO signing, NO X-PAYMENT, NO funds movement, NO deploy, NO external sends.
Pricing is owner-gated: this tool REPORTS drift, never changes a price.
`--check` exits 1 only on HARD drift (non-canonical envelope, non-integer
amount, or a tier cheaper-per-unit violated by a larger tier); it never
fails on a missing payer or on owner-gated price/doc drift.
"""
import argparse, base64, datetime, json, re, sys, urllib.error, urllib.request

CANON = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f"
USDC_BASE = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
EXACT_NETWORK = "eip155:8453"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Content-Type": "application/json"}

# Wall configs. `manifest_tiers` are parsed dynamically from the wall's own
# manifest; `cookbook_tiers` are the tiers the cookbook README advertises.
# A wall whose manifest says nothing about bulk but whose cookbook advertises
# one yields DOC_DRIFT (buyer-facing doc defect) - never a service-blame claim.
WALLS = [
    {
        "name": "royal-ruby",
        "url": "https://royal-ruby-x402.fly.dev/api/law-lookup",
        "manifest": "https://royal-ruby-x402.fly.dev/.well-known/x402.json",
        "body": {"topic": "consumer rights law", "state": "federal-only"},
        "bulk_field": "bulk",
        "quantities": [5, 9, 10, 50, 100, 500],
        "floor": 10,
        "cookbook_tiers": [{"min": 10, "max": 99, "per_unit_usd": 0.002},
                           {"min": 100, "max": 500, "per_unit_usd": 0.001}],
    },
    {
        "name": "contract-eye",
        "url": "https://contract-eye-x402.fly.dev/api/analyze-contract",
        "manifest": "https://contract-eye-x402.fly.dev/.well-known/x402.json",
        "body": {"text": "This agreement requires the tenant to waive all rights and pay unlimited penalties for any reason."},
        "bulk_field": "bulk",
        "quantities": [10, 100],
        "floor": None,
        "cookbook_tiers": [{"min": 10, "max": 99, "per_unit_usd": 0.002},
                           {"min": 100, "max": None, "per_unit_usd": 0.001}],
    },
    {
        "name": "nanobanana",
        "url": "https://nanobanana-x402.fly.dev/api/generate",
        "manifest": "https://nanobanana-x402.fly.dev/.well-known/x402.json",
        "body": {"prompt": "a red circle"},
        "bulk_field": "bulk",
        "quantities": [10],
        "floor": None,
        "cookbook_tiers": [{"min": 10, "max": None, "per_unit_usd": 0.008}],
    },
]


def fetch(url, body=None, timeout=30):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=UA, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, {k.lower(): v for k, v in r.headers.items()}, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in e.headers.items()}, e.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, {}, "ERR " + repr(e)


def decode_challenge(headers):
    """Return (accepts[0], x402Version) from a base64 payment-required header."""
    ch = headers.get("payment-required")
    if not ch:
        return None, None
    try:
        j = json.loads(base64.b64decode(ch + "=" * (-len(ch) % 4)).decode())
        acc = (j.get("accepts") or [{}])[0]
        return acc, j.get("x402Version")
    except Exception:
        return None, None


def envelope_flags(acc):
    f = []
    if not acc:
        return ["NO_CHALLENGE"]
    if str(acc.get("scheme", "")).lower() != "exact":
        f.append("SCHEME_DRIFT")
    if acc.get("network") != EXACT_NETWORK:
        f.append("NETWORK_DRIFT")
    if str(acc.get("payTo", "")).lower() != CANON.lower():
        f.append("PAYTO_DRIFT")
    asset = str(acc.get("asset", "")).lower()
    if asset and asset != USDC_BASE:
        f.append("ASSET_DRIFT")
    raw = acc.get("amount")
    try:
        amount = int(raw)
        if amount <= 0 or str(raw).strip() != str(amount):
            f.append("AMOUNT_NOT_INTEGER")
    except (TypeError, ValueError):
        amount = None
        f.append("AMOUNT_NOT_INTEGER")
    return f, amount


def manifest_tier_claims(text):
    """Parse '$0.002/citation for 10-99' style claims from a manifest."""
    out, seen = [], set()
    for m in re.finditer(r"\$\s*([0-9.]+)\s*/\s*\w+\s+for\s+(\d+)\s*-\s*(\d+)", text, re.I):
        try:
            t = {"min": int(m.group(2)), "max": int(m.group(3)), "per_unit_usd": float(m.group(1))}
            key = (t["min"], t["max"], t["per_unit_usd"])
            if key not in seen:
                seen.add(key); out.append(t)
        except ValueError:
            pass
    return out


def manifest_base_claims(text):
    """Parse '$0.05 per call' style base-price claims from a manifest."""
    out = []
    for m in re.finditer(r"\$\s*([0-9.]+)\s+per\s+(?:call|request|lookup)", text, re.I):
        try:
            out.append(float(m.group(1)))
        except ValueError:
            pass
    return sorted(set(out))


def expected_per_unit(q, tiers):
    for t in tiers:
        lo, hi = t["min"], t.get("max")
        if q >= lo and (hi is None or q <= hi):
            return t["per_unit_usd"]
    return None


def audit_wall(w):
    # manifest truth (documented tiers live on the seller's own manifest)
    mstatus, _, mtext = fetch(w["manifest"])
    man_tiers = manifest_tier_claims(mtext) if mstatus == 200 else []
    man_base = manifest_base_claims(mtext) if mstatus == 200 else []
    # base probe
    _, h, _ = fetch(w["url"], w["body"])
    acc, ver = decode_challenge(h)
    flags, base_atoms = envelope_flags(acc)
    base_usd = (base_atoms / 1e6) if base_atoms is not None else None
    tiers = []
    for q in w["quantities"]:
        body = dict(w["body"])
        body[w["bulk_field"]] = q
        _, h2, _ = fetch(w["url"], body)
        a2, _ = decode_challenge(h2)
        f2, atoms = envelope_flags(a2)
        usd = (atoms / 1e6) if atoms is not None else None
        # per-unit is meaningful ONLY where the wall's own manifest documents a
        # bulk mechanism AND the quantity clears the floor. Below the floor (or
        # with no documented bulk mechanism) the field is ignored: the call is the
        # flat base price, so dividing by quantity would invent a fake discount.
        applies = bool(man_tiers) and (not w.get("floor") or q >= w["floor"])
        per = (usd / q) if (applies and usd is not None and q) else None
        exp = expected_per_unit(q, man_tiers) if man_tiers else expected_per_unit(q, w["cookbook_tiers"])
        tiers.append({"quantity": q, "amount_atoms": str(atoms) if atoms is not None else None,
                      "total_usd": usd, "bulk_mechanism_applies": applies,
                      "per_unit_usd": round(per, 6) if per is not None else None,
                      "expected_per_unit_usd": exp, "envelope_flags": f2})
        flags = flags + ["tier%d:%s" % (q, x) for x in f2]
    # monotonic: among DOCUMENTED tiers only, a larger tier never costs more per unit
    seen = [t for t in tiers if t.get("bulk_mechanism_applies") and t["per_unit_usd"] is not None]
    for i in range(1, len(seen)):
        if seen[i]["quantity"] > seen[i - 1]["quantity"] and seen[i]["per_unit_usd"] > seen[i - 1]["per_unit_usd"] + 1e-9:
            flags.append("NON_MONOTONIC_TIER")
    if base_usd is not None:
        for t in seen:
            if t["per_unit_usd"] > base_usd + 1e-9:
                flags.append("TIER_OVER_BASE_q%d" % t["quantity"])
    # floor: below bulk minimum == base price
    for t in tiers:
        if w.get("floor") and t["quantity"] < w["floor"] and base_usd is not None and t["total_usd"] is not None:
            if abs(t["total_usd"] - base_usd) > 1e-9:
                flags.append("FLOOR_BROKEN_q%d" % t["quantity"])
    # advertised-vs-live: manifest tiers authoritative for the seller
    doc_flags = []
    if not man_tiers:
        if w["cookbook_tiers"]:
            doc_flags.append("COOKBOOK_TIER_UNSUPPORTED_BY_MANIFEST")
            ignored = any(t["total_usd"] is not None and base_usd is not None
                          and abs(t["total_usd"] - base_usd) < 1e-9
                          and t["quantity"] >= w["cookbook_tiers"][0]["min"] for t in tiers)
            if ignored:
                doc_flags.append("BULK_FIELD_IGNORED_BY_LIVE_402")
    else:
        for t in tiers:
            if t["expected_per_unit_usd"] is not None and t["per_unit_usd"] is not None:
                if abs(t["per_unit_usd"] - t["expected_per_unit_usd"]) > 1e-9:
                    doc_flags.append("MANIFEST_TIER_DRIFT_q%d" % t["quantity"])
                    break
    base_drift = []
    if base_usd is not None:
        for b in man_base:
            if abs(b - base_usd) > 1e-9:
                base_drift.append({"advertised_usd": b, "live_usd": base_usd})
    if base_drift:
        doc_flags.append("MANIFEST_BASE_PRICE_DRIFT")
    hard = [f for f in flags if f in ("SCHEME_DRIFT", "NETWORK_DRIFT", "PAYTO_DRIFT", "ASSET_DRIFT",
                                     "AMOUNT_NOT_INTEGER", "NO_CHALLENGE", "NON_MONOTONIC_TIER")
            or f.startswith(("FLOOR_BROKEN_", "TIER_OVER_BASE_", "tier"))]
    return {"name": w["name"], "base_amount_atoms": str(base_atoms) if base_atoms is not None else None,
            "base_usd": base_usd, "x402_version": ver,
            "manifest_advertised_base_usd": man_base, "base_price_drift": base_drift,
            "manifest_advertised_tiers": man_tiers, "cookbook_advertised_tiers": w["cookbook_tiers"],
            "tiers": tiers, "hard_flags": sorted(set(hard)), "doc_flags": sorted(set(doc_flags))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="CI gate: fail on HARD drift only")
    ap.add_argument("--out", help="write JSON snapshot to this path")
    a = ap.parse_args()
    snap = {"tool": "bulk-tier-auditor", "version": 1,
            "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "canonical_payto": CANON, "network": EXACT_NETWORK, "asset": USDC_BASE,
            "note": "Prices are owner-gated; this tool REPORTS drift and never changes a price. No signing, no X-PAYMENT, no funds.",
            "walls": [audit_wall(w) for w in WALLS]}
    hard = any(w["hard_flags"] for w in snap["walls"])
    doc = any(w["doc_flags"] for w in snap["walls"])
    snap["verdict"] = "HARD_DRIFT" if hard else ("DOC_DRIFT_WARN" if doc else "OK")
    text = json.dumps(snap, indent=2)
    print(text)
    if a.out:
        with open(a.out, "w") as f:
            f.write(text)
    return 1 if (a.check and hard) else 0


if __name__ == "__main__":
    sys.exit(main())
