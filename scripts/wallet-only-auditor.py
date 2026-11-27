#!/usr/bin/env python3
"""Tiffany Innovation 60 - Wallet-Only Purchase Conformance Auditor.

The owner's law is "get autonomous agents to our platforms to create revenue."
An autonomous agent has a WALLET, not an email, an account, a browser session or
a human turn. If a paid RAEN surface introduces an identity wall BEFORE or AT
the payment gate (required email / account / API key / OAuth / KYC / signup),
the agent cannot buy -- a silent acquisition loss with no money moved.

Tools 1-59 grade the wall (23/42/43), the docs (48/59), the payer (49/50/51),
the ledger/chain (52), settlement (54), and the MCP bridge (57) -- but none
grades whether an autonomous agent can buy with a wallet ALONE. This closes it.

Read-only, stdlib-only. No signing, no X-PAYMENT, no funds, no sends, no deploy.
It issues UNPAID probes, decodes the public 402, and inspects the public manifest
schema + description for identity gates.

Verdicts: WALLET_ONLY / IDENTITY_WALL / GAP / UNREACHABLE.
--check fails (exit 1) ONLY on a HARD identity wall on a paid route. A documented
OPTIONAL key alternative (e.g. "or a Bearer dev key"), a down page, an absent
schema or a price drift is a WARN/GAP (exit 0) -> handoff, never an auto-fix.
Pricing and credentials are owner-gated; this tool NEVER changes either.
"""
import base64
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

CANON = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f".lower()
RETIRED = "0x7861db4efc14a1ed5dd8c96c528a3796560f1393".lower()
UA = {"User-Agent": "RAEN-WalletOnly-Auditor/1.0 (+autonomous-buyer-truth)",
      "Accept": "application/json"}
TIMEOUT = 25

# name, base, paid route, paid method, unpaid body, manifest url, free discovery probe
WALLS = [
    {"name": "royal-ruby", "base": "https://royal-ruby-x402.fly.dev",
     "route": "/api/law-lookup", "method": "POST", "body": {"topic": "wallet-only probe"},
     "manifest": "https://royal-ruby-x402.fly.dev/.well-known/x402.json",
     "free": ("https://royal-ruby-x402.fly.dev/.well-known/x402.json", None)},
    {"name": "contract-eye", "base": "https://contract-eye-x402.fly.dev",
     "route": "/api/analyze-contract", "method": "POST", "body": {"text": "wallet-only probe"},
     "manifest": "https://contract-eye-x402.fly.dev/.well-known/x402.json",
     "free": ("https://contract-eye-x402.fly.dev/.well-known/x402.json", None)},
    {"name": "nanobanana", "base": "https://nanobanana-x402.fly.dev",
     "route": "/api/generate-image", "method": "POST", "body": {"prompt": "wallet-only probe"},
     "manifest": "https://nanobanana-x402.fly.dev/.well-known/x402.json",
     "free": ("https://nanobanana-x402.fly.dev/.well-known/x402.json", None)},
    {"name": "raen-mcp-gateway", "base": "https://raen-mcp-gateway.fly.dev",
     "route": "/mcp", "method": "POST",
     "body": {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
              "params": {"name": "raen_law_lookup", "arguments": {"topic": "wallet-only probe"}}},
     "manifest": "https://raen-mcp-gateway.fly.dev/.well-known/x402.json",
     "free": ("https://raen-mcp-gateway.fly.dev/mcp",
              {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})},
]

# Exact field names that constitute an identity gate if REQUIRED on a paid route.
IDENTITY_FIELDS = {
    "email", "e_mail", "email_address", "phone", "telephone", "mobile",
    "ssn", "kyc", "kyc_level", "api_key", "apikey", "api-key", "authorization",
    "oauth", "oauth_token", "password", "passwd", "account", "account_id",
    "username", "credit_card", "card_number", "cvv", "billing_address",
}
# A phrase proving an account/credential step is a REQUIRED precondition to buy.
HARD_PHRASES = re.compile(
    r"must\s+sign\s*up|sign\s*up\s+required|create\s+an\s+account|account\s+required|"
    r"email\s+required|api\s*key\s+required|kyc\s+required|login\s+required|"
    r"log\s+in\s+required|oauth\s+required|registration\s+required|register\s+to\s+use|"
    r"requires?\s+(?:an?\s+)?(?:account|sign\s*up|registration|kyc)\b",
    re.I,
)
# A documented OPTIONAL credential alternative is a WARN, not a hard wall.
OPTIONAL_ALT = re.compile(
    r"or\s+(?:a\s+)?bearer|or\s+(?:an?\s+)?api\s*key|dev\s+key|optional.{0,20}key",
    re.I,
)


def fetch(url, method="GET", body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    hdr = dict(UA)
    if data is not None:
        hdr["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=hdr, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return getattr(r, "status", None) or r.getcode(), dict(r.headers), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, {}, "ERR:" + str(e)[:100]


def decode_challenge(headers, body):
    for key, val in headers.items():
        if key.lower() in ("payment-required", "x-payment-required"):
            raw = val.strip()
            try:
                return json.loads(base64.b64decode(raw + "=" * (-len(raw) % 4)).decode())
            except Exception:
                return None
    try:
        cand = json.loads(body.strip())
        if any(k in cand for k in ("accepts", "payTo", "x402Version")):
            return cand
    except Exception:
        pass
    return None


def wallet_gate(chal):
    """Return (ok, note) for a canonical, wallet-only 402 challenge."""
    if not chal or not isinstance(chal.get("accepts"), list) or not chal["accepts"]:
        return False, "no decodable accepts[]"
    a = chal["accepts"][0]
    payto = str(a.get("payTo", ""))
    if len(payto) != 42 or payto.lower() != CANON:
        return False, "payTo not canonical" + (" (RETIRED!)" if payto.lower() == RETIRED else "")
    if str(a.get("network", "")).lower() != "eip155:8453":
        return False, "network not eip155:8453"
    if str(a.get("scheme", "")).lower() != "exact":
        return False, "scheme not exact"
    return True, "canonical wallet gate"


def collect_schema_fields(endpoint):
    """Field names declared anywhere in one manifest endpoint object."""
    fields = set()
    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("properties", "required") and isinstance(v, (dict, list)):
                    if isinstance(v, dict):
                        fields.update(str(x).lower() for x in v.keys())
                    else:
                        fields.update(str(x).lower() for x in v)
                elif k in ("body",) and isinstance(v, dict):
                    fields.update(str(x).lower() for x in v.keys())
                walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(endpoint)
    return fields


def find_endpoint(manifest, route):
    eps = manifest.get("endpoints", []) if isinstance(manifest, dict) else []
    if isinstance(eps, dict):
        for k, v in eps.items():
            if route in k or (isinstance(v, dict) and v.get("path") == route):
                return v
        return None
    for e in eps:
        if isinstance(e, dict) and (e.get("path") == route or e.get("route") == route or e.get("endpoint") == route):
            return e
    # gateway-style: single /mcp endpoint
    for e in eps:
        if isinstance(e, dict) and e.get("path") == route:
            return e
    return None


def grade_identity(fields, description):
    """Return (hard_bool, warns_list). Pure function -- unit-testable."""
    hard, warns = False, []
    hit = sorted((fields or set()) & IDENTITY_FIELDS)
    if hit:
        hard = True
        warns.append("required identity field(s): " + ", ".join(hit))
    if HARD_PHRASES.search(description or ""):
        hard = True
        warns.append("hard account/credential precondition in description")
    if OPTIONAL_ALT.search(description or "") and not hard:
        warns.append("optional credential alternative noted (wallet still works)")
    return hard, warns


def audit():
    rows = []
    for w in WALLS:
        row = {"name": w["name"], "route": w["route"]}
        code, hdrs, body = fetch(w["base"] + w["route"], w["method"], w["body"])
        row["unpaid_status"] = code
        chal = decode_challenge(hdrs, body)
        ok, note = wallet_gate(chal)
        row["wallet_gate"] = note if ok else "NO GATE / " + note

        mcode, _, mbody = fetch(w["manifest"])
        desc = ""
        fields = set()
        if mcode == 200:
            try:
                man = json.loads(mbody)
                ep = find_endpoint(man, w["route"])
                if ep:
                    desc = ep.get("description", "")
                    fields = collect_schema_fields(ep)
            except Exception as e:
                desc = "manifest parse error: " + str(e)[:60]
        else:
            desc = "manifest unreachable (HTTP %s)" % mcode

        hard, warns = grade_identity(fields, desc)
        fcode, _, _ = fetch(w["free"][0], "POST" if w["free"][1] else "GET", w["free"][1])
        row["free_discovery_status"] = fcode
        row["paid_schema_identity_fields"] = sorted(fields & IDENTITY_FIELDS)
        row["warns"] = warns

        if not ok:
            row["verdict"] = "UNREACHABLE" if code == 0 else "GAP"
        elif hard:
            row["verdict"] = "IDENTITY_WALL"
        elif fcode != 200:
            row["verdict"] = "GAP"
            row["warns"].append("free discovery probe not 200 (HTTP %s)" % fcode)
        else:
            row["verdict"] = "WALLET_ONLY"
        rows.append(row)
    return rows


def self_test():
    cases = [
        ({"topic", "state", "scope"}, "Look up law citations. Pay via x402 on Base.", False),
        ({"email", "topic"}, "Pay via x402.", True),
        ({"topic"}, "Create an account to use this endpoint.", True),
        ({"topic"}, "tools/call requires an x402 payment or a Bearer dev key.", False),
    ]
    for i, (fields, desc, expect_hard) in enumerate(cases):
        hard, _ = grade_identity(set(fields), desc)
        status = "PASS" if hard == expect_hard else "FAIL"
        print("  case %d: expect_hard=%s got=%s -> %s" % (i + 1, expect_hard, hard, status))
        if hard != expect_hard:
            return 1
    gate_ok, _ = wallet_gate({"accepts": [{"payTo": CANON, "network": "eip155:8453", "scheme": "exact", "amount": 5000}]})
    if not gate_ok:
        print("  case 5: canonical wallet gate -> FAIL")
        return 1
    print("  case 5: canonical wallet gate -> PASS")
    return 0


def main():
    if "--self-test" in sys.argv:
        return self_test()
    rows = audit()
    out = {
        "tool": "wallet-only-purchase-conformance-auditor",
        "innovation": 60,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "doctrine": "autonomous agent has a wallet, not an email/account/API key; identity wall before payment = lost sale",
        "rows": rows,
    }
    print(json.dumps(out, indent=2))
    if "--check" in sys.argv:
        hard = [r for r in rows if r["verdict"] == "IDENTITY_WALL"]
        if hard:
            print("HARD IDENTITY WALL on: " + ", ".join(r["name"] for r in hard), file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
