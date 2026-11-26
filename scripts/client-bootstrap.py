#!/usr/bin/env python3
"""Innovation 44 - Machine-Buyer Client Bootstrap (stdlib, read-only).

The cookbook's other 43 tools grade stages of the buyer journey (discovery,
catalog, challenge shape, trust, receipt, readiness). This one closes the LAST
mile: it turns each kept-live wall into ready-to-paste client code that an
autonomous agent can run to complete a first purchase.

Every value in the emitted snippet is LIVE-READ from an unpaid 402 challenge -
price, network, scheme, canonical payTo, request body. The tool itself NEVER
signs, NEVER sends X-PAYMENT, NEVER makes an RPC money call, NEVER moves funds,
NEVER uses a key, NEVER posts to a directory and NEVER deploys. The generated
code contains a signing stub that raises until the buyer plugs in their OWN
wallet signer. BURN FREEZE respected: only kept-live walls are probed.

Outputs registry/client-bootstrap.json (live snapshot) and
registry/client-bootstrap.md (buyer copy with the runnable skeleton).

Exit 0 = every probed wall canonical; 1 = a canonical break; 2 = none reachable.
"""

import argparse
import base64
import datetime
import json
import sys
import urllib.error
import urllib.request

VERSION = "client-bootstrap/1.0"
CANON = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f"
BASE_NETWORK = "eip155:8453"
ATOMIC = 1_000_000

# Kept-live walls only. Unpaid POST to the paid route - the exact probes used
# by the conformance doctor and the readiness scorecard (Innovation 42/43).
WALLS = [
    {"name": "royal-ruby", "base": "https://royal-ruby-x402.fly.dev",
     "route": "/api/law-lookup", "method": "POST",
     "body": {"query": "x402 bootstrap probe"}},
    {"name": "contract-eye", "base": "https://contract-eye-x402.fly.dev",
     "route": "/api/analyze-contract", "method": "POST",
     "body": {"text": "x402 bootstrap probe"}},
    {"name": "nanobanana", "base": "https://nanobanana-x402.fly.dev",
     "route": "/api/generate-image", "method": "POST",
     "body": {"prompt": "x402 bootstrap probe"}},
    {"name": "raen-mcp-gateway", "base": "https://raen-mcp-gateway.fly.dev",
     "route": "/mcp", "method": "POST",
     "body": {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
              "params": {"name": "raen_law_lookup",
                         "arguments": {"topic": "x402 bootstrap probe"}}}},
]

UA = {"User-Agent": "Mozilla/5.0 (compatible; RAEN-client-bootstrap/1.0)",
      "Accept": "application/json"}


def http(method, url, body=None, headers=None, timeout=20):
    hdr = dict(headers or {})
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        hdr.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=hdr, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers.items()), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers.items()), e.read().decode("utf-8", "replace")
    except Exception as e:
        return None, {}, "error: %s" % type(e).__name__


def canon(addr):
    return isinstance(addr, str) and addr.lower() == CANON.lower()


def decode_challenge(headers):
    raw = None
    for k, v in headers.items():
        if k.lower() in ("payment-required", "x-payment-required"):
            raw = v
            break
    if not raw:
        return None, "no payment-required header"
    if "," in raw and not raw.lstrip().startswith("{"):
        raw = raw.split(",", 1)[1].strip()
    if "..." in raw:
        return None, "header truncated"
    try:
        obj = json.loads(base64.b64decode(raw + "=" * (-len(raw) % 4)).decode("utf-8"))
    except Exception as e:
        return None, "header decode failed: %s" % type(e).__name__
    accepts = obj.get("accepts") or []
    if not isinstance(accepts, list) or not accepts:
        return None, "empty accepts[]"
    return obj, None


def probe(wall):
    url = wall["base"] + wall["route"]
    status, headers, _ = http(wall["method"], url, wall.get("body"), UA)
    out = {"name": wall["name"], "url": url, "method": wall["method"],
           "request_body": wall.get("body"), "http_status": status,
           "canonical": False}
    if status != 402:
        out["detail"] = "expected 402, got %s" % status
        return out
    obj, err = decode_challenge(headers)
    if obj is None or err:
        out["detail"] = err or "undecodable challenge"
        return out
    acc = (obj.get("accepts") or [{}])[0]
    if not isinstance(acc, dict):
        acc = {}
    payto, scheme, net = acc.get("payTo"), acc.get("scheme"), acc.get("network")
    raw_amt = acc.get("amount")
    try:
        amt = int(raw_amt) if raw_amt is not None else None
    except (TypeError, ValueError):
        amt = None
    checks = {
        "v2": obj.get("x402Version") == 2,
        "scheme": scheme == "exact",
        "network": net == BASE_NETWORK,
        "payTo": canon(payto),
        "amount": amt is not None and amt > 0,
    }
    out.update(
        x402Version=obj.get("x402Version"), scheme=scheme, network=net,
        payTo=payto, amount_atomic=amt, asset=acc.get("asset"),
        amount_usd=(round(amt / ATOMIC, 6) if amt is not None else None),
        checks=checks, canonical=all(checks.values()),
        detail=("canonical" if all(checks.values()) else
                "failed: " + ",".join(k for k, ok in checks.items() if not ok)),
    )
    return out


SKEL = r'''#!/usr/bin/env python3
# RAEN client bootstrap - generated live KEYWORDS, stdlib only.
# Every price/payTo/network below is a LIVE-READ fact from an unpaid 402.
# This skeleton NEVER signs and NEVER spends on its own: step 2 calls a stub you
# must replace with YOUR wallet's x402 signer. Verify payTo before paying.
import json, base64, urllib.request, urllib.error

CANON = "CANON_PLACEHOLDER"
WALLS = WALLS_PLACEHOLDER


def unpaid(choice):
    """Step 1 - unpaid call. The seller's 402 challenge is the source of truth."""
    w = WALLS[choice]
    req = urllib.request.Request(
        w["url"], data=json.dumps(w["body"]).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "User-Agent": "raen-client-bootstrap/1.0"},
        method=w["method"])
    try:
        urllib.request.urlopen(req, timeout=20)
        raise RuntimeError("expected a 402 challenge, got 2xx (is this route free?)")
    except urllib.error.HTTPError as e:
        if e.code != 402:
            raise
        raw = (e.headers.get("payment-required")
               or e.headers.get("x-payment-required") or "")
        if "," in raw and not raw.lstrip().startswith("{"):
            raw = raw.split(",", 1)[1].strip()
        obj = json.loads(base64.b64decode(raw + "=" * (-len(raw) % 4)))
        return obj, w


def build_payment_header(challenge):
    """Step 2a - build the X-PAYMENT payload. YOU supply the signature.

    The RAEN bootstrap tool never signs and never touches a wallet. Plug in an
    x402 signer (EIP-3009 transferWithAuthorization on Base) that produces the
    base64 header the seller's accepts[] entry describes.
    """
    a = challenge["accepts"][0]
    assert a["payTo"].lower() == CANON.lower(), "NON-CANONICAL payTo - DO NOT PAY"
    assert a["scheme"] == "exact" and a["network"] == "eip155:8453", "wrong scheme/network"
    assert int(a["amount"]) > 0, "invalid amount"
    # TODO: sign with YOUR wallet. Return the base64 X-PAYMENT header string.
    raise NotImplementedError("connect your own x402 signer (EIP-3009 on Base)")


def paid(choice):
    """Step 2b - retry with the signed header and read the deliverable."""
    challenge, w = unpaid(choice)
    header = build_payment_header(challenge)  # base64 X-PAYMENT from your signer
    req = urllib.request.Request(
        w["url"], data=json.dumps(w["body"]).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-PAYMENT": header},
        method=w["method"])
    return urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")


if __name__ == "__main__":
    import sys
    choice = sys.argv[1] if len(sys.argv) > 1 else "royal-ruby"
    print(paid(choice))
'''


def render_md(rows, generated_at):
    L = []
    A = L.append
    A("# Machine-Buyer Client Bootstrap")
    A("")
    A("Generated %s - %s. Every URL, price, payTo and network below is a LIVE-READ "
      "fact from an unpaid 402 challenge. No funds were moved to produce this." % (generated_at, VERSION))
    A("")
    A("| Wall | Endpoint | Live price | Network | Scheme | Canonical payTo |")
    A("|---|---|---|---|---|---|")
    for r in rows:
        price = ("$%.4f" % r["amount_usd"]) if r.get("amount_usd") is not None else "n/a"
        A("| %s | `%s %s` | %s | %s | %s | %s |" % (
            r["name"], r["method"], r["url"], price,
            r.get("network", "?"), r.get("scheme", "?"),
            "yes" if r.get("checks", {}).get("payTo") else "NO - DO NOT PAY"))
    A("")
    A("## Four-step flow (the only part a buyer must supply is their own signature)")
    A("")
    A("1. **Unpaid call** -> receive the 402 `payment-required` header (base64 JSON).")
    A("2. **Decode** `accepts[0]`: `scheme`, `network`, `payTo`, `amount` (atomic USDC, 6 dp).")
    A("3. **Preflight assert** `payTo` equals the full canonical address (case-insensitive), "
      "`scheme=exact`, `network=eip155:8453`, `amount>0`. Never pay a lookalike.")
    A("4. **Sign with YOUR wallet** (EIP-3009 on Base) -> base64 `X-PAYMENT` -> retry the call. "
      "The bootstrap tool never signs; the skeleton below raises until you plug in a signer.")
    A("")
    A("## Run-ready skeleton (stdlib; replace the signing stub)")
    A("")
    A("```python")
    A(SKEL)
    A("```")
    A("")
    A("Canonical payTo: `%s`. A wall whose `Canonical payTo` column reads NO is a "
      "payment-path break - do not pay it; the live 402 of a canonical wall is always "
      "authoritative over any hand-maintained price table." % CANON)
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-json", default=None)
    ap.add_argument("--out-md", default=None)
    a = ap.parse_args()
    rows = [probe(w) for w in WALLS]
    generated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    breaks = [r for r in rows if not r.get("canonical")]
    reachable = [r for r in rows if r.get("http_status") is not None]
    walls_pub = {r["name"]: {
        "url": r["url"], "method": r["method"], "request_body": r.get("request_body"),
        "http_status": r.get("http_status"), "live_price_usd": r.get("amount_usd"),
        "amount_atomic": r.get("amount_atomic"), "asset": r.get("asset"),
        "scheme": r.get("scheme"), "network": r.get("network"),
        "payTo": r.get("payTo"), "canonical": r.get("canonical"),
        "checks": r.get("checks"), "detail": r.get("detail"),
    } for r in rows}
    report = {
        "version": VERSION, "generated_at": generated_at,
        "scope": "kept-live walls only; unpaid POST; no signing, no X-PAYMENT, no funds, no deploy",
        "canonical_payTo": CANON,
        "walls": walls_pub,
        "summary": {"total": len(rows),
                    "canonical": sum(1 for r in rows if r.get("canonical")),
                    "breaks": len(breaks)},
        "verdict": ("CANONICAL_BREAK" if breaks else
                    ("NO_WALL_REACHABLE" if not reachable else "OK")),
    }
    body = json.dumps(report, indent=2)
    skel = (SKEL.replace("CANON_PLACEHOLDER", CANON)
                .replace("WALLS_PLACEHOLDER",
                         json.dumps(walls_pub, indent=2)))
    if a.out_json:
        open(a.out_json, "w", encoding="utf-8").write(body + "\n")
    if a.out_md:
        md = render_md(rows, generated_at).replace(SKEL, skel)
        open(a.out_md, "w", encoding="utf-8").write(md)
    print(json.dumps({"verdict": report["verdict"], "summary": report["summary"],
                      "walls": {r["name"]: {"price": r.get("amount_usd"),
                                            "canonical": r.get("canonical"),
                                            "detail": r.get("detail")} for r in rows}}, indent=2))
    if breaks:
        return 1
    if not reachable:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
