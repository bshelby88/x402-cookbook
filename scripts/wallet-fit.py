#!/usr/bin/env python3
"""RAEN Innovation 49 - Buyer Wallet Fit Check.

Recipes 23/43 grade the WALL. Recipe 33 grades addresses in TEXT. Recipe 27
proves a settlement AFTER paying. Recipe 46 plans a budget from live prices but
never reads the payer's actual chain state. None answers the buyer's own
pre-sign question: "can THIS wallet complete a paid call, and will the payment
be recognized as a real external purchase?"

This tool answers it from the chain alone, before the buyer signs anything:
  * live price / payTo / network from an unpaid 402 challenge (authoritative)
  * Base USDC balanceOf(buyer) with multi-RPC consensus
  * Base ETH gas balance (informational)
  * ETH-mainnet USDC balance (chain-coverage law, informational)
  * buyer role classification: external / internal self-loop / known crawler

READ-ONLY, stdlib-only. No signing, no EIP-3009 authorization, no X-PAYMENT,
no money movement, no deploy, no external send.

Usage:
  python3 scripts/wallet-fit.py 0xBUYER [--wall URL] [--expect-usdc N]
                                [--out-json FILE] [--out-md FILE]
Exit: 0 = READY, 1 = cannot/should not pay, 2 = fetch/unreachable.
"""
import argparse, base64, json, re, sys, time, urllib.error, urllib.request

CANON = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f"
RETIRED = "0x7861db4efc14a1ed5dd8c96c528a3796560f1393"
AGENTCASH = "0xfbc0eb7811d477e55261d956df39f0046e192240"
BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
ETH_USDC = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
KNOWN_CRAWLER = "0xc9c7b38c0942914fc8ea12063bc92dcd3b581670"  # TIFF-BUYER-05 breadth class
DEFAULT_WALL = "https://royal-ruby-x402.fly.dev/api/law-lookup"
BASE_RPCS = ["https://mainnet.base.org", "https://base.publicnode.com", "https://base.drpc.org"]
ETH_RPCS = ["https://ethereum-rpc.publicnode.com", "https://ethereum.publicnode.com"]
UA = {"User-Agent": "Mozilla/5.0 (raen-wallet-fit/1.0)"}


def valid_addr(a):
    return bool(a and re.fullmatch(r"0x[0-9a-fA-F]{40}", a))


def http(method, url, data=None, headers=None):
    h = dict(UA)
    if headers:
        h.update(headers)
    if data is not None and not isinstance(data, bytes):
        data = data.encode()
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        r = urllib.request.urlopen(req, timeout=20)
        return r.status, dict(r.headers.items()), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers.items()), e.read()
    except Exception as e:
        return 0, {}, ("FETCH_ERROR:" + str(e)).encode()


def decode_challenge(headers, body):
    raw = None
    for k, v in headers.items():
        if k.lower() in ("payment-required", "x-payment-required"):
            raw = v
            break
    if not raw:
        # some servers return the challenge in the body
        try:
            j = json.loads(body)
            raw = j.get("paymentRequired") or j.get("payment-required")
            if isinstance(raw, dict):
                return raw
        except Exception:
            pass
    if not raw:
        return None
    if isinstance(raw, dict):
        return raw
    try:
        s = raw.replace("-", "+").replace("_", "/")
        s += "=" * (-len(s) % 4)
        return json.loads(base64.b64decode(s).decode("utf-8", "replace"))
    except Exception:
        return None


def live_price(wall):
    code, headers, body = http("GET", wall)
    ch = decode_challenge(headers, body)
    info = {"wall": wall, "http_status": code}
    if code != 402 or not ch:
        info["note"] = "no decodable 402 from wall; fall back to --expect-usdc"
        return info, None
    accepts = ch.get("accepts") or []
    if not accepts:
        info["note"] = "402 envelope has no accepts[]"
        return info, None
    a = accepts[0]
    info.update({
        "scheme": a.get("scheme"),
        "network": a.get("network"),
        "asset": a.get("asset"),
        "payto": a.get("payTo"),
        "amount_atomic": a.get("amount"),
        "price_usdc": (round(int(a["amount"]) / 1e6, 6)
                       if str(a.get("amount", "")).isdigit() else None),
        "payto_canonical": str(a.get("payTo", "")).lower() == CANON.lower(),
    })
    return info, info.get("price_usdc")


def rpc_call(url, method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    code, _, raw = http("POST", url, data=body, headers={"Content-Type": "application/json"})
    try:
        return json.loads(raw)
    except Exception:
        return {"error": "http %s / %s" % (code, raw[:60].decode("utf-8", "replace"))}


def balance_of(rpc_list, token, holder):
    data = "0x70a08231" + holder[2:].lower().rjust(64, "0")
    vals = []
    for u in rpc_list:
        res = rpc_call(u, "eth_call", [{"to": token, "data": data}, "latest"])
        v = res.get("result")
        if isinstance(v, str) and v.startswith("0x") and len(v) > 2:
            vals.append(round(int(v, 16) / 1e6, 6))
        time.sleep(0.4)
    if not vals:
        return {"value": None, "consensus": False, "reads": []}
    # consensus = most common value; require >=2 matching reads when >1 read
    counts = {}
    for v in vals:
        counts[v] = counts.get(v, 0) + 1
    best = max(counts, key=counts.get)
    return {"value": best, "consensus": (len(vals) == 1 or counts[best] >= 2),
            "reads": vals, "agreeing": counts[best]}


def gas_balance(rpc_list, holder):
    vals = []
    for u in rpc_list:
        res = rpc_call(u, "eth_getBalance", [holder, "latest"])
        v = res.get("result")
        if isinstance(v, str) and v.startswith("0x") and len(v) > 2:
            vals.append(round(int(v, 16) / 1e18, 8))
        time.sleep(0.4)
    if not vals:
        return {"value_eth": None, "consensus": False}
    return {"value_eth": max(vals, key=vals.count), "consensus": True, "reads": vals}


def classify_buyer(addr):
    a = addr.lower()
    if a == CANON.lower():
        return "INTERNAL_CANONICAL", "payment would be a self-loop, not external revenue"
    if a == RETIRED.lower():
        return "INTERNAL_RETIRED", "retired treasury; never a real external buyer"
    if a == AGENTCASH.lower():
        return "INTERNAL_AGENTCASH", "internal funding wallet; testing, never revenue"
    if a == KNOWN_CRAWLER.lower():
        return "KNOWN_CRAWLER", "TIFF-BUYER-05 breadth class (156 payees/6.4d, p50 $0.003); dust-excluded, NOT demand"
    return "EXTERNAL_BUYER", "not a known internal wallet or recorded breadth-crawler"


def main():
    ap = argparse.ArgumentParser(description="RAEN Innovation 49 - Buyer Wallet Fit Check")
    ap.add_argument("address", help="buyer's own 42-char Base address")
    ap.add_argument("--wall", default=DEFAULT_WALL, help="paid wall to read a live price from (GET, unpaid)")
    ap.add_argument("--expect-usdc", type=float, default=None, help="fallback price if the wall is unreachable")
    ap.add_argument("--out-json", default=None)
    ap.add_argument("--out-md", default=None)
    args = ap.parse_args()

    if not valid_addr(args.address):
        print("ERROR: buyer address must be a full 42-character 0x address", file=sys.stderr)
        return 2

    wall_info, live_price_usdc = live_price(args.wall)
    required = live_price_usdc if live_price_usdc is not None else args.expect_usdc
    price_source = "live_402" if live_price_usdc is not None else ("expect_usdc" if args.expect_usdc is not None else "default_0.01")
    if required is None:
        required = 0.01

    usdc_base = balance_of(BASE_RPCS, BASE_USDC, args.address)
    usdc_eth = balance_of(ETH_RPCS, ETH_USDC, args.address)
    gas = gas_balance(BASE_RPCS[:2], args.address)
    role, role_note = classify_buyer(args.address)

    drift = False
    if wall_info.get("payto_canonical") is False:
        drift = True
    elif wall_info.get("payto_canonical") is None and args.expect_usdc is None:
        # no live challenge and no explicit price -> cannot assert canonical
        drift = True

    if drift:
        verdict = "DRIFT"
        reason = "live wall payTo is not canonical (or unverifiable) - ABSTAIN"
    elif role != "EXTERNAL_BUYER":
        verdict, reason = role, role_note
    elif not usdc_base["consensus"] or usdc_base["value"] is None:
        verdict, reason = "UNREACHABLE", "no USDC balance consensus on Base - cannot judge"
    elif usdc_base["value"] < required:
        verdict = "INSUFFICIENT_USDC"
        reason = "Base USDC %.6f < required %.6f" % (usdc_base["value"], required)
    else:
        verdict, reason = "READY", "external wallet with %.6f USDC >= %.6f required" % (usdc_base["value"], required)

    report = {
        "tool": "raen-buyer-wallet-fit", "version": 1, "innovation": 49,
        "buyer": args.address, "verdict": verdict, "reason": reason,
        "required_usdc": required, "price_source": price_source,
        "wall": wall_info,
        "base_usdc": usdc_base, "base_gas_eth": gas, "eth_mainnet_usdc": usdc_eth,
        "buyer_role": role, "role_note": role_note,
        "chain_scope": "Base (eip155:8453) primary; ETH mainnet informational",
        "truth": "chain balances read from public RPCs; live price from unpaid 402; no signing, no funds moved",
    }

    print("Buyer Wallet Fit — %s" % args.address)
    print("  verdict: %s — %s" % (verdict, reason))
    print("  required: %.6f USDC (%s)" % (required, price_source))
    print("  wall: %s payTo_canonical=%s" % (args.wall, wall_info.get("payto_canonical")))
    print("  Base USDC: %s (consensus=%s, reads=%s)" % (usdc_base["value"], usdc_base["consensus"], usdc_base["reads"]))
    print("  Base gas ETH: %s (informational)" % gas.get("value_eth"))
    print("  ETH-mainnet USDC: %s (informational)" % usdc_eth["value"])
    print("  role: %s — %s" % (role, role_note))

    if args.out_json:
        with open(args.out_json, "w") as f:
            json.dump(report, f, indent=2)
    if args.out_md:
        with open(args.out_md, "w") as f:
            f.write("# Buyer Wallet Fit — `%s`\n\n" % args.address)
            f.write("**Verdict: %s** — %s\n\n" % (verdict, reason))
            f.write("| Check | Value |\n|---|---|\n")
            f.write("| Required | %.6f USDC (%s) |\n" % (required, price_source))
            f.write("| Live wall | %s (HTTP %s) |\n" % (args.wall, wall_info.get("http_status")))
            f.write("| payTo canonical | %s |\n" % wall_info.get("payto_canonical"))
            f.write("| Base USDC | %s (consensus %s) |\n" % (usdc_base["value"], usdc_base["consensus"]))
            f.write("| Base gas ETH | %s (informational) |\n" % gas.get("value_eth"))
            f.write("| ETH-mainnet USDC | %s (informational) |\n" % usdc_eth["value"])
            f.write("| Buyer role | %s |\n" % role)
            f.write("\nThe live 402 is authoritative over any snapshot. No funds moved.\n")

    if verdict == "READY":
        return 0
    if verdict == "UNREACHABLE":
        return 2
    return 1


if __name__ == "__main__":
    sys.exit(main())
