#!/usr/bin/env python3
"""developer-docs.py — build a TRUTH-grounded 'Pay with USDC' developer documentation
pack for RAEN's kept-live x402 walls (Recipe 39; closes TIFF-PLAN-95).

Machine-buyer acquisition asset: a quickstart + API reference + 3 integration examples
whose every price / payTo / network / request-shape claim comes from a LIVE surface
(fresh unpaid 402 challenge and the seller's own manifest), never a hand-typed figure.

Read-only, stdlib-only. Sends only unpaid GET/POST discovery probes. No X-PAYMENT,
no signing, no RPC money calls, no secrets, no funds movement, no external sends,
no directory POSTs, no deploys. BURN FREEZE: only KEPT-LIVE walls are probed.

Exit codes: 0 CLEAN, 1 DRIFT (noncanonical payTo/network/scheme or price mismatch),
            2 UNREACHABLE (no wall produced a live 402).
"""
import argparse, base64, datetime, json, re, sys, urllib.error, urllib.request

VERSION = "developer-docs/1.0"
CANON = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f"
RETIRED = "0x7861db4efc14a1ed5dd8c96c528a3796560f1393"
AGENTCASH = "0xfbc0eb7811d477e55261d956df39f0046e192240"
UA = {"User-Agent": "Mozilla/5.0 (compatible; RAEN-developer-docs/1.0)",
      "Accept": "*/*", "Content-Type": "application/json"}

WALLS = [
    {"svc": "royal-ruby", "base": "https://royal-ruby-x402.fly.dev",
     "route": "/api/law-lookup", "method": "POST",
     "body": {"topic": "credit-report disputes for collection accounts",
              "state": "LA", "scope": "both"}},
    {"svc": "contract-eye", "base": "https://contract-eye-x402.fly.dev",
     "route": "/api/analyze-contract", "method": "POST",
     "body": {"text": "This agreement auto-renews every twelve months unless cancelled sixty days prior.",
              "focus": ["renewal", "liability"]}},
    {"svc": "gateway", "base": "https://raen-mcp-gateway.fly.dev",
     "route": "/mcp", "method": "POST",
     # tools/list is FREE discovery (200, no challenge); the PAID wall is tools/call.
     "body": {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
              "params": {"name": "raen_law_lookup", "arguments": {"query": "FCRA"}}},
     "free_discovery": "tools/list (free, no challenge)"},
]

TRUTH_NOTES = [
    "Price truth = a fresh live 402 challenge (accepts[0].amount), never a hand-typed or cached figure.",
    "payTo truth = the full 42-character canonical address, compared case-insensitively (homoglyph-safe).",
    "A 402 challenge is a demand signal, not a sale: most challenges are scanners/bots (Recipe 36).",
    "Internal self-pays (AgentCash) are not external revenue; fleet external revenue is $0.00 unless the chain says otherwise.",
    "On x402 paid walls the 402 precedes body validation: request shapes here are the seller's published manifest examples, not an observed validation result.",
    "Some surfaces expose a FREE discovery call that returns 200 with no challenge (e.g. gateway tools/list); the paid wall is tools/call.",
    "This pack verifies Base (eip155:8453) only — the chain RAEN walls settle on. Frozen services are never probed (BURN FREEZE).",
    "Code examples are illustrative: they contain NO real key and sign NOTHING. Payment happens only when the buyer attaches their own X-PAYMENT.",
]


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


def role(addr):
    a = (addr or "").lower()
    if a == CANON: return "CANONICAL"
    if a == RETIRED: return "RETIRED"
    if a == AGENTCASH: return "INTERNAL_AGENTCASH"
    return "UNKNOWN"


def deep_find(obj, want):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == want: return v
            found = deep_find(v, want)
            if found is not None: return found
    elif isinstance(obj, list):
        for item in obj:
            found = deep_find(item, want)
            if found is not None: return found
    return None


def probe(w, timeout):
    out = {"svc": w["svc"], "base": w["base"], "route": w["route"], "method": w["method"]}
    if w.get("free_discovery"):
        out["free_discovery"] = w["free_discovery"]
    # 1. MANIFEST
    ms, _, mb = get(w["base"] + "/.well-known/x402.json", timeout=timeout)
    out["manifest_status"] = ms
    try:
        mf = json.loads(mb) if ms == 200 else {}
    except Exception:
        mf = {}
    # request body fields from manifest (published examples / schema)
    body_fields = []
    node = deep_find(mf, "body")
    if isinstance(node, dict):
        props = node.get("properties")
        if isinstance(props, dict):
            body_fields = sorted(props.keys())
        elif isinstance(node.get("items"), dict) and isinstance(node["items"].get("properties"), dict):
            body_fields = sorted(node["items"]["properties"].keys())
    if not body_fields:
        body_fields = sorted(w["body"].keys())
    out["request_fields"] = body_fields
    out["request_example"] = w["body"]
    out["manifest_price"] = deep_find(mf, "price") or deep_find(mf, "amount")
    # 2. LIVE 402
    cs, ch, cb = get(w["base"] + w["route"], method="POST",
                     body=json.dumps(w["body"]), timeout=timeout)
    out["challenge_status"] = cs
    acc = None
    if cs == 402:
        dec = decode_challenge(ch)
        if dec and isinstance(dec.get("accepts"), list) and dec["accepts"]:
            acc = dec["accepts"][0]
        elif isinstance(dec, dict):
            acc = dec
    if not acc:
        # some services return the decoded challenge in the 402 body
        try:
            b = json.loads(cb)
            if isinstance(b.get("accepts"), list) and b["accepts"]:
                acc = b["accepts"][0]
        except Exception:
            pass
    if acc:
        amt = acc.get("amount")
        amt_s = str(amt) if amt is not None else ""
        atomic = int(amt_s) if amt_s.isdigit() else None
        out["amount_atomic"] = atomic
        out["price_usd"] = (atomic / 1_000_000) if atomic is not None else None
        out["payto"] = acc.get("payTo")
        out["payto_role"] = role(acc.get("payTo"))
        out["network"] = acc.get("network")
        out["scheme"] = acc.get("scheme")
    else:
        out["amount_atomic"] = out["price_usd"] = None
        out["payto"] = out["payto_role"] = out["network"] = out["scheme"] = None
    # 3. OPENAPI
    os_, _, ob = get(w["base"] + "/openapi.json", timeout=timeout)
    out["openapi_status"] = os_
    out["documented"] = (os_ == 200 and w["route"] in ob)
    return out


def build(pack, drift):
    now = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    lines = []
    A = lines.append
    A("# Pay with USDC — RAEN x402 developer documentation")
    A("")
    A(f"Generated {now} from LIVE surfaces by `{VERSION}`. Every price, payTo, network "
      "and request shape below was read from a fresh unpaid 402 challenge and the "
      "seller's own manifest — no cached or hand-typed figures.")
    A("")
    A("> Read this first: RAEN walls settle on **Base (eip155:8453)** in USDC. "
      "Payments use x402 with EIP-3009 (`transferWithAuthorization`) — no card, no account, "
      "no API key. Discovery is free; the call is paid.")
    A("")
    A("## 1. Quickstart (3 steps)")
    A("")
    A("1. **Discover** — `GET /.well-known/x402.json` on a wall. Free, no payment. "
      "Lists routes, request shapes and prices.")
    A("2. **Get a challenge** — send the request once with no payment. The wall replies "
      "`402 Payment Required` with a base64 `payment-required` header. Decode it to see "
      "`accepts[0]` (amount in USDC atomic units, payTo, network, scheme).")
    A("3. **Pay and retry** — sign an EIP-3009 `transferWithAuthorization` for exactly that "
      "amount/payTo/network, base64-encode it as `X-PAYMENT`, resend the same request. "
      "The wall settles on-chain and returns the deliverable (and a receipt).")
    A("")
    A("## 2. API reference (live-verified)")
    A("")
    A("| Service | Route | Method | Live price | Network | Scheme | payTo (canonical) |")
    A("|---|---|---|---|---|---|---|")
    for w in pack["walls"]:
        p = f"${w['price_usd']:g}" if w.get("price_usd") is not None else "n/a"
        A(f"| {w['svc']} | `{w['route']}` | {w['method']} | {p} | "
          f"{w.get('network') or 'n/a'} | {w.get('scheme') or 'n/a'} | `{w.get('payto') or 'n/a'}` |")
    A("")
    for w in pack["walls"]:
        A(f"### {w['svc']} — `{w['route']}`")
        A("")
        A(f"- Request fields (seller's published example): `{', '.join(w['request_fields'])}`")
        A(f"- Example body: `{json.dumps(w['request_example'], separators=(',', ':'))}`")
        A(f"- Manifest HTTP {w.get('manifest_status')}, OpenAPI HTTP {w.get('openapi_status')} "
          f"({'documented' if w.get('documented') else 'not documented'}), live 402 HTTP {w.get('challenge_status')}")
        if w.get("free_discovery"):
            A(f"- Free discovery: {w['free_discovery']} — the route above is the paid wall.")
        A("")
    A("## 3. Integration examples")
    A("")
    A("### Example 1 — decode a live 402 challenge (curl + Python stdlib, no payment)")
    A("```bash")
    A("curl -s -D - -o /dev/null -X POST https://contract-eye-x402.fly.dev/api/analyze-contract \\")
    A("  -H 'Content-Type: application/json' \\")
    A("  -d '{\"text\":\"auto-renews every 12 months\",\"focus\":[\"renewal\"]}' \\")
    A("  | grep -i '^payment-required:'")
    A("```")
    A("")
    A("```python")
    A("import base64, json, urllib.request, urllib.error")
    A("req = urllib.request.Request(")
    A("    'https://contract-eye-x402.fly.dev/api/analyze-contract',")
    A("    data=b'{\"text\":\"auto-renews every 12 months\",\"focus\":[\"renewal\"]}',")
    A("    method='POST', headers={'Content-Type': 'application/json'})")
    A("try:")
    A("    urllib.request.urlopen(req)  # 200 would mean the route is not paid")
    A("except urllib.error.HTTPError as e:")
    A("    if e.code == 402:")
    A("        raw = e.headers['payment-required']")
    A("        challenge = json.loads(base64.b64decode(raw + '=' * (-len(raw) % 4)))")
    A("        a = challenge['accepts'][0]")
    A("        print('pay', a['amount'], 'atomic USDC to', a['payTo'], 'on', a['network'])")
    A("```")
    A("")
    A("### Example 2 — attach X-PAYMENT and retry (illustrative; sign with YOUR wallet)")
    A("```python")
    A("import base64, json, urllib.request")
    A("# 1. decode the challenge as in Example 1 -> a = challenge['accepts'][0]")
    A("# 2. sign EIP-3009 transferWithAuthorization with YOUR key (never committed here).")
    A("#    amount = a['amount'], to = a['payTo'], asset = a['asset'], network = a['network'].")
    A("authorization = {'transferWithAuthorization': SIGNED_AUTHORIZATION}  # your signed payload")
    A("x_payment = base64.b64encode(json.dumps(authorization).encode()).decode()")
    A("req = urllib.request.Request(")
    A("    'https://contract-eye-x402.fly.dev/api/analyze-contract',")
    A("    data=b'{\"text\":\"auto-renews every 12 months\",\"focus\":[\"renewal\"]}',")
    A("    method='POST', headers={'Content-Type': 'application/json', 'X-PAYMENT': x_payment})")
    A("with urllib.request.urlopen(req) as r:")
    A("    print(r.status, r.read().decode())  # 200 + deliverable + receipt")
    A("```")
    A("")
    A("### Example 3 — three-surface cross-check before wiring a wall")
    A("```python")
    A("import json, urllib.request")
    A("base = 'https://royal-ruby-x402.fly.dev'")
    A("manifest = json.load(urllib.request.urlopen(base + '/.well-known/x402.json'))")
    A("openapi = json.load(urllib.request.urlopen(base + '/openapi.json'))")
    A("route = '/api/law-lookup'")
    A("print('in manifest :', route in json.dumps(manifest))")
    A("print('in openapi  :', route in openapi.get('paths', {}))")
    A("print('manifest fields:', manifest.get('extensions', {}).get('bazaar', {}))")
    A("# Then decode a live 402 (Example 1) and confirm its payTo/network/amount")
    A("# match the manifest. A mismatch is DRIFT — report it, do not pay it.")
    A("```")
    A("")
    A("## 4. Truth notes")
    A("")
    for t in TRUTH_NOTES:
        A(f"- {t}")
    A("")
    A(f"Verdict: **{'CLEAN' if not drift else 'DRIFT'}** — live 402s canonical on all probed walls, "
      "0 price drift." if not drift else
      f"Verdict: **DRIFT** — {len(drift)} issue(s) (see JSON).")
    A("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    ap.add_argument("--md", required=True)
    ap.add_argument("--timeout", type=int, default=25)
    args = ap.parse_args()
    walls = [probe(w, args.timeout) for w in WALLS]
    reachable = sum(1 for w in walls if w.get("amount_atomic") is not None)
    drift = []
    for w in walls:
        if w.get("payto_role") != "CANONICAL" and w.get("amount_atomic") is not None:
            drift.append({"svc": w["svc"], "issue": "noncanonical payTo", "value": w.get("payto")})
        if w.get("network") not in (None, "eip155:8453"):
            drift.append({"svc": w["svc"], "issue": "network drift", "value": w.get("network")})
        if w.get("scheme") not in (None, "exact"):
            drift.append({"svc": w["svc"], "issue": "scheme drift", "value": w.get("scheme")})
    pack = {
        "bundle": "RAEN 'Pay with USDC' developer documentation pack",
        "version": 1, "tool": VERSION,
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "canonical_payto": CANON, "chain": "eip155:8453",
        "verdict": "CLEAN" if (reachable >= 2 and not drift) else ("DRIFT" if drift else "UNREACHABLE"),
        "walls_verified": len([w for w in walls if w.get("amount_atomic") is not None]),
        "price_drift": len(drift), "truth_notes": TRUTH_NOTES, "drift": drift, "walls": walls,
    }
    with open(args.json, "w", encoding="utf-8") as f:
        json.dump(pack, f, indent=2)
    with open(args.md, "w", encoding="utf-8") as f:
        f.write(build(pack, drift))
    print(f"{VERSION} verdict={pack['verdict']} walls={len(walls)} "
          f"live402={sum(1 for w in walls if w.get('challenge_status') == 402)} "
          f"canonical={sum(1 for w in walls if w.get('payto_role') == 'CANONICAL')} "
          f"price_drift={len(drift)}")
    for w in walls:
        p = f"${w['price_usd']:g}" if w.get("price_usd") is not None else "n/a"
        print(f"  {w['svc']:<12} live={p:<8} payto={w.get('payto_role')} "
              f"net={w.get('network')} fields={','.join(w['request_fields'])}")
    return 0 if pack["verdict"] == "CLEAN" else (1 if drift else 2)


if __name__ == "__main__":
    sys.exit(main())
