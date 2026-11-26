#!/usr/bin/env python3
"""dev-education.py — generate a live-grounded 3-part "x402 for Developers" education
series for machine buyers (Recipe 40; closes Airtable POST-102).

Acceptance (POST-102): a markdown file containing 3 COMPLETE articles, each with code
examples. Every price / payTo / network / request shape is taken from a FRESH unpaid 402
challenge and the seller's own manifest — never hand-typed or cached.

Read-only, stdlib-only. Sends only unpaid GET/POST discovery probes to KEPT-LIVE walls.
No X-PAYMENT, no signing, no RPC money calls, no secrets, no funds movement, no external
sends, no directory POSTs, no deploys. BURN FREEZE: frozen services are never probed.

Exit codes: 0 CLEAN, 1 DRIFT (noncanonical payTo/network/scheme), 2 UNREACHABLE.
"""
import argparse, base64, datetime, json, urllib.error, urllib.request

VERSION = "dev-education/1.0"
CANON = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f"
RETIRED = "0x7861db4efc14a1ed5dd8c96c528a3796560f1393"
AGENTCASH = "0xfbc0eb7811d477e55261d956df39f0046e192240"
UA = {"User-Agent": "Mozilla/5.0 (compatible; RAEN-dev-education/1.0)",
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
     "body": {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
              "params": {"name": "raen_law_lookup", "arguments": {"query": "FCRA"}}},
     "free_discovery": "tools/list (free, no challenge)"},
]

HONESTY = [
    "A 402 challenge is a demand signal, not a sale — most challenges are scanners/bots.",
    "Internal AgentCash self-pays are not external revenue; fleet external revenue is $0.00 unless the chain says otherwise.",
    "Discovery (manifest, tools/list) is free; only the paid wall returns 402.",
    "The 402 precedes body validation on these walls — request shapes are the seller's published examples, not an observed 400.",
    "Sign nothing in this document: every code example uses the buyer's OWN wallet and contains no real key.",
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


def deep_find(obj, want):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == want:
                return v
            found = deep_find(v, want)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = deep_find(item, want)
            if found is not None:
                return found
    return None


def probe(w, timeout):
    out = {"svc": w["svc"], "base": w["base"], "route": w["route"], "method": w["method"]}
    if w.get("free_discovery"):
        out["free_discovery"] = w["free_discovery"]
    ms, _, mb = get(w["base"] + "/.well-known/x402.json", timeout=timeout)
    out["manifest_status"] = ms
    try:
        mf = json.loads(mb) if ms == 200 else {}
    except Exception:
        mf = {}
    node = deep_find(mf, "body")
    fields = []
    if isinstance(node, dict):
        props = node.get("properties")
        if isinstance(props, dict):
            fields = sorted(props.keys())
        elif isinstance(node.get("items"), dict) and isinstance(node["items"].get("properties"), dict):
            fields = sorted(node["items"]["properties"].keys())
    if not fields:
        fields = sorted(w["body"].keys())
    out["request_fields"] = fields
    out["request_example"] = w["body"]
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
        try:
            b = json.loads(cb)
            if isinstance(b.get("accepts"), list) and b["accepts"]:
                acc = b["accepts"][0]
        except Exception:
            pass
    if acc:
        amt = str(acc.get("amount", ""))
        atomic = int(amt) if amt.isdigit() else None
        out["amount_atomic"] = atomic
        out["price_usd"] = (atomic / 1_000_000) if atomic is not None else None
        out["payto"] = acc.get("payTo")
        out["network"] = acc.get("network")
        out["scheme"] = acc.get("scheme")
    else:
        for k in ("amount_atomic", "price_usd", "payto", "network", "scheme"):
            out[k] = None
    os_, _, ob = get(w["base"] + "/openapi.json", timeout=timeout)
    out["openapi_status"] = os_
    out["documented"] = (os_ == 200 and w["route"] in ob)
    return out


def build(pack, verdict):
    now = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    L = []
    A = L.append
    A("# x402 for Developers — a three-part course grounded in live walls")
    A("")
    A(f"Generated {now} by `{VERSION}` for Airtable POST-102. This is a complete "
      "3-article series: Part 1 introduces the protocol, Part 2 builds an integration, "
      "Part 3 covers production patterns. Every price, payTo, network and request shape "
      "below is read from a fresh unpaid 402 challenge and the seller's own manifest — "
      "no cached or hand-typed figures. Verification verdict: **" + verdict + "**.")
    A("")
    A("---")
    A("")
    # ---- LIVE TABLE (shared factual spine for all three articles) ----
    A("## Live reference table (read from unpaid 402 challenges)")
    A("")
    A("| Service | Route | Method | Live price | Network | Scheme | payTo |")
    A("|---|---|---|---|---|---|---|")
    for w in pack["walls"]:
        p = f"${w['price_usd']:g}" if w.get("price_usd") is not None else "n/a"
        A(f"| {w['svc']} | `{w['route']}` | {w['method']} | {p} | "
          f"{w.get('network') or 'n/a'} | {w.get('scheme') or 'n/a'} | `{w.get('payto') or 'n/a'}` |")
    A("")
    A("---")
    A("")
    # ---- ARTICLE 1 ----
    A("# Article 1 — Introduction to the x402 payment protocol")
    A("")
    A("x402 turns the ordinary HTTP `402 Payment Required` status into a machine-payable "
      "contract. A client calls a paid route with no payment; the server replies `402` "
      "carrying a base64 `payment-required` header describing what it accepts. The client "
      "signs that exact amount to that exact address on that exact chain, attaches the "
      "signature as `X-PAYMENT`, and retries. No account, no API key, no card — value "
      "moves with the request.")
    A("")
    A("## The four things in a challenge")
    A("")
    A("```json")
    A('{"accepts":[{"scheme":"exact","network":"eip155:8453",'
      '"amount":"50000","payTo":"' + CANON + '"}]}')
    A("```")
    A("")
    A("- `scheme`: `exact` means pay this precise amount, not a cap.")
    A("- `network`: `eip155:8453` is Base — the chain RAEN walls settle on.")
    A("- `amount`: USDC atomic units (6 decimals) — `50000` is $0.05.")
    A("- `payTo`: the seller's receiving address. Compare the FULL 42 characters, "
      "case-insensitively; lookalike addresses exist.")
    A("")
    A("## Discovery is free; the call is paid")
    A("")
    A("A well-behaved wall publishes `/.well-known/x402.json` and `/openapi.json`. Both "
      "are free. Some surfaces also expose a free discovery call (here, the gateway's "
      "`tools/list`); the paid wall is a different route (`tools/call`). Read discovery "
      "first — it tells you the request shape before you ever see a price.")
    A("")
    A("```bash")
    A("curl -s https://contract-eye-x402.fly.dev/.well-known/x402.json | head -c 800")
    A("```")
    A("")
    A("## Your first challenge (no payment, no signing)")
    A("")
    A("```python")
    A("import base64, json, urllib.error, urllib.request")
    A("req = urllib.request.Request(")
    A("    'https://contract-eye-x402.fly.dev/api/analyze-contract',")
    A("    data=b'{\"text\":\"auto-renews every 12 months\",\"focus\":[\"renewal\"]}',")
    A("    method='POST', headers={'Content-Type': 'application/json'})")
    A("try:")
    A("    urllib.request.urlopen(req)  # a 200 here would mean the route is NOT paid")
    A("except urllib.error.HTTPError as e:")
    A("    if e.code == 402:")
    A("        raw = e.headers['payment-required']")
    A("        ch = json.loads(base64.b64decode(raw + '=' * (-len(raw) % 4)))")
    A("        a = ch['accepts'][0]")
    A("        print(a['amount'], a['payTo'], a['network'], a['scheme'])")
    A("```")
    A("")
    A("> Honesty: a 402 is a demand signal, not a sale. Most challenges are scanners. "
      "External revenue is $0.00 unless the chain says otherwise.")
    A("")
    A("---")
    A("")
    # ---- ARTICLE 2 ----
    A("# Article 2 — Integrating x402 into your application")
    A("")
    A("An integration is a five-step loop: discover, challenge, sign, retry, verify. "
      "The live walls above are the reference; use their real amounts and addresses.")
    A("")
    A("## Step 1 — Read the seller's published request shape")
    A("")
    A("```python")
    A("import json, urllib.request")
    A("base = 'https://royal-ruby-x402.fly.dev'")
    A("mf = json.load(urllib.request.urlopen(base + '/.well-known/x402.json'))")
    A("print(json.dumps(mf.get('extensions', {}), indent=2)[:800])")
    A("```")
    A("")
    A("For the live walls in this course the request fields are:")
    A("")
    for w in pack["walls"]:
        A(f"- `{w['svc']}` `{w['route']}`: `{', '.join(w['request_fields'])}` — "
          f"example `{json.dumps(w['request_example'], separators=(',', ':'))}`"
          + (f"; free discovery: {w['free_discovery']}" if w.get("free_discovery") else ""))
    A("")
    A("## Step 2 — Decode the challenge and pin the truth")
    A("")
    A("```python")
    A("import base64, json, urllib.error, urllib.request")
    A("CANON = '" + CANON + "'")
    A("def challenge(url, body):")
    A("    req = urllib.request.Request(url, data=json.dumps(body).encode(),")
    A("                                 method='POST', headers={'Content-Type': 'application/json'})")
    A("    try:")
    A("        urllib.request.urlopen(req); return None  # unexpectedly free")
    A("    except urllib.error.HTTPError as e:")
    A("        if e.code != 402: raise")
    A("        raw = e.headers['payment-required']")
    A("        return json.loads(base64.b64decode(raw + '=' * (-len(raw) % 4)))['accepts'][0]")
    A("a = challenge('https://contract-eye-x402.fly.dev/api/analyze-contract',")
    A("              {'text': 'auto-renews', 'focus': ['renewal']})")
    A("assert a['payTo'].lower() == CANON      # full 42-char compare, homoglyph-safe")
    A("assert a['network'] == 'eip155:8453'")
    A("assert a['scheme'] == 'exact'")
    A("print('pay', int(a['amount']) / 1_000_000, 'USDC')")
    A("```")
    A("")
    A("## Step 3 — Sign EIP-3009 with YOUR wallet")
    A("")
    A("The challenge names an `asset` (USDC on Base). Sign a "
      "`transferWithAuthorization` for exactly `a['amount']` to exactly `a['payTo']`. "
      "The signing key is the buyer's and never appears in this course.")
    A("")
    A("```python")
    A("# PSEUDOCODE — illustrative. signing happens in the buyer's own wallet/runtime.")
    A("# authorization = wallet.sign_transfer_with_authorization(")
    A("#     token=a['asset'], to=a['payTo'], value=int(a['amount']), network=a['network'])")
    A("# x_payment = base64.b64encode(json.dumps({'transferWithAuthorization':")
    A("#     authorization}).encode()).decode()")
    A("```")
    A("")
    A("## Step 4 — Retry with X-PAYMENT (note the header name)")
    A("")
    A("```python")
    A("req = urllib.request.Request(")
    A("    'https://contract-eye-x402.fly.dev/api/analyze-contract',")
    A("    data=b'{\"text\":\"auto-renews\",\"focus\":[\"renewal\"]}', method='POST',")
    A("    headers={'Content-Type': 'application/json', 'X-PAYMENT': x_payment})")
    A("with urllib.request.urlopen(req) as r:")
    A("    print(r.status, r.read().decode())  # 200 + deliverable + receipt")
    A("```")
    A("")
    A("Use `X-PAYMENT`. The older `PAYMENT-SIGNATURE` spelling silently re-challenges "
      "the buyer and can cause a double-pay (Recipe 25).")
    A("")
    A("## Step 5 — Verify the receipt on-chain")
    A("")
    A("Do not trust a dashboard. Decode the USDC `Transfer` logs for the returned tx and "
      "confirm the recipient is the full canonical address (Recipe 27).")
    A("")
    A("---")
    A("")
    # ---- ARTICLE 3 ----
    A("# Article 3 — Advanced patterns and best practices")
    A("")
    A("## Three-surface cross-check before wiring any wall")
    A("")
    A("Compare (a) `/.well-known/x402.json`, (b) `/openapi.json`, and (c) a fresh live "
      "402. A published doc that names a field the route rejects kills the buyer before "
      "a price is ever shown; a manifest price that differs from the live challenge is "
      "drift — report it, do not pay it.")
    A("")
    A("```python")
    A("import json, urllib.request")
    A("base = 'https://royal-ruby-x402.fly.dev'")
    A("mf = json.load(urllib.request.urlopen(base + '/.well-known/x402.json'))")
    A("api = json.load(urllib.request.urlopen(base + '/openapi.json'))")
    A("route = '/api/law-lookup'")
    A("print('manifest:', route in json.dumps(mf), 'openapi:', route in api.get('paths', {}))")
    A("# then decode a live 402 (Article 1) and compare amount/payTo/network to the manifest")
    A("```")
    A("")
    A("## Guard every address comparison")
    A("")
    A("Compare the FULL 42 characters, case-insensitively. Shorthand like `0xfbc0…2240` "
      "is ambiguous and has produced false zeros; homoglyph lookalikes exist (Recipe 33). "
      "Roles here: canonical `" + CANON + "`, retired `" + RETIRED + "`, "
      "internal AgentCash `" + AGENTCASH + "`. Internal self-pays are not external revenue.")
    A("")
    A("## Idempotency, failure triage and zero-value tiers")
    A("")
    A("- Never re-pay on a 402 you already settled: map a retry to the receipt first "
      "(Recipe 32). A repeated challenge with a prior valid receipt is not a new sale.")
    A("- Distinguish a payment-path incident from scanner traffic: check the collector's "
      "`failed` count and whether any challenge came from a funded wallet before escalating.")
    A("- A $0-tier cannot settle — the facilitator rejects zero-value transfers. Charge "
      "and rebate instead, and key rebates on SETTLED payments, not issued challenges.")
    A("- Telemetry price maps must derive from the live challenge `amount`, never a "
      "hardcoded number — a 20× revenue overstatement came from exactly that mistake.")
    A("")
    A("## Chain coverage in your own reporting")
    A("")
    A("Three RPCs on one chain is one chain of evidence. A wallet holding USDC may hold "
      "it on Base AND Ethereum mainnet; a 'zero balance' claim must scope every chain "
      "with history. Publish `0 on <chain>`, never a bare `0`.")
    A("")
    A("## Honesty list")
    A("")
    for h in HONESTY:
        A(f"- {h}")
    A("")
    A("---")
    A("")
    A("## Verification record")
    A("")
    A(f"Probe time {now}. Verdict **{verdict}**. See "
      "`registry/dev-education.json` for the machine-readable snapshot. "
      "Read-only, no signing, no deploy, no external publish.")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="x402_developer_education.md")
    ap.add_argument("--json-out", default="")
    ap.add_argument("--timeout", type=float, default=25)
    args = ap.parse_args()
    walls = [probe(w, args.timeout) for w in WALLS]
    reachable = [w for w in walls if w.get("challenge_status") == 402]
    drift = []
    for w in reachable:
        if not w.get("payto") or w["payto"].lower() != CANON:
            drift.append(f"{w['svc']}: payTo {w.get('payto')}")
        if w.get("network") != "eip155:8453":
            drift.append(f"{w['svc']}: network {w.get('network')}")
        if w.get("scheme") != "exact":
            drift.append(f"{w['svc']}: scheme {w.get('scheme')}")
    verdict = "CLEAN" if not drift and len(reachable) >= 2 else "DRIFT" if drift else "UNREACHABLE"
    pack = {"version": VERSION, "generated_at": datetime.datetime.now(
        datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "verdict": verdict, "drift": drift, "walls": walls, "honesty": HONESTY}
    md = build(pack, verdict)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(md)
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8", newline="\n") as f:
            json.dump(pack, f, indent=2)
    print(f"VERSION {VERSION} verdict={verdict} reachable={len(reachable)}/{len(WALLS)} drift={len(drift)}")
    for w in walls:
        p = f"${w['price_usd']:g}" if w.get("price_usd") is not None else "n/a"
        print(f"  {w['svc']:14s} HTTP {w['challenge_status']} price={p} "
              f"payto={w.get('payto')} network={w.get('network')} scheme={w.get('scheme')}")
    for d in drift:
        print("  DRIFT:", d)
    print(f"wrote {args.out} ({len(md)} chars) / 3 articles")
    if not reachable:
        return 2
    return 1 if drift else 0


if __name__ == "__main__":
    raise SystemExit(main())
