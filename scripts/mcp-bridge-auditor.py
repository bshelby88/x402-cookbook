#!/usr/bin/env python3
"""MCP Buyer-Bridge Auditor - tool 57 (RAEN x402 cookbook).

Read-only, stdlib-only. Grades the MCP tool surface an autonomous buyer
actually meets: tools/list discovery, per-tool input schema, advertised
price vs the LIVE 402 challenge, canonical payTo, and free-backdoor refusal.

NO signing, NO X-PAYMENT, NO funds movement, NO deploy, NO external sends.
Pricing is owner-gated: this tool REPORTS drift, never changes a price.
"""
import argparse, base64, json, re, sys, urllib.error, urllib.request

CANON = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f"
EXACT_NETWORK = "eip155:8453"
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
}


def rpc(url, method, params, rid=1, timeout=40):
    body = json.dumps({"jsonrpc": "2.0", "id": rid, "method": method, "params": params}).encode()
    req = urllib.request.Request(url, data=body, headers=UA, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8", "replace")
    except Exception as e:  # network/DNS failure is a finding, not a crash
        return 0, {}, "ERR " + repr(e)


def parse_mcp(body):
    """MCP may return plain JSON or SSE data: frames."""
    if "data:" in body:
        body = "\n".join(l[5:].strip() for l in body.splitlines() if l.startswith("data:"))
    return json.loads(body)


def decode_challenge(headers, body):
    raw = None
    for k, v in headers.items():
        if k.lower() in ("payment-required", "x-payment-required"):
            raw = v
            break
    if raw:
        try:
            padded = raw + "=" * (-len(raw) % 4)
            return json.loads(base64.b64decode(padded))
        except Exception:
            pass
    # Fallback: some servers echo accepts[] in the JSON body.
    try:
        j = json.loads(body)
        if "accepts" in j:
            return j
    except Exception:
        pass
    return None


def price_from_description(desc):
    m = re.search(r"\$\s*([0-9]+(?:\.[0-9]+)?)\s*(?:USDC)?", desc or "", re.I)
    return float(m.group(1)) if m else None


def audit(url):
    snap = {"tool": "mcp-bridge-auditor", "version": 1, "gateway_url": url,
            "checks": [], "status": "OK", "findings": [],
            "doctrine": "report price drift, never change owner-gated pricing"}
    st, hdrs, body = rpc(url, "tools/list", {})
    if st != 200:
        snap["status"] = "UNREACHABLE"
        snap["findings"].append("tools/list HTTP %s - bridge is down or gated" % st)
        return snap
    try:
        tools = parse_mcp(body).get("result", {}).get("tools", [])
    except Exception as e:
        snap["status"] = "BAD_TOOLS_LIST"
        snap["findings"].append("tools/list unparseable: %r" % e)
        return snap

    snap["tools_advertised"] = len(tools)
    if not tools:
        snap["findings"].append("tools/list returned 0 tools - buyer sees nothing to buy")

    for t in tools:
        name = t.get("name", "?")
        desc = t.get("description", "") or ""
        adv = price_from_description(desc)
        schema = t.get("inputSchema", {})
        required = schema.get("required", []) if isinstance(schema, dict) else []
        row = {"tool": name, "advertised_usd": adv, "required": required,
               "has_input_schema": bool(schema), "live": None, "flags": []}

        # A NONEXISTENT tool name is used nowhere: we probe only real tool names,
        # and we NEVER send X-PAYMENT, so no paid tool can execute.
        st2, h2, b2 = rpc(url, "tools/call", {"name": name, "arguments": {}}, rid=2)
        ch = decode_challenge(h2, b2)
        if st2 == 200:
            row["flags"].append("FREE_BACKDOOR")
            snap["findings"].append("%s: tools/call returned 200 with no payment (free execution)" % name)
        elif st2 == 402 and ch:
            acc = (ch.get("accepts") or [{}])[0]
            try:
                live = int(acc.get("amount", "0")) / 1e6
            except Exception:
                live = None
            payto = str(acc.get("payTo", ""))
            row["live"] = {"usd": live, "amount_atoms": acc.get("amount"),
                           "scheme": acc.get("scheme"), "network": acc.get("network"),
                           "payTo": payto}
            if str(acc.get("scheme", "")).lower() != "exact":
                row["flags"].append("SCHEME_DRIFT")
            if acc.get("network") != EXACT_NETWORK:
                row["flags"].append("NETWORK_DRIFT")
            if payto.lower() != CANON.lower():
                row["flags"].append("PAYTO_DRIFT")
                snap["findings"].append("%s: payTo is NOT canonical (%s)" % (name, payto[:12] + "…"))
            if adv is not None and live is not None and abs(adv - live) > 1e-9:
                row["flags"].append("PRICE_DRIFT")
                snap["findings"].append("%s: description says $%.3f but live 402 charges $%.3f"
                                        % (name, adv, live))
        else:
            row["flags"].append("UNCHALLENGED")
            snap["findings"].append("%s: expected 402 challenge, got HTTP %s" % (name, st2))
        if not required:
            row["flags"].append("NO_REQUIRED_FIELDS")
        snap["checks"].append(row)

    hard = {"PAYTO_DRIFT", "FREE_BACKDOOR", "SCHEME_DRIFT", "NETWORK_DRIFT"}
    if any(f in r["flags"] for r in snap["checks"] for f in hard):
        snap["status"] = "FAIL"
    elif any("PRICE_DRIFT" in r["flags"] for r in snap["checks"]):
        snap["status"] = "DRIFT_WARN"
    return snap


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="https://raen-mcp-gateway.fly.dev/mcp")
    ap.add_argument("--check", action="store_true", help="exit 1 on hard drift (payTo/scheme/network/free-backdoor)")
    ap.add_argument("--out", help="write JSON snapshot to this path")
    a = ap.parse_args()
    snap = audit(a.url)
    text = json.dumps(snap, indent=2)
    print(text)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    if a.check and snap["status"] == "FAIL":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
