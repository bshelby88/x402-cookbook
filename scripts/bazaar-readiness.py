#!/usr/bin/env python3
"""Bazaar readiness auditor - READ-ONLY.

Answers one buyer-discovery question with live evidence:
    "Can an autonomous agent index and actually call this x402 endpoint?"

A static .well-known/x402.json can advertise a paywall that agent directories
cannot index: no extensions.bazaar, no input.method, or an empty example body.
This tool reads the manifest as served, checks the exact fields discovery
requires, and emits a ready-to-POST 402index-style registration payload.

It never signs, never POSTs, never spends, never mutates a service.

Usage:
    python3 scripts/bazaar-readiness.py royal-ruby-x402 contract-eye-x402
    python3 scripts/bazaar-readiness.py --host contract-eye-x402 --pretty

Exit codes: 0 audited (gaps reported), 2 transport failure on every host.
"""
import argparse
import json
import subprocess
import sys

CANONICAL_PAYTO = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f"
VALID_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}
MANIFEST_PATH = "/.well-known/x402.json"


def normalize_host(host):
    return host if "." in host else host + ".fly.dev"


def fetch(host, timeout=15):
    url = "https://" + normalize_host(host) + MANIFEST_PATH
    try:
        p = subprocess.run(
            ["curl", "-s", "-m", str(timeout), url],
            capture_output=True, text=True, timeout=timeout + 5,
        )
        if p.returncode != 0:
            return None, "curl exit " + str(p.returncode)
        if not p.stdout.strip():
            return None, "empty body (host suspended or unreachable)"
        return json.loads(p.stdout), None
    except Exception as exc:  # noqa: BLE001 - report, never crash the sweep
        return None, str(exc)[:160]


def audit_endpoint(url_path, ep):
    accepts = ep.get("accepts") or {}
    bazaar = (ep.get("extensions") or {}).get("bazaar") or {}
    info = bazaar.get("info") or {}
    inp = info.get("input") or {}
    body = inp.get("body")
    method = inp.get("method")

    gaps = []
    scheme = str(accepts.get("scheme", ""))
    network = str(accepts.get("network", ""))
    payto = str(accepts.get("payTo", ""))
    if scheme != "exact":
        gaps.append("scheme!=exact:" + (scheme or "missing"))
    if network != "eip155:8453":
        gaps.append("network!=eip155:8453:" + (network or "missing"))
    if payto.lower() != CANONICAL_PAYTO:
        gaps.append("payTo!=canonical:" + (payto or "missing"))
    if not bazaar:
        gaps.append("missing extensions.bazaar")
    if method not in VALID_METHODS:
        gaps.append("missing/invalid input.method:" + (str(method) or "missing"))
    if not isinstance(body, dict) or not body:
        gaps.append("empty example body")

    # A complete bazaar block is what agent indexes need to reach the 402,
    # not a 400. probe_body mirrors the advertised example body.
    payload = None
    if not gaps:
        payload = {
            "url": url_path,
            "http_method": method,
            "probe_body": body,
            "price_usd": accepts.get("price") or accepts.get("amount"),
            "payment_asset": "USDC",
            "payment_network": "Base",
        }
    return {
        "endpoint": url_path,
        "readiness": "READY" if not gaps else "GAP",
        "gaps": gaps,
        "price": accepts.get("price"),
        "method": method,
        "registration_payload": payload,
    }


def audit_host(host):
    manifest, err = fetch(host)
    if err or manifest is None:
        return {"host": host, "status": "UNREACHABLE", "reason": err or "empty manifest",
                "endpoints": [], "ready": 0, "total": 0}
    eps = manifest.get("endpoints") or {}
    results = []
    for path, ep in eps.items():
        url = "https://" + normalize_host(host) + (path if path.startswith("/") else "/" + path)
        results.append(audit_endpoint(url, ep))
    ready = sum(1 for r in results if r["readiness"] == "READY")
    return {"host": host, "status": "OK", "reason": None,
            "endpoints": results, "ready": ready, "total": len(results)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("hosts", nargs="*", help="Fly hostnames WITHOUT .fly.dev")
    ap.add_argument("--host", action="append", default=[],
                    help="repeatable single-host flag")
    ap.add_argument("--pretty", action="store_true")
    args = ap.parse_args()
    hosts = list(dict.fromkeys(args.hosts + args.host))
    if not hosts:
        ap.error("pass at least one host")
    report = [audit_host(h) for h in hosts]
    json.dump(report, sys.stdout, indent=2 if args.pretty else None)
    sys.stdout.write("\n")
    if all(r["status"] == "UNREACHABLE" for r in report):
        sys.exit(2)


if __name__ == "__main__":
    main()
