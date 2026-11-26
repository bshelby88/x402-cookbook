#!/usr/bin/env python3
"""Innovation 45 - Installable Agent Buyer Skill Card (stdlib, read-only).

The cookbook's 44 tools are reference material an agent must READ and interpret.
This one emits a single portable SKILL.md-style card an autonomous agent can
INSTALL (copy into a skills/ dir or paste into system instructions) and then
follow to buy from any RAEN wall without re-deriving the protocol.

Every price / payTo / network / request body in the card is LIVE-READ from an
unpaid 402 challenge; the card carries its generated_utc and declares that the
live 402 is authoritative over the snapshot.

This tool NEVER signs, NEVER sends X-PAYMENT, NEVER makes an RPC money call,
NEVER moves funds, NEVER uses a key, NEVER posts anywhere and NEVER deploys.
BURN FREEZE respected: only kept-live walls are probed, unpaid.

Outputs registry/agent-skillcard.json (live snapshot) and
registry/agent-skillcard.md (the installable card).

Exit 0 = every probed wall canonical; 1 = a canonical break; 2 = none reachable.
"""

import argparse
import base64
import datetime
import json
import sys
import urllib.error
import urllib.request

VERSION = "agent-skillcard/1.0"
CANON = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f"
RETIRED = "0x7861db4efc14a1ed5dd8c96c528a3796560f1393"
BASE_NETWORK = "eip155:8453"
ATOMIC = 1_000_000

WALLS = [
    {"name": "royal-ruby", "base": "https://royal-ruby-x402.fly.dev",
     "route": "/api/law-lookup", "method": "POST",
     "offer": "Statutory law lookup with cited baseline",
     "body": {"query": "x402 skillcard probe"}},
    {"name": "contract-eye", "base": "https://contract-eye-x402.fly.dev",
     "route": "/api/analyze-contract", "method": "POST",
     "offer": "Contract risk analysis",
     "body": {"text": "x402 skillcard probe"}},
    {"name": "nanobanana", "base": "https://nanobanana-x402.fly.dev",
     "route": "/api/generate-image", "method": "POST",
     "offer": "Image generation",
     "body": {"prompt": "x402 skillcard probe"}},
    {"name": "raen-mcp-gateway", "base": "https://raen-mcp-gateway.fly.dev",
     "route": "/mcp", "method": "POST",
     "offer": "MCP tool call gateway (tools/list is free for discovery)",
     "body": {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
              "params": {"name": "raen_law_lookup",
                         "arguments": {"topic": "x402 skillcard probe"}}}},
]

UA = {"User-Agent": "Mozilla/5.0 (compatible; RAEN-agent-skillcard/1.0)",
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
            return r.status, dict(r.headers.items())
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers.items())
    except Exception:
        return None, {}


def decode_challenge(headers):
    raw = None
    for k, v in headers.items():
        if k.lower() in ("payment-required", "x-payment-required"):
            raw = v
            break
    if not raw or "..." in raw:
        return None
    if "," in raw and not raw.lstrip().startswith("{"):
        raw = raw.split(",", 1)[1].strip()
    try:
        return json.loads(base64.b64decode(raw + "=" * (-len(raw) % 4)).decode("utf-8"))
    except Exception:
        return None


def canon(addr):
    return (isinstance(addr, str) and len(addr) == 42
            and addr.lower() == CANON.lower())


def probe(wall):
    url = wall["base"] + wall["route"]
    status, headers = http(wall["method"], url, wall.get("body"), UA)
    out = {"name": wall["name"], "offer": wall["offer"], "url": url,
           "method": wall["method"], "request_body": wall.get("body"),
           "http_status": status, "canonical": False}
    if status != 402:
        out["detail"] = "expected 402, got %s" % status
        return out
    obj = decode_challenge(headers)
    if not obj:
        out["detail"] = "undecodable payment-required header"
        return out
    acc = (obj.get("accepts") or [{}])[0]
    if not isinstance(acc, dict):
        acc = {}
    raw_amt = acc.get("amount")
    try:
        amt = int(raw_amt) if raw_amt is not None else None
    except (TypeError, ValueError):
        amt = None
    acc_scheme = acc.get("scheme")
    acc_network = acc.get("network")
    acc_payto = acc.get("payTo")
    checks = {
        "v2": obj.get("x402Version") == 2,
        "scheme": acc_scheme == "exact",
        "network": acc_network == BASE_NETWORK,
        "payTo": canon(acc_payto),
        "amount": amt is not None and amt > 0,
    }
    out.update(
        x402Version=obj.get("x402Version"), scheme=acc_scheme,
        network=acc_network, payTo=acc_payto, asset=acc.get("asset"),
        amount_atomic=amt,
        amount_usd=(round(amt / ATOMIC, 6) if amt is not None else None),
        checks=checks, canonical=all(checks.values()),
        detail=("canonical" if all(checks.values()) else
                "failed: " + ",".join(k for k, ok in checks.items() if not ok)),
    )
    return out


def render_card(rows, generated_at, verdict):
    L = []
    A = L.append
    A("---")
    A("name: raen-x402-buyer")
    A("description: >-")
    A("  Buy paid AI services from the RAEN x402 fleet on Base. Use when an "
      "autonomous agent needs to call a RAEN paid endpoint: live-verified "
      "prices, canonical payTo guard, EIP-3009 checkout order and claims-desk "
      "fallback in one portable file.")
    A("---")
    A("")
    A("# RAEN x402 buyer card (installable)")
    A("")
    A("Copy this file into your agent's `skills/` directory or paste it into "
      "your system instructions. It is self-contained and read-only.")
    A("")
    A("**Snapshot generated** `%s` (UTC). Every price and payTo below was "
      "read live from an unpaid 402 challenge at that time. The **live 402 is "
      "authoritative** — re-read it at purchase time; a snapshot is never a "
      "contract." % generated_at)
    A("")
    A("## Hard rules")
    A("")
    A("1. Only pay a `payTo` equal to the FULL 42-character canonical address "
      "`%s` (case-insensitive). Reject prefixes, suffixes, lookalikes, and "
      "the retired `%s`." % (CANON, RETIRED))
    A("2. Verify the decoded challenge: `x402Version==2`, `scheme=='exact'`, "
      "`network=='eip155:8453'`, integer `amount > 0`, asset is USDC on Base.")
    A("3. Sign EIP-3009 `transferWithAuthorization` with YOUR OWN wallet for "
      "the exact terms in the challenge. Never reuse a signature, never pay "
      "a different amount or address.")
    A("4. Do not treat a 402 as an error or as a completed purchase. A 402 is "
      "the seller's price quote; a 2xx after the signed retry is the "
      "deliverable.")
    A("5. If a settled payment yields no deliverable, use the claims desk at "
      "`https://royal-ruby-x402.fly.dev/` (`?payer=<your-address>`) instead "
      "of paying twice. Public telemetry: "
      "`https://settlement-collector.fly.dev/stats`.")
    A("6. Never put keys, wallet secrets or signed headers in chat, logs, "
      "issues or this card.")
    A("")
    A("## Live walls (verdict: %s at snapshot time)" % verdict)
    A("")
    A("| Service | Endpoint | Offer | Price | Unpaid request body |")
    A("| --- | --- | --- | --- | --- |")
    for r in rows:
        price = ("$%.6g" % r["amount_usd"]) if r.get("amount_usd") is not None else "n/a"
        body = json.dumps(r.get("request_body"), separators=(",", ":"))
        if len(body) > 90:
            body = body[:87] + "..."
        A("| `%s` | `%s` | %s | %s | `%s` |" %
          (r["name"], r["url"], r["offer"], price, body.replace("|", "\\|")))
    A("")
    A("## Checkout order (one call)")
    A("")
    A("1. `POST` the request body from the table to the wall's URL with "
      "`Content-Type: application/json` and **no** payment header.")
    A("2. Expect `402`. Base64-decode the `payment-required` header into the "
      "x402 v2 envelope; read `accepts[0]`.")
    A("3. Apply the Hard rules guards. If any fails, STOP — do not sign.")
    A("4. Sign the exact `accepts[0]` terms with your wallet "
      "(EIP-3009 on Base) and retry the same request with the base64 "
      "`X-PAYMENT` header.")
    A("5. Read the 2xx deliverable. Verify it is the advertised output, not "
      "a `degraded` placeholder.")
    A("")
    A("Free discovery before paying: `tools/list` on the MCP gateway is open; "
      "`/.well-known/x402.json` on each wall advertises its schema. "
      "Cross-check docs against the live 402 — when they disagree, the live "
      "402 wins.")
    A("")
    A("## Honesty")
    A("")
    A("RAEN publishes real telemetry, including $0 external revenue. This "
      "card asserts a price snapshot and a payTo guard only; it does not "
      "promise uptime, output quality or a refund outside the claims desk.")
    A("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()
    rows = [probe(w) for w in WALLS]
    reachable = [r for r in rows if r.get("http_status") == 402]
    breaks = [r["name"] for r in rows if r.get("canonical") is False
              and r.get("http_status") == 402]
    verdict = ("OK" if not breaks and len(reachable) == len(WALLS)
               else "BREAK" if breaks else "UNREACHABLE")
    generated_at = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    snap = {
        "tool": VERSION, "generated_utc": generated_at, "verdict": verdict,
        "canonical_payto": CANON, "retired_payto": RETIRED,
        "network": BASE_NETWORK, "asset": "USDC 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "walls": rows, "breaks": breaks,
        "authority": "live 402 challenge > manifest > this snapshot",
        "no_sign_no_send": True,
    }
    card = render_card(rows, generated_at, verdict)
    if not args.no_write:
        with open("registry/agent-skillcard.json", "w", encoding="utf-8") as f:
            json.dump(snap, f, indent=2, ensure_ascii=False)
            f.write("\n")
        with open("registry/agent-skillcard.md", "w", encoding="utf-8") as f:
            f.write(card)
    print("verdict=%s reachable=%d/%d breaks=%s generated=%s" %
          (verdict, len(reachable), len(WALLS), breaks, generated_at))
    for r in rows:
        print("  %-18s status=%s price=%s canonical=%s detail=%s" %
              (r["name"], r.get("http_status"), r.get("amount_usd"),
               r.get("canonical"), r.get("detail")))
    if breaks:
        return 1
    if not reachable:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
