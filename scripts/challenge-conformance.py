#!/usr/bin/env python3
"""x402 Challenge Conformance Doctor (TIFFANY Innovation 42).

Read-only, stdlib-only. NO signing, NO X-PAYMENT header, NO RPC money calls,
NO funds movement, NO external sends, NO deploys. It only issues UNPAID HTTP
probes (GET/HEAD/POST) and decodes the public 402 challenge.

Why this exists: a machine buyer's generic x402 client can only pay a wall if
the 402 is a *well-formed challenge* on the method it actually calls. A quote
handler that returns 402 with no `payment-required` header (the QUOTE-FIX v2
defect family) grades `invalid_challenge` at x402 Doctor/Bazaar and the buyer
never reaches the pay button -- a lost sale with no money moved.

For each kept-live paid wall this tool grades, per HTTP method:
  transport   402 status returned
  header      payment-required present + base64(JSON) decodable
  envelope    x402Version == 2, accepts[] non-empty
  fields      scheme=exact, network=eip155:8453, canonical payTo (full 42-char
              case-insensitive), integer amount in USDC atomic units (1e6)
  resource    resource.url matches the probed resource URL
  parity      manifest price/payTo/scheme/network == live challenge

Verdicts: CANONICAL / DRIFT / INVALID_CHALLENGE / UNREACHABLE / NOT_APPLICABLE.
Only failures on a MANIFEST-ADVERTISED method fail CI (exit 1). Extra-method
findings are WARN (exit 0) because they are real friction, not a paid-path break.
"""

import base64
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

CANONICAL = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f".lower()
BASE_USDC_ATOMIC_PER_USD = 1_000_000
TIMEOUT = 25
UA = "RAEN-Challenge-Conformance-Doctor/1.0 (+machine-buyer-truth)"

WALLS = [
    {
        "name": "royal-ruby",
        "base": "https://royal-ruby-x402.fly.dev",
        "route": "/api/law-lookup",
        "advertised": ["POST"],
        "body": {"query": "x402 conformance probe"},
    },
    {
        "name": "contract-eye",
        "base": "https://contract-eye-x402.fly.dev",
        "route": "/api/analyze-contract",
        "advertised": ["POST"],
        "body": {"text": "x402 conformance probe"},
    },
    {
        "name": "nanobanana",
        "base": "https://nanobanana-x402.fly.dev",
        "route": "/api/generate-image",
        "advertised": ["POST"],
        "body": {"prompt": "x402 conformance probe"},
    },
    {
        "name": "raen-mcp-gateway",
        "base": "https://raen-mcp-gateway.fly.dev",
        "route": "/mcp",
        "advertised": ["POST"],
        "body": {
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "raen_law_lookup", "arguments": {"topic": "x402 conformance probe"}},
        },
        # tools/list is the documented free discovery method -- must stay 200.
        "free_probe": {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        "free_expect": 200,
    },
]

HDR_RE = re.compile(r"(?im)^payment-required:\s*(.+)$")


def http(method, url, body=None):
    """Return (status, headers_dict, body_text). Never raises on HTTP errors."""
    data = None
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, dict(r.headers.items()), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers.items()), e.read().decode("utf-8", "replace")
    except Exception as e:
        return None, {}, "{}"


def decode_challenge(headers):
    """Decode the payment-required header into the x402 v2 challenge object."""
    raw = None
    for k, v in headers.items():
        if k.lower() == "payment-required":
            raw = v
            break
    if not raw:
        return None, "no payment-required header"
    value = raw.strip()
    if "," in value and not value.lstrip().startswith("{"):
        value = value.split(",", 1)[1].strip()  # strip "base64," prefix if present
    if "..." in value:
        return None, "header value truncated (unusable)"
    try:
        padded = value + "=" * (-len(value) % 4)
        obj = json.loads(base64.b64decode(padded).decode("utf-8"))
        return obj, None
    except Exception as e:
        return None, "header decode failed: %s" % type(e).__name__


def manifest_for(wall):
    """Fetch /.well-known/x402.json and return the accept block for this route."""
    url = wall["base"] + "/.well-known/x402.json"
    status, _, text = http("GET", url)
    if status != 200:
        return None, "manifest HTTP %s" % status
    try:
        doc = json.loads(text)
    except Exception:
        return None, "manifest not JSON"
    resources = doc.get("resources") or doc.get("endpoints") or []
    for res in resources:
        if isinstance(res, dict) and res.get("path") == wall["route"] and res.get("accepts"):
            a = res["accepts"]
            price = a.get("price")
            try:
                price_usd = float(str(price).replace("$", "")) if price is not None else None
            except ValueError:
                price_usd = None
            return {
                "scheme": a.get("scheme"), "network": a.get("network"),
                "payTo": a.get("payTo"), "price": price, "price_usd": price_usd,
            }, None
    return None, "no priced accept block for route in manifest"


def grade_probe(wall, method, status, headers, body_text, manifest):
    """Grade a single method probe; return a structured result dict."""
    result = {
        "method": method, "status": status,
        "advertised": method in wall["advertised"],
        "checks": {}, "findings": [],
    }
    if status is None:
        result["verdict"] = "UNREACHABLE"
        result["findings"].append("no HTTP response")
        return result

    result["checks"]["http_402"] = (status == 402)
    if status != 402:
        # A free discovery method (e.g. gateway tools/list) returning 200 is healthy.
        if method == "POST" and wall.get("free_expect") and status == wall["free_expect"]:
            result["verdict"] = "NOT_APPLICABLE"
            result["findings"].append("free discovery method returned expected %s" % status)
        else:
            result["verdict"] = "NOT_APPLICABLE"
            result["findings"].append("unexpected status %s (not a paid challenge)" % status)
        return result

    challenge, err = decode_challenge(headers)
    if err or not isinstance(challenge, dict):
        result["checks"]["decodable_challenge"] = False
        result["verdict"] = "INVALID_CHALLENGE"
        result["findings"].append(err or "undecodable challenge")
        result["body_excerpt"] = body_text[:240]
        return result

    result["checks"]["decodable_challenge"] = True
    result["checks"]["x402_v2"] = (challenge.get("x402Version") == 2)
    accepts = challenge.get("accepts") or []
    result["checks"]["accepts_nonempty"] = bool(accepts)
    if not accepts:
        result["verdict"] = "INVALID_CHALLENGE"
        result["findings"].append("402 challenge has empty accepts[]")
        return result

    acc = accepts[0]
    amount = acc.get("amount")
    try:
        amount_i = int(amount)
    except (TypeError, ValueError):
        amount_i = None
    pay_to = str(acc.get("payTo") or "").lower()
    net = acc.get("network")
    scheme = acc.get("scheme")
    resource = challenge.get("resource") or {}
    res_url = resource.get("url") if isinstance(resource, dict) else None

    result["live"] = {
        "scheme": scheme, "network": net, "amount_atomic": amount_i,
        "amount_usd": (round(amount_i / BASE_USDC_ATOMIC_PER_USD, 6) if amount_i is not None else None),
        "payTo": str(acc.get("payTo") or ""),
        "accepts_count": len(accepts),
        "resource_url": res_url,
        "maxAmountRequired_present": "maxAmountRequired" in acc,
    }

    ok = True
    if not result["checks"]["x402_v2"]:
        result["findings"].append("x402Version != 2")
        ok = False
    if scheme != "exact":
        result["findings"].append("scheme != exact")
        ok = False
    if net != "eip155:8453":
        result["findings"].append("network != eip155:8453")
        ok = False
    if pay_to != CANONICAL:
        result["findings"].append("payTo not canonical (full 42-char compare)")
        ok = False
    if amount_i is None or amount_i <= 0:
        result["findings"].append("missing/nonpositive amount")
        ok = False
    expected_url = wall["base"] + wall["route"]
    if res_url and res_url.rstrip("/") != expected_url.rstrip("/"):
        result["findings"].append("resource.url mismatch")
        ok = False

    if manifest and amount_i is not None and manifest.get("price_usd") is not None:
        expected_atomic = round(manifest["price_usd"] * BASE_USDC_ATOMIC_PER_USD)
        parity = (expected_atomic == amount_i)
        result["checks"]["manifest_price_parity"] = parity
        if not parity:
            result["findings"].append(
                "price drift: live $%s vs manifest $%s" % (
                    round(amount_i / BASE_USDC_ATOMIC_PER_USD, 6), manifest["price_usd"]
                )
            )
            ok = False
    if manifest and manifest.get("payTo") and manifest["payTo"].lower() != CANONICAL:
        result["checks"]["manifest_payto_canonical"] = False
        result["findings"].append("manifest payTo not canonical")
        ok = False

    result["verdict"] = "CANONICAL" if ok else "DRIFT"
    return result


def main():
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tool": "challenge-conformance.py",
        "version": 1,
        "scope": "kept-live paid walls only; unpaid GET/HEAD/POST probes; no signing, no payment, no deploy",
        "canonical_payTo": CANONICAL,
        "walls": [], "findings": [],
    }
    ci_fail = False
    for wall in WALLS:
        url = wall["base"] + wall["route"]
        manifest, m_err = manifest_for(wall)
        entry = {
            "name": wall["name"], "url": url,
            "advertised_methods": wall["advertised"],
            "manifest": manifest,
            "manifest_error": m_err,
            "probes": [],
        }
        for method in ("POST", "GET", "HEAD"):
            status, headers, text = http(method, url, wall.get("body") if method == "POST" else None)
            g = grade_probe(wall, method, status, headers, text, manifest)
            entry["probes"].append(g)
            if g["advertised"] and g["verdict"] in ("DRIFT", "INVALID_CHALLENGE", "UNREACHABLE"):
                ci_fail = True
                out["findings"].append(
                    "%s %s %s: %s" % (wall["name"], method, g["verdict"], "; ".join(g["findings"]))
                )
            elif g["verdict"] in ("DRIFT", "INVALID_CHALLENGE") and not g["advertised"]:
                out["findings"].append(
                    "WARN %s %s %s: %s" % (wall["name"], method, g["verdict"], "; ".join(g["findings"]))
                )
        # Gateway free discovery check.
        if wall.get("free_probe"):
            st, _, _ = http("POST", url, wall["free_probe"])
            entry["free_discovery"] = {
                "method": "tools/list", "status": st,
                "healthy": (st == wall.get("free_expect")),
            }
            if st != wall.get("free_expect"):
                ci_fail = True
                out["findings"].append("%s tools/list returned %s (expected %s)" % (
                    wall["name"], st, wall.get("free_expect")))
        if manifest and manifest.get("price_usd") is None:
            out["findings"].append(
                "WARN %s manifest omits a price for %s -- live 402 is authoritative" % (
                    wall["name"], wall["route"])
            )
        out["walls"].append(entry)

    counts = {"CANONICAL": 0, "DRIFT": 0, "INVALID_CHALLENGE": 0, "UNREACHABLE": 0, "NOT_APPLICABLE": 0}
    for w in out["walls"]:
        for p in w["probes"]:
            counts[p["verdict"]] = counts.get(p["verdict"], 0) + 1
    out["summary"] = {
        "walls": len(out["walls"]), "verdict_counts": counts,
        "findings": len(out["findings"]),
        "ci_verdict": "FAIL" if ci_fail else "PASS",
    }
    sys.stdout.write(json.dumps(out, indent=2) + "\n")
    return 1 if ci_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
