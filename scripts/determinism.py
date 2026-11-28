#!/usr/bin/env python3
"""Innovation 65 - x402 Challenge Determinism Auditor (RAEN x402 cookbook).

Machine-buyer acquisition tool. Every other tool grades ONE 402 snapshot. But
RAEN's own ops history is full of concurrent deploys, stale images and live-only
changes that leave one machine serving a DIFFERENT challenge than another. A
machine buyer whose preflight/budget policy is computed from one 402 cannot
function if the next identical request returns a different price or payTo: that
is a silent acquisition blocker no single-snapshot tool can see.

This tool probes each kept-live paid wall (and the MCP gateway's five paid
tools) THREE times with identical UNPAID bodies, decodes every 402, and grades
whether the canonical payment envelope is DETERMINISTIC across time. It reports
field-level drift (amount / payTo / network / scheme / asset / timeout / EIP-3009
domain / resource) and a fleet determinism score.

READ-ONLY, stdlib-only. Never signs, never sends X-PAYMENT, never pays, never
moves funds, never uses a key, never deploys, never changes a price (pricing is
owner-gated). --check fails on hard drift or instability, never on a price being
outside the owner-gated band.

Acquired-data comparison before acting: tools 24/61 (price snapshot/band), 42
(challenge conformance GET vs HEAD vs POST), 57 (MCP bridge prices), 58 (volume
tier across quantities), 62 (single-probe constructability + header/body) and
64 (point-of-sale offer disclosure) all grade a SINGLE response or a different
axis. NONE repeats an identical unpaid probe to test temporal determinism.
That gap is this tool.
"""
import argparse, base64, json, sys, time, urllib.error, urllib.request

CANON = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f"
BASE_USDC = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
EXACT_NETWORK = "eip155:8453"
PROBES_PER_TARGET = 3
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
      "Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
TIMEOUT = 35

PROBES = [
    {"name": "royal-ruby", "url": "https://royal-ruby-x402.fly.dev/api/law-lookup",
     "body": {"topic": "determinism probe"}},
    {"name": "contract-eye", "url": "https://contract-eye-x402.fly.dev/api/analyze-contract",
     "body": {"text": "determinism probe"}},
    {"name": "nanobanana", "url": "https://nanobanana-x402.fly.dev/api/generate-image",
     "body": {"prompt": "determinism probe"}},
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
    if "data:" in body:
        body = "\n".join(l[5:].strip() for l in body.splitlines() if l.startswith("data:"))
    try:
        j = json.loads(body)
        return j if isinstance(j, dict) and "accepts" in j else None
    except Exception:
        return None


def accepts0(chal):
    a = chal.get("accepts") if isinstance(chal, dict) else None
    return a[0] if isinstance(a, list) and a and isinstance(a[0], dict) else {}


def fingerprint(status, headers, body):
    """Decode one probe into (fingerprint dict, hard defects list, price_usd)."""
    d = []
    if status == 200:
        return None, ["paid call returned 200 (free backdoor)"], None
    if status != 402:
        return None, ["expected HTTP 402, got %s" % status], None
    hc, bc = header_challenge(headers), body_challenge(body)
    if hc is None and bc is None:
        return None, ["no decodable accepts[] in header or body"], None
    a = accepts0(hc or bc)
    ha, ba = accepts0(hc), accepts0(bc)
    if str(a.get("scheme", "")).lower() != "exact":
        d.append("scheme != exact")
    if str(a.get("network", "")).lower() != EXACT_NETWORK:
        d.append("network != " + EXACT_NETWORK)
    if str(a.get("payTo", "")).lower() != CANON:
        d.append("payTo not canonical")
    if str(a.get("asset", "")).lower() != BASE_USDC:
        d.append("asset not canonical Base USDC")
    if ha and ba:
        if str(ha.get("payTo", "")).lower() != str(ba.get("payTo", "")).lower():
            d.append("header/body payTo disagree")
        if str(ha.get("amount", ha.get("maxAmountRequired", ""))) != str(ba.get("amount", ba.get("maxAmountRequired", ""))):
            d.append("header/body amount disagree")
    raw = a.get("amount", a.get("maxAmountRequired"))
    try:
        atoms = int(raw)
        if atoms <= 0:
            raise ValueError
    except Exception:
        atoms = None
        d.append("amount missing/invalid")
    extra = a.get("extra") if isinstance(a.get("extra"), dict) else {}
    fp = {
        "scheme": str(a.get("scheme", "")).lower(),
        "network": str(a.get("network", "")).lower(),
        "payTo": str(a.get("payTo", "")).lower(),
        "asset": str(a.get("asset", "")).lower(),
        "amount": atoms,
        "maxTimeoutSeconds": a.get("maxTimeoutSeconds"),
        "extra.name": extra.get("name"),
        "extra.version": extra.get("version"),
        "resource": (hc or bc or {}).get("resource"),
    }
    return fp, d, (round(atoms / 1e6, 6) if atoms is not None else None)


def grade_series(name, series):
    """series: list of (status, headers, body). Returns verdict + drift detail."""
    fps, defects, prices = [], [], []
    for st, h, b in series:
        fp, d, price = fingerprint(st, h, b)
        defects.extend(d)
        if fp is not None:
            fps.append(fp)
        if price is not None:
            prices.append(price)
    if defects:
        return {"name": name, "verdict": "DRIFT", "probes": len(series),
                "price_usd": prices[0] if prices else None, "drift_fields": [], "defects": sorted(set(defects))}
    if len(fps) != len(series):
        return {"name": name, "verdict": "NO_CHALLENGE", "probes": len(series),
                "price_usd": prices[0] if prices else None, "drift_fields": [],
                "defects": ["not every probe returned a decodable 402"]}
    base = fps[0]
    drift = sorted(k for k in base if any(fp.get(k) != base.get(k) for fp in fps[1:]))
    verdict = "UNSTABLE" if drift else "STABLE"
    return {"name": name, "verdict": verdict, "probes": len(series),
            "price_usd": prices[0] if prices else None, "drift_fields": drift,
            "spread_usd": (round(max(prices) - min(prices), 6) if prices else None),
            "defects": []}


def aggregate(results):
    stable = sum(1 for r in results if r["verdict"] == "STABLE")
    return {
        "probes_per_target": PROBES_PER_TARGET,
        "targets": len(results),
        "stable_targets": stable,
        "determinism_score_pct": round(100.0 * stable / len(results), 1) if results else 0.0,
        "verdict": "DETERMINISTIC" if stable == len(results) else "INSTABILITY_FOUND",
        "hard_drift_targets": [r["name"] for r in results if r["verdict"] in ("DRIFT", "NO_CHALLENGE")],
        "unstable_targets": [r["name"] for r in results if r["verdict"] == "UNSTABLE"],
    }


def good_challenge(amount="5000", payto=CANON):
    chal = {"x402Version": 2, "resource": {"url": "u"},
            "accepts": [{"scheme": "exact", "network": EXACT_NETWORK, "payTo": payto,
                         "asset": BASE_USDC, "amount": amount,
                         "maxTimeoutSeconds": 300,
                         "extra": {"name": "USD Coin", "version": "2"}}]}
    hdr = {"payment-required": base64.b64encode(json.dumps(chal).encode()).decode()}
    return (402, hdr, json.dumps(chal))


def self_test():
    cases = []
    r = grade_series("stable", [good_challenge() for _ in range(3)])
    cases.append(("stable", r["verdict"] == "STABLE" and not r["drift_fields"], r))
    r = grade_series("unstable-price", [good_challenge("5000"), good_challenge("6000"), good_challenge("5000")])
    cases.append(("unstable-price", r["verdict"] == "UNSTABLE" and "amount" in r["drift_fields"], r))
    r = grade_series("unstable-payto", [good_challenge(), good_challenge(payto="0x" + "1" * 40), good_challenge()])
    cases.append(("unstable-payto", r["verdict"] == "DRIFT" and any("payTo" in x for x in r["defects"]), r))
    r = grade_series("free-backdoor", [(200, {}, "{}")] * 3)
    cases.append(("free-backdoor", r["verdict"] == "DRIFT", r))
    r = grade_series("one-nochallenge", [good_challenge(), (0, {}, "ERR"), good_challenge()])
    cases.append(("one-nochallenge", r["verdict"] == "DRIFT" or r["verdict"] == "NO_CHALLENGE", r))
    ok = all(p for _, p, _ in cases)
    for n, p, _ in cases:
        print("  %-20s %s" % (n, "PASS" if p else "FAIL"))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="nonzero on hard drift/instability")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--json", action="store_true", help="emit full JSON snapshot")
    args = ap.parse_args()
    if args.self_test:
        print("SELF-TEST:"); return 0 if self_test() else 1
    results = []
    for t in PROBES:
        series = []
        for i in range(PROBES_PER_TARGET):
            series.append(fetch(t["url"], t["body"]))
            if i < PROBES_PER_TARGET - 1:
                time.sleep(1)
        results.append(grade_series(t["name"], series))
    agg = aggregate(results)
    if args.json:
        print(json.dumps({"generated_by": "Innovation 65 determinism auditor",
                          "results": results, "aggregate": agg}, indent=2))
        bad = sum(1 for r in results if r["verdict"] != "STABLE")
        return 1 if (args.check and bad) else 0
    print("=== X402 CHALLENGE DETERMINISM (3x identical unpaid probes) ===")
    for r in results:
        price = ("$%.3f" % r["price_usd"]) if r["price_usd"] is not None else "-"
        print("%-22s %-12s %-8s probes=%d drift=%s" %
              (r["name"], r["verdict"], price, r["probes"], ",".join(r.get("drift_fields", [])) or "-"))
        for x in r["defects"]: print("    DEFECT:", x)
    print("\nAGGREGATE:", json.dumps(agg))
    bad = sum(1 for r in results if r["verdict"] != "STABLE")
    print("\nSUMMARY: %d/%d stable targets, determinism=%s%%, verdict=%s" %
          (len(results) - bad, len(results), agg["determinism_score_pct"], agg["verdict"]))
    return 1 if (args.check and bad) else 0


if __name__ == "__main__":
    sys.exit(main())
