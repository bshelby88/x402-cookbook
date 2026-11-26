#!/usr/bin/env python3
"""llms-lint.py — buyer-surface discovery-doc linter (Recipe 35).

Read-only, GET/POST-unpaid-only, stdlib-only. No signing, no X-PAYMENT, no RPC
money calls, no funds movement, no external sends.

llms.txt is the first surface an autonomous buyer reads. If it names the wrong
payTo, omits it, or quotes a stale price, the buyer either misroutes funds or
walks away before the live 402 ever gets a chance to tell the truth. This tool
cross-checks each machine-discovery doc against the LIVE 402 challenge and the
canonical address set.

Exit codes: 0 CLEAN, 1 DRIFT (wrong payTo / poison address), 2 all-unreachable.
Gaps (missing llms.txt, missing payTo, stale price) are findings, not crashes.
"""
import argparse, base64, json, re, sys, urllib.error, urllib.request

CANON = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f"
RETIRED = "0x7861db4efc14a1ed5dd8c96c528a3796560f1393"
AGENTCASH = "0xfbc0eb7811d477e55261d956df39f0046e192240"

SURFACES = [
    ("router",       "https://rae-fleet-router.fly.dev/llms.txt"),
    ("royal-ruby",   "https://royal-ruby-x402.fly.dev/llms.txt"),
    ("contract-eye", "https://contract-eye-x402.fly.dev/llms.txt"),
    ("nanobanana",   "https://nanobanana-x402.fly.dev/llms.txt"),
    ("sentry-forge", "https://sentry-forge-x402.fly.dev/llms.txt"),
    ("gateway",      "https://raen-mcp-gateway.fly.dev/llms.txt"),
]

# Live unpaid probes: (service_key, url, method, body_or_None)
LIVE_ROUTES = [
    ("contract-eye", "https://contract-eye-x402.fly.dev/api/analyze-contract", "POST",
     '{"text":"This service agreement governs the parties and includes liability limitations and a twelve month automatic renewal term."}'),
    ("royal-ruby", "https://royal-ruby-x402.fly.dev/api/law-lookup", "POST", '{"query":"FCRA 611"}'),
    ("gateway", "https://raen-mcp-gateway.fly.dev/mcp", "POST",
     '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"raen_law_lookup","arguments":{"query":"FCRA"}}}'),
]

ADDR_RE = re.compile(r"0x[0-9a-fA-F]{40}")
PRICE_RE = re.compile(r"\$\s*([0-9]+(?:\.[0-9]+)?)")
PAY_CONTEXT = re.compile(r"pay\s?to|payer|payment|wallet|remit|send|settlement", re.I)
LISTING_RE = re.compile(r"-\s+([a-z0-9][a-z0-9-]*)\s+[—-].*?\$([0-9]+(?:\.[0-9]+)?)\s*USDC", re.I)


def fetch(url, method="GET", body=None, timeout=25):
    req = urllib.request.Request(
        url, data=body.encode() if body else None, method=method,
        headers={"User-Agent": "Mozilla/5.0 (compatible; RAEN-llms-lint/1.0)",
                 "Accept": "*/*", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8", "replace")
    except Exception:
        return 0, {}, ""


def classify(addr):
    a = addr.lower()
    if a == CANON:
        return "CANONICAL"
    if a == RETIRED:
        return "RETIRED"
    if a == AGENTCASH:
        return "INTERNAL_AGENTCASH"
    return "UNKNOWN"


def decode_challenge(headers):
    raw = None
    for k, v in headers.items():
        if k.lower() in ("payment-required", "x-payment-required"):
            raw = v
            break
    if not raw:
        return None
    try:
        return json.loads(base64.b64decode(raw + "=" * (-len(raw) % 4)))
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(description="Lint RAEN llms.txt buyer surfaces against live 402 truth")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    ap.add_argument("--out", help="write JSON snapshot to this path")
    args = ap.parse_args()

    report = {"tool": "llms-lint/1.0", "canonical_payto": CANON,
              "surfaces": {}, "live_402": {}, "doc_prices": {}, "findings": [], "verdict": ""}

    doc_prices = {}
    reachable = 0
    for name, url in SURFACES:
        code, hdrs, text = fetch(url)
        entry = {"url": url, "http": code, "bytes": len(text)}
        if code == 200 and text:
            reachable += 1
            canon_hits = sum(1 for a in ADDR_RE.findall(text) if a.lower() == CANON)
            entry["canonical_address_hits"] = canon_hits
            pay_addrs = []
            other_addrs = []
            for line in text.splitlines():
                # A labelled watch/tracking line is NOT a payment instruction.
                watch_line = bool(re.search(r"watch|track|stranding|legacy", line, re.I))
                for a in ADDR_RE.findall(line):
                    cl = classify(a)
                    rec = {"address": a, "role": cl}
                    if PAY_CONTEXT.search(line) and not watch_line:
                        pay_addrs.append(rec)
                    else:
                        other_addrs.append(rec)
            entry["addresses_in_payment_context"] = pay_addrs
            entry["other_addresses"] = other_addrs[:8]
            entry["prices"] = sorted(set(PRICE_RE.findall(text)))
            for svc, price in LISTING_RE.findall(text):
                doc_prices.setdefault(svc.lower(), set()).add(price)
                entry.setdefault("listed_services", {})[svc.lower()] = price
            if canon_hits == 0:
                report["findings"].append({"severity": "GAP", "surface": name,
                    "type": "MISSING_CANONICAL_PAYTO",
                    "detail": "no canonical payTo in buyer discovery doc; buyer cannot verify destination"})
            for rec in pay_addrs:
                if rec["role"] in ("RETIRED", "INTERNAL_AGENTCASH", "UNKNOWN"):
                    report["findings"].append({"severity": "DRIFT", "surface": name,
                        "type": "NONCANONICAL_PAYMENT_ADDRESS", "role": rec["role"],
                        "address": rec["address"],
                        "detail": "payment-context address is not canonical; misrouting risk"})
        else:
            report["findings"].append({"severity": "GAP", "surface": name,
                "type": "LLMS_TXT_UNAVAILABLE", "http": code,
                "detail": "machine discovery doc absent; buyer has no index on this surface"})
        report["surfaces"][name] = entry

    for svc, url, method, body in LIVE_ROUTES:
        code, hdrs, text = fetch(url, method, body)
        ch = decode_challenge(hdrs)
        if ch and ch.get("accepts"):
            acc = ch["accepts"][0]
            amount = acc.get("amount")
            live_price = None
            try:
                live_price = str(int(amount) / 1e6)
            except Exception:
                pass
            payto = acc.get("payTo", "")
            net = ch.get("network") or acc.get("network")
            report["live_402"][svc] = {"http": code, "amount_micro": amount,
                "price_usd": live_price, "payTo": payto,
                "payTo_role": classify(payto) if payto else None, "network": net}
            if classify(payto) != "CANONICAL":
                report["findings"].append({"severity": "DRIFT", "surface": svc,
                    "type": "LIVE_PAYTO_NOT_CANONICAL", "role": classify(payto)})
            for dp in doc_prices.get(svc, set()):
                if live_price is not None and abs(float(dp) - float(live_price)) > 1e-9:
                    report["findings"].append({"severity": "GAP", "surface": svc,
                        "type": "STALE_DOC_PRICE", "doc_price_usd": dp,
                        "live_price_usd": live_price,
                        "detail": "directory doc price disagrees with live 402; live challenge authoritative"})
        else:
            report["live_402"][svc] = {"http": code, "challenge": None,
                "detail": "no payment-required header (route may differ); not scored"}

    report["doc_prices"] = {k: sorted(v) for k, v in doc_prices.items()}
    drift = [f for f in report["findings"] if f["severity"] == "DRIFT"]
    gaps = [f for f in report["findings"] if f["severity"] == "GAP"]
    report["verdict"] = ("DRIFT" if drift else ("GAPS" if gaps else "CLEAN"))
    report["summary"] = {"surfaces_up": reachable, "surfaces_total": len(SURFACES),
                         "drift": len(drift), "gaps": len(gaps)}
    if reachable == 0:
        rc = 2
    elif drift:
        rc = 1
    else:
        rc = 0
    out = json.dumps(report, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(out)
    if args.json:
        print(out)
    else:
        print("verdict:", report["verdict"], report["summary"])
        for f in report["findings"]:
            print(" ", f["severity"], f["type"], f.get("surface", ""),
                  f.get("role", ""), f.get("doc_price_usd", ""), f.get("live_price_usd", ""))
    return rc


if __name__ == "__main__":
    sys.exit(main())
