#!/usr/bin/env python3
"""Innovation 62 - x402 Challenge Constructability Auditor (RAEN x402 cookbook).

Machine-buyer acquisition tool. A strict autonomous x402 client cannot pay a
wall from the price alone: it must CONSTRUCT a valid EIP-3009 payment
authorization. This tool decodes each LIVE 402 challenge (unpaid probe, no
X-PAYMENT) and grades whether the buyer has every field required to build that
payment, and whether header-readers and body-readers agree.

READ-ONLY, stdlib-only. Never signs, never pays, never moves funds, never
changes a price (pricing is owner-gated). --check fails ONLY on hard gate /
constructability defects; band and doc drift are WARN/owner-handoff.

Acquired-data comparison before acting: tools 48 (schema parity), 57 (MCP
bridge prices), 58 (volume-tier docs), 61 (price vs winner band) all inspect
PRICE or DOC parity. NONE verify that accepts[0] carries the EIP-3009 domain
fields (extra.name/extra.version), asset, timeout and resource a strict client
needs to actually construct a payment. That gap is this tool.
"""
import argparse, base64, json, sys, urllib.error, urllib.request

CANON = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f"
BASE_USDC = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
EXACT_NETWORK = "eip155:8453"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
      "Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
TIMEOUT = 35

PROBES = [
    {"name": "royal-ruby", "url": "https://royal-ruby-x402.fly.dev/api/law-lookup",
     "body": {"topic": "constructability probe"}},
    {"name": "contract-eye", "url": "https://contract-eye-x402.fly.dev/api/analyze-contract",
     "body": {"text": "constructability probe"}},
    {"name": "nanobanana", "url": "https://nanobanana-x402.fly.dev/api/generate-image",
     "body": {"prompt": "constructability probe"}},
    {"name": "gateway:law", "url": "https://raen-mcp-gateway.fly.dev/mcp",
     "body": {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
              "params": {"name": "raen_law_lookup", "arguments": {}}}},
    {"name": "gateway:ticker", "url": "https://raen-mcp-gateway.fly.dev/mcp",
     "body": {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
              "params": {"name": "raen_ticker_analysis", "arguments": {}}}},
    {"name": "gateway:dispute_letter", "url": "https://raen-mcp-gateway.fly.dev/mcp",
     "body": {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
              "params": {"name": "raen_dispute_letter", "arguments": {}}}},
    {"name": "gateway:image", "url": "https://raen-mcp-gateway.fly.dev/mcp",
     "body": {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
              "params": {"name": "raen_image_gen", "arguments": {}}}},
    {"name": "gateway:contract", "url": "https://raen-mcp-gateway.fly.dev/mcp",
     "body": {"jsonrpc": "2.0", "id": 5, "method": "tools/call",
              "params": {"name": "raen_contract_review", "arguments": {}}}},
]


def fetch(url, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=UA, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, dict(r.headers), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, {}, "ERR " + repr(e)


def header_challenge(headers):
    for k, v in headers.items():
        if k.lower() in ("payment-required", "x-payment-required"):
            try:
                return json.loads(base64.b64decode(v + "=" * (-len(v) % 4)))
            except Exception:
                return None
    return None


def body_challenge(body):
    if "data:" in body:  # SSE frame
        body = "\n".join(l[5:].strip() for l in body.splitlines() if l.startswith("data:"))
    try:
        j = json.loads(body)
        return j if isinstance(j, dict) and "accepts" in j else None
    except Exception:
        return None


def accepts0(chal):
    if not isinstance(chal, dict):
        return {}
    a = chal.get("accepts")
    return a[0] if isinstance(a, list) and a and isinstance(a[0], dict) else {}


def grade(name, status, headers, body):
    """Return {name, verdict, defects, warns, amount_usd}."""
    d, w = [], []
    if status == 200:
        return {"name": name, "verdict": "FREE_BACKDOOR", "http": status,
                "defects": ["paid call returned 200 with no 402 challenge"],
                "warns": [], "amount_usd": None}
    if status != 402:
        return {"name": name, "verdict": "NO_CHALLENGE", "http": status,
                "defects": ["expected HTTP 402, got %s" % status], "warns": [], "amount_usd": None}

    hc = header_challenge(headers)
    bc = body_challenge(body)
    if hc is None and bc is None:
        return {"name": name, "verdict": "INVALID_CHALLENGE", "http": status,
                "defects": ["no decodable accepts[] in header or body"], "warns": [], "amount_usd": None}

    a = accepts0(hc or bc)
    ha, ba = accepts0(hc), accepts0(bc)
    # canonical gate checks (hard)
    if str(a.get("scheme", "")).lower() != "exact":
        d.append("scheme != exact")
    if str(a.get("network", "")).lower() != EXACT_NETWORK:
        d.append("network != " + EXACT_NETWORK)
    if str(a.get("payTo", "")).lower() != CANON:
        d.append("payTo not canonical")
    if str(a.get("asset", "")).lower() != BASE_USDC:
        d.append("asset not canonical Base USDC")
    # EIP-3009 constructability fields (hard) -- the novel axis
    raw_amt = a.get("amount", a.get("maxAmountRequired"))
    try:
        amt = int(raw_amt)
        if amt <= 0:
            raise ValueError
    except Exception:
        amt = None
        d.append("amount missing/invalid")
    if not (isinstance(a.get("maxTimeoutSeconds"), int) and a["maxTimeoutSeconds"] > 0):
        d.append("maxTimeoutSeconds missing/invalid")
    extra = a.get("extra") if isinstance(a.get("extra"), dict) else {}
    if not extra.get("name"):
        d.append("extra.name (EIP-3009 domain) missing")
    if not extra.get("version"):
        d.append("extra.version (EIP-3009 domain) missing")
    if not (hc or {}).get("resource") and not (bc or {}).get("resource"):
        d.append("resource descriptor missing")
    # header vs body agreement (hard) -- body-reading clients
    if ha and ba:
        if str(ha.get("payTo", "")).lower() != str(ba.get("payTo", "")).lower():
            d.append("header/body payTo disagree")
        if str(ha.get("amount", ha.get("maxAmountRequired", ""))) != str(ba.get("amount", ba.get("maxAmountRequired", ""))):
            d.append("header/body amount disagree")
    elif hc and not bc:
        w.append("body has no accepts[] (body-reading clients fail)")
    # owner-gated WARNs
    if amt is not None and amt < 3000:
        w.append("price $%.3f below acquired-data winner floor $0.003 (owner-gated)" % (amt / 1e6))
    if amt is not None and amt > 10000:
        w.append("price $%.3f above winner band $0.01 (owner-gated)" % (amt / 1e6))
    return {"name": name, "verdict": "CONSTRUCTIBLE" if not d else "DEFECT", "http": status,
            "defects": d, "warns": w, "amount_usd": round(amt / 1e6, 6) if amt else None}


def self_test():
    good = {"x402Version": 2, "resource": {"url": "u", "description": "d"},
            "accepts": [{"scheme": "exact", "network": EXACT_NETWORK, "payTo": CANON,
                         "asset": BASE_USDC, "amount": "5000",
                         "maxTimeoutSeconds": 300, "extra": {"name": "USD Coin", "version": "2"}}]}
    import copy
    hdr = {"payment-required": base64.b64encode(json.dumps(good).encode()).decode()}
    cases = []
    r = grade("good", 402, hdr, json.dumps(good)); cases.append(("good", r["verdict"] == "CONSTRUCTIBLE", r))
    g2 = copy.deepcopy(good); del g2["accepts"][0]["extra"]["name"]
    h2 = {"payment-required": base64.b64encode(json.dumps(g2).encode()).decode()}
    r = grade("no-domain-name", 402, h2, json.dumps(g2)); cases.append(("no-domain-name", r["verdict"] == "DEFECT" and any("extra.name" in x for x in r["defects"]), r))
    g3 = copy.deepcopy(good); del g3["accepts"][0]["asset"]
    h3 = {"payment-required": base64.b64encode(json.dumps(g3).encode()).decode()}
    r = grade("no-asset", 402, h3, json.dumps(g3)); cases.append(("no-asset", r["verdict"] == "DEFECT", r))
    g4 = copy.deepcopy(good); g4["accepts"][0]["payTo"] = "0x" + "1" * 40
    h4 = {"payment-required": base64.b64encode(json.dumps(g4).encode()).decode()}
    r = grade("bad-payto", 402, h4, json.dumps(g4)); cases.append(("bad-payto", r["verdict"] == "DEFECT", r))
    g5 = copy.deepcopy(good); g5["accepts"][0]["amount"] = "1000"
    h5 = {"payment-required": base64.b64encode(json.dumps(good).encode()).decode()}
    r = grade("hdr-body-amount-mismatch", 402, h5, json.dumps(g5)); cases.append(("mismatch", r["verdict"] == "DEFECT" and any("amount disagree" in x for x in r["defects"]), r))
    r = grade("free-backdoor", 200, {}, "{}"); cases.append(("200", r["verdict"] == "FREE_BACKDOOR", r))
    r = grade("below-band", 402, hdr, json.dumps(good))
    # below-band is exercised via a dedicated mutated challenge
    gb = copy.deepcopy(good); gb["accepts"][0]["amount"] = "2000"
    hb = {"payment-required": base64.b64encode(json.dumps(gb).encode()).decode()}
    rb = grade("below-band", 402, hb, json.dumps(gb))
    cases.append(("below-band-warn-only", rb["verdict"] == "CONSTRUCTIBLE" and any("winner floor" in x for x in rb["warns"]), rb))
    ok = all(p for _, p, _ in cases)
    for n, p, _ in cases:
        print("  %-24s %s" % (n, "PASS" if p else "FAIL"))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="nonzero on hard defects")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        print("SELF-TEST:"); return 0 if self_test() else 1
    results = []
    for t in PROBES:
        st, h, b = fetch(t["url"], t["body"])
        results.append(grade(t["name"], st, h, b))
    for r in results:
        price = ("$%.3f" % r["amount_usd"]) if r["amount_usd"] is not None else "-"
        print("%-22s %-14s %-8s http=%s" % (r["name"], r["verdict"], price, r["http"]))
        for x in r["defects"]: print("    DEFECT:", x)
        for x in r["warns"]: print("    WARN  :", x)
    hard = sum(1 for r in results if r["verdict"] not in ("CONSTRUCTIBLE",))
    print("\nSUMMARY: %d/%d constructible, %d hard defect(s)" % (len(results) - hard, len(results), hard))
    return 1 if (args.check and hard) else 0


if __name__ == "__main__":
    sys.exit(main())
