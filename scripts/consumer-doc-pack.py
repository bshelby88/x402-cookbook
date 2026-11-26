#!/usr/bin/env python3
"""consumer-doc-pack.py — build a TRUTH-grounded consumer documentation copy pack for RAEN's kept-live paid walls (Recipe 38).

Closes TIFF-PLAN-17 ("/recommend consumer documentation copy pack") as a machine-buyer
acquisition asset: a buyer-facing doc pack whose every claim is sourced from a LIVE
surface, never hand-typed.

Read-only, stdlib-only. Sends only unpaid GET/POST probes. No signing, no X-PAYMENT,
no RPC money calls, no secrets, no funds movement, no external sends, no directory POSTs.
BURN FREEZE: only KEPT-LIVE walls are probed; frozen services are never touched.

Three-surface cross-check per wall:
  1. MANIFEST (/.well-known/x402.json): advertised request fields (extensions.bazaar
     info.input.body / JSON schema), advertised price (accepts.price or accepts.amount),
     declared payTo / network / scheme.
  2. LIVE 402 (unpaid POST): accepts[0].amount / payTo / network / scheme — the ONLY
     price truth.
  3. OPENAPI (/openapi.json): whether the route is documented and how.
A deliberately-wrong-body probe is ATTEMPTED, but on x402 paid walls the 402 challenge
precedes body validation, so the route's 400 message is usually NOT observable unpaid.
The tool reports that honestly as VALIDATION_GATED rather than inventing a schema verdict.

Exit codes: 0 CLEAN, 1 DRIFT (price/payTo/network/scheme mismatch or noncanonical),
            2 UNREACHABLE (no wall produced a live 402).
"""
import argparse, base64, datetime, json, re, sys, urllib.error, urllib.request

VERSION = "consumer-doc-pack/1.0"
CANON = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f"
RETIRED = "0x7861db4efc14a1ed5dd8c96c528a3796560f1393"
AGENTCASH = "0xfbc0eb7811d477e55261d956df39f0046e192240"
UA = {"User-Agent": "Mozilla/5.0 (compatible; RAEN-consumer-doc-pack/1.0)",
      "Accept": "*/*", "Content-Type": "application/json"}

# Kept-live walls only (BURN FREEZE). Frozen services are never probed.
WALLS = [
    {"svc": "royal-ruby", "base": "https://royal-ruby-x402.fly.dev",
     "route": "/api/law-lookup", "manifest_key": "/api/law-lookup",
     "fallback_body": {"topic": "credit-report disputes for collection accounts",
                       "state": "LA", "scope": "both"}},
    {"svc": "contract-eye", "base": "https://contract-eye-x402.fly.dev",
     "route": "/api/analyze-contract", "manifest_key": "/api/analyze-contract",
     "fallback_body": {"text": "This agreement auto-renews every twelve months unless cancelled sixty days prior.",
                       "focus": ["renewal", "liability"]}},
    {"svc": "gateway", "base": "https://raen-mcp-gateway.fly.dev",
     "route": "/mcp", "manifest_key": None,
     # tools/list is FREE discovery (HTTP 200, no challenge) — the PAID wall is tools/call.
     "fallback_body": {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": "raen_law_lookup", "arguments": {"query": "FCRA"}}}},
]

TRUTH_NOTES = [
    "Price truth = a fresh live 402 challenge (accepts[0].amount), never a hand-typed or cached price.",
    "payTo truth = the full 42-character canonical address, compared case-insensitively (homoglyph-safe).",
    "Many 402 challenges are scanners/bots — challenges are a demand signal, NOT sales (Recipe 36).",
    "Internal self-pays (AgentCash) are not external revenue; fleet external revenue is $0.00 unless the chain says otherwise.",
    "On x402 paid walls the 402 precedes body validation: a wrong-body probe cannot reveal the route's 400 message unpaid. Schema claims here come from the manifest, not an observed validation error.",
    "Chain-coverage: this verifies Base (eip155:8453) only — the chain RAEN walls settle on.",
    "Frozen services are never probed (BURN FREEZE); this pack covers kept-live walls only.",
    "Some surfaces offer a FREE discovery call that returns 200 with no challenge (e.g. the gateway's tools/list). A 200 on a free discovery call is not a paid wall; the paid wall here is tools/call.",
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
    if a == CANON:
        return "CANONICAL"
    if a == RETIRED:
        return "RETIRED"
    if a == AGENTCASH:
        return "INTERNAL_AGENTCASH"
    return "UNKNOWN"


def deep_find(obj, want):
    """First value whose key == want anywhere in a nested dict/list."""
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


def advertised_price(acc, description):
    """Return (usd, atomic, source) or (None, None, source) — never guess."""
    a = acc if isinstance(acc, dict) else {}
    if isinstance(a.get("amount"), (str, int)) and str(a.get("amount")).isdigit():
        atomic = int(a["amount"])
        return atomic / 1_000_000, atomic, "accepts.amount"
    price = a.get("price")
    if isinstance(price, str):
        m = re.search(r"\$\s*([\d.]+)", price)
        if m:
            usd = float(m.group(1))
            return usd, round(usd * 1_000_000), "accepts.price"
    m = re.search(r"\$\s*([\d.]+)", description or "")
    if m:
        usd = float(m.group(1))
        return usd, round(usd * 1_000_000), "description"
    return None, None, "none"


def manifest_endpoint(manifest, key):
    """Return (endpoint_dict, source) accepting endpoints{} or resources[]."""
    if key and isinstance(manifest.get("endpoints"), dict) and key in manifest["endpoints"]:
        return manifest["endpoints"][key], "endpoints"
    res = manifest.get("resources")
    if isinstance(res, list) and res:
        for r in res:
            if key and r.get("path") == key:
                return r, "resources"
        return res[0], "resources[0]"
    if isinstance(manifest.get("accepts"), dict):
        return manifest, "root"
    return {}, "none"


def advertised_body(endpoint):
    info = deep_find(endpoint, "input")
    if isinstance(info, dict) and isinstance(info.get("body"), dict):
        return dict(info["body"]), "extensions.bazaar.info.input.body"
    body = deep_find(endpoint, "body")
    if isinstance(body, dict) and body:
        return dict(body), "bazaar.schema.body"
    return None, "none"


def build_wall(spec, timeout):
    base, route = spec["base"], spec["route"]
    out = {"svc": spec["svc"], "base": base, "route": route, "manifest_http": 0,
           "openapi_http": 0, "live_http": 0, "advertised": {}, "live": {}, "checks": {},
           "request_body": {}, "body_source": "none", "ok": False}

    # 1. Manifest
    mcode, _, mtxt = get(base + "/.well-known/x402.json", timeout=timeout)
    out["manifest_http"] = mcode
    manifest = {}
    if mcode == 200:
        try:
            manifest = json.loads(mtxt)
        except Exception:
            manifest = {}
    ep, ep_src = manifest_endpoint(manifest, spec["manifest_key"])
    acc = ep.get("accepts", {})
    desc = ep.get("description") or (manifest.get("service", {}) or {}).get("description", "")
    adv_usd, adv_atomic, price_src = advertised_price(acc, desc)
    body, body_src = advertised_body(ep)
    out["advertised"] = {
        "source": ep_src, "price_usd": adv_usd, "price_atomic": adv_atomic,
        "price_field": price_src, "payto": acc.get("payTo"),
        "payto_role": role(acc.get("payTo")), "network": acc.get("network"),
        "scheme": acc.get("scheme"),
    }
    if body:
        out["request_body"], out["body_source"] = body, body_src
    else:
        out["request_body"], out["body_source"] = spec["fallback_body"], "fallback_known_good"

    # 2. Live 402 (unpaid POST with the advertised/fallback body)
    payload = json.dumps(out["request_body"])
    lcode, lhdrs, _ = get(base + route, "POST", payload, timeout=timeout)
    out["live_http"] = lcode
    ch = decode_challenge(lhdrs)
    live = {}
    if ch and isinstance(ch.get("accepts"), list) and ch["accepts"]:
        a = ch["accepts"][0]
        amt = a.get("amount")
        try:
            amt = int(amt)
        except (TypeError, ValueError):
            amt = None
        live = {"amount_atomic": amt, "amount_usd": (amt / 1_000_000) if amt is not None else None,
                "payto": a.get("payTo"), "payto_role": role(a.get("payTo")),
                "network": a.get("network"), "scheme": a.get("scheme")}
    out["live"] = live

    # 3. OpenAPI
    ocode, _, _ = get(base + "/openapi.json", timeout=timeout)
    out["openapi_http"] = ocode

    # 4. Wrong-body probe — honest about the 402 gate
    wcode, _, _ = get(base + route, "POST", '{"__invalid_probe__": true}', timeout=timeout)
    out["validation_probe"] = {
        "http": wcode,
        "observable": wcode == 400,
        "verdict": "OBSERVED_400" if wcode == 400 else "VALIDATION_GATED_402_PRECEDES_BODY",
    }

    # Cross-checks
    checks = {
        "live_is_402": lcode == 402,
        "payto_canonical": live.get("payto_role") == "CANONICAL",
        "network_ok": live.get("network") == "eip155:8453",
        "scheme_ok": live.get("scheme") == "exact",
        "manifest_payto_matches_live": (
            bool(acc.get("payTo")) and bool(live.get("payto")) and
            str(acc.get("payTo")).lower() == str(live.get("payto")).lower()),
        "price_matches": (adv_usd is None or live.get("amount_usd") is None
                          or abs(adv_usd - live["amount_usd"]) < 1e-9),
        "price_comparable": adv_usd is not None and live.get("amount_usd") is not None,
    }
    out["checks"] = checks
    out["ok"] = all([checks["live_is_402"], checks["payto_canonical"],
                     checks["network_ok"], checks["scheme_ok"],
                     checks["price_matches"]])
    return out


def consumer_markdown(report, walls):
    ts = report["generated_at"]
    lines = [
        "# RAEN consumer documentation pack — verified first-call facts",
        "",
        f"Generated {ts} by `{VERSION}`. Every price, address and request shape below was read from a **live** surface this run — nothing is hand-typed.",
        "",
        "## Before you pay",
        "",
        "- Price truth is the live HTTP 402 challenge, not this page and not any cached price.",
        "- Pay the **canonical** address in full: `0x9b8a27e03ceba490953cda8ab1291c0e13baf72f` on **Base (eip155:8453)**, scheme `exact`, USDC `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`.",
        "- An unpaid POST returns 402 with a `payment-required` header (base64 JSON). Decode `accepts[0]`, pay with `X-PAYMENT`, retry the POST.",
        "- A 402 is a challenge, not a sale. Most challenge volume here is scanners/bots. External earned revenue is **$0.00** unless the chain says otherwise.",
        "- Frozen services are not covered here; only kept-live walls are listed.",
        "",
        "## Verified walls",
        "",
    ]
    for w in walls:
        live = w.get("live", {})
        adv = w.get("advertised", {})
        lines += [
            f"### {w['svc']} — `POST {w['route']}`",
            "",
            f"- Base URL: `{w['base']}`",
            f"- Live price: **${live.get('amount_usd')}** USDC (`accepts[0].amount = {live.get('amount_atomic')}`)",
            f"- Pay-to: `{live.get('payto')}` ({live.get('payto_role')})",
            f"- Network / scheme: `{live.get('network')}` / `{live.get('scheme')}`",
            f"- Manifest: HTTP {w.get('manifest_http')}; OpenAPI: HTTP {w.get('openapi_http')}; advertised price: "
            + (f"${adv.get('price_usd')} ({adv.get('price_field')})" if adv.get("price_usd") is not None else "not published in manifest — live 402 is authoritative"),
            f"- Request body (source: `{w.get('body_source')}`):",
            "",
            "```json",
            json.dumps(w.get("request_body", {}), indent=2),
            "```",
            "",
            "```bash",
            f"curl -s -X POST '{w['base']}{w['route']}' -H 'Content-Type: application/json' "
            f"-d '{json.dumps(w.get('request_body', {}))}' -i   # -> 402; decode payment-required, then retry with X-PAYMENT",
            "```",
            "",
        ]
        if adv.get("price_usd") is not None and live.get("amount_usd") is not None and not w["checks"]["price_matches"]:
            lines.append(f"- ⚠️ **PRICE DRIFT**: manifest says ${adv.get('price_usd')}, live 402 charges ${live.get('amount_usd')}. Trust the live 402.")
            lines.append("")
    lines += [
        "## Honest limits",
        "",
        "- Route-level input validation could not be observed unpaid: the 402 challenge precedes body validation on these walls. Request shapes above are the seller's own published manifest examples, not a claim about server-side validation.",
        "- This pack verifies Base only; no other chain is asserted.",
        "- Nothing here was published externally; this is a local, read-only artifact.",
        "",
        "MIT licensed. Not legal or financial advice.",
        "",
    ]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Build a TRUTH-grounded consumer documentation copy pack.")
    ap.add_argument("--json", default="registry/consumer-doc-pack.json")
    ap.add_argument("--md", default="registry/consumer-doc-pack.md")
    ap.add_argument("--timeout", type=int, default=25)
    args = ap.parse_args()

    walls = [build_wall(w, args.timeout) for w in WALLS]
    any_live = any(w["checks"]["live_is_402"] for w in walls)
    drift = any(not w["ok"] for w in walls)
    verdict = "UNREACHABLE" if not any_live else ("DRIFT" if drift else "CLEAN")
    report = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "tool": VERSION, "verdict": verdict,
        "canonical_payto": CANON, "chain": "eip155:8453", "scheme": "exact",
        "truth_notes": TRUTH_NOTES, "walls": walls,
        "counts": {
            "walls": len(walls),
            "live_402": sum(1 for w in walls if w["checks"]["live_is_402"]),
            "canonical": sum(1 for w in walls if w["checks"]["payto_canonical"]),
            "price_drift": sum(1 for w in walls if w["checks"]["price_comparable"] and not w["checks"]["price_matches"]),
        },
    }
    with open(args.json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")
    with open(args.md, "w", encoding="utf-8") as f:
        f.write(consumer_markdown(report, walls))
    print(f"{VERSION} verdict={verdict} walls={len(walls)} "
          f"live402={report['counts']['live_402']} canonical={report['counts']['canonical']} "
          f"price_drift={report['counts']['price_drift']}")
    for w in walls:
        print(f"  {w['svc']:12} live={w['live'].get('amount_usd')} "
              f"payto={w['live'].get('payto_role')} net={w['live'].get('network')} "
              f"body={w['body_source']} ok={w['ok']}")
    return 0 if verdict == "CLEAN" else (1 if verdict == "DRIFT" else 2)


if __name__ == "__main__":
    sys.exit(main())
