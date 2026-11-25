#!/usr/bin/env python3
"""catalog-parity.py — read-only discovery-parity auditor for the RAEN x402 fleet.

A machine buyer that discovers the fleet through rae-fleet-router /catalog.json
needs that catalog to be COMPLETE and CANONICAL. This tool compares the live
catalog against an evidence-backed list of known-live paid walls and reports:

  * discovery_gap  - a live, canonical wall that the catalog does not advertise
  * catalog_drift  - a catalog item whose payTo/network is not canonical
  * unverifiable   - an expected host that could not be probed this run

It sends ONLY unauthenticated GETs. It never signs, never builds an X-PAYMENT
header, and never moves money. A 402 on a paid route is not needed: /health and
/.well-known/x402.json are free surfaces and are sufficient to prove liveness
and payTo canonity for the parity check.

Usage:
  python scripts/catalog-parity.py
  python scripts/catalog-parity.py --expected registry/known-live-walls.json --out report.json
  python scripts/catalog-parity.py --fail-on-gap   (exit 1 if a gap exists; for CI)

Truth order (same as the fleet): live challenge > manifest > catalog > registry.
This tool deliberately trusts the LIVE catalog and LIVE manifests; the expected
host list only says where to look, never what to conclude.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

CATALOG_URL = "https://rae-fleet-router.fly.dev/catalog.json"
CANONICAL_PAYTO = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f"
CANONICAL_NETWORK = "eip155:8453"
USER_AGENT = "Mozilla/5.0 (compatible; RAEN-catalog-parity/1.0; +https://github.com/bshelby88/x402-cookbook)"
TIMEOUT = 15

# Fallback expected walls when no registry file is supplied. Each of these was
# verified live at the time this tool shipped (see registry/known-live-walls.json
# for per-host evidence). Keep the registry authoritative; this is a convenience.
DEFAULT_EXPECTED = [
    "briefsnap-x402.fly.dev",
    "contract-eye-x402.fly.dev",
    "dispatch-x402.fly.dev",
    "dispute-forge-x402.fly.dev",
    "escrow-x402.fly.dev",
    "nanobanana-x402.fly.dev",
    "nft-alpha-x402.fly.dev",
    "power-pack-x402.fly.dev",
    "rae-fleet-router.fly.dev",
    "royal-ruby-x402.fly.dev",
    "suprapack-x402.fly.dev",
    "tradingagents-x402.fly.dev",
    "vault-pro-x402.fly.dev",
]


def utcnow():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def http_get(url):
    """Return (status, body_bytes, error). Never raises."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json,text/plain,*/*"},
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, resp.read(), None
    except urllib.error.HTTPError as exc:
        return exc.code, b"", "http %s" % exc.code
    except Exception as exc:  # network/DNS/TLS
        return 0, b"", "%s: %s" % (type(exc).__name__, str(exc)[:120])


def is_canonical_payto(value):
    return isinstance(value, str) and value.strip().lower() == CANONICAL_PAYTO


def collect_payto(obj, found):
    """Recursively collect payTo-like strings from an arbitrary manifest."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key.lower() in ("payto", "pay_to", "payee", "recipient") and isinstance(value, str):
                found.add(value.strip())
            collect_payto(value, found)
    elif isinstance(obj, list):
        for value in obj:
            collect_payto(value, found)
    return found


def load_expected(path):
    if not path:
        return DEFAULT_EXPECTED, "built-in default list"
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, dict):
        walls = data.get("walls", [])
        hosts = [
            w["host"] if isinstance(w, dict) else str(w)
            for w in walls
        ]
        return hosts, path
    return [str(w) for w in data], path


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--catalog", default=CATALOG_URL, help="live /catalog.json URL")
    parser.add_argument("--expected", default=None, help="path to registry/known-live-walls.json")
    parser.add_argument("--out", default=None, help="write the JSON report here")
    parser.add_argument("--fail-on-gap", action="store_true", help="exit 1 when a discovery gap or drift exists")
    args = parser.parse_args()

    expected, expected_source = load_expected(args.expected)

    status, raw, err = http_get(args.catalog)
    if status != 200:
        print("catalog-parity: catalog fetch failed: %s" % err, file=sys.stderr)
        return 2
    catalog = json.loads(raw.decode("utf-8", "replace"))

    walls = catalog.get("walls", []) or []
    items = []
    for wall in walls:
        if not isinstance(wall, dict):
            continue
        for item in wall.get("items", []) or []:
            entry = dict(item)
            entry["_wall_host"] = wall.get("host")
            items.append(entry)

    catalog_hosts = sorted(set(
        [w.get("host") for w in walls if isinstance(w, dict) and w.get("host")]
        + [i.get("host") for i in items if i.get("host")]
    ))
    catalog_host_set = set(host.lower() for host in catalog_hosts)

    drift = []
    for item in items:
        payto = item.get("payTo")
        network = item.get("network")
        price = item.get("price_usdc")
        issues = []
        # Free/zero-price routes with null payTo are advertised free tiers, not
        # misrouted money. Flag them as 'free' only when a price is missing too.
        if not is_canonical_payto(payto):
            if (price in (None, 0, "0")) and payto is None:
                issues.append("free_route_null_payto")
            else:
                issues.append("non_canonical_payTo")
        if network and network != CANONICAL_NETWORK:
            issues.append("wrong_network")
        if issues:
            drift.append({
                "host": item.get("_wall_host") or item.get("host"),
                "slug": item.get("slug"),
                "payTo": payto,
                "network": network,
                "price_usdc": price,
                "issues": issues,
            })

    gaps = []
    unverifiable = []
    for host in expected:
        lname = host.lower()
        if lname in catalog_host_set:
            continue
        h_status, _, h_err = http_get("https://%s/health" % host)
        m_status, m_raw, m_err = http_get("https://%s/.well-known/x402.json" % host)
        paytos = set()
        manifest_ok = False
        if m_status == 200:
            try:
                collect_payto(json.loads(m_raw.decode("utf-8", "replace")), paytos)
                manifest_ok = any(is_canonical_payto(p) for p in paytos)
            except Exception:
                manifest_ok = False
        if h_status == 200 and manifest_ok:
            gaps.append({
                "host": host,
                "health": h_status,
                "manifest_payto_canonical": True,
                "manifest_payTo_values": sorted(p for p in paytos if isinstance(p, str))[:4],
                "reason": "live canonical wall absent from /catalog.json",
            })
        else:
            unverifiable.append({
                "host": host,
                "health_status": h_status,
                "health_error": h_err,
                "manifest_status": m_status,
                "manifest_error": m_err,
                "manifest_payto_canonical": manifest_ok,
            })

    canonical_items = sum(1 for i in items if is_canonical_payto(i.get("payTo")))
    report = {
        "tool": "catalog-parity",
        "version": "1.0.0",
        "generated_utc": utcnow(),
        "catalog_url": args.catalog,
        "catalog_generated_utc": catalog.get("generated_utc"),
        "expected_source": expected_source,
        "catalog": {
            "wall_count": catalog.get("wall_count"),
            "endpoint_count": catalog.get("endpoint_count"),
            "distinct_hosts": len(catalog_hosts),
            "hosts": catalog_hosts,
            "canonical_paid_items": canonical_items,
        },
        "expected_host_count": len(expected),
        "discovery_gaps": gaps,
        "catalog_drift": drift,
        "unverifiable": unverifiable,
        "coverage_pct": round(100.0 * (len(expected) - len(gaps) - len(unverifiable)) / max(1, len(expected)), 1),
        "note": "Read-only. Unauthenticated GETs only; no signing, no X-PAYMENT, no money movement. "
                "Live manifest > catalog > this report. A gap is a discoverability defect, not a wall outage.",
    }
    text = json.dumps(report, indent=2, sort_keys=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    print(text)

    if args.fail_on_gap and (gaps or any(
        d.get("issues") and "free_route_null_payto" not in d["issues"] for d in drift
    )):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
