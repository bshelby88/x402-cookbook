#!/usr/bin/env python3
"""playground-walkthrough.py — verify the RAEN /playground buyer surface and emit a truth-labelled walkthrough content pack (Recipe 37).

Read-only, stdlib-only. No signing, no X-PAYMENT, no RPC money calls, no secrets,
no funds movement, no external sends. Sends only unpaid GET/POST probes.

The /playground page hardcodes a list of walls and prices. Those prices are a
buyer-facing claim, and like any doc claim they can drift from the live 402.
A machine buyer who follows a stale price misroutes funds or abandons the first
paid call. This tool:

  1. GETs the live /playground HTML (free) and parses every advertised wall+price.
  2. Re-probes only KEPT-LIVE walls with an unpaid POST and decodes the x402 v2
     challenge (accepts[0]: amount / payTo / network / scheme).
  3. Compares each advertised price to the live price and flags drift.
  4. Labels frozen walls as NOT VERIFIED (BURN FREEZE) - never probed, never
     recommended for a first paid call.
  5. Emits machine-readable JSON and a buyer-facing Markdown walkthrough whose
     prices come ONLY from live 402s, with the canonical payTo spelled out in full.

Exit codes: 0 CLEAN (all probed walls canonical, no price drift),
            1 DRIFT (noncanonical payTo / wrong network+scheme / price mismatch),
            2 UNREACHABLE (playground AND all probes failed).
"""
import argparse, base64, datetime, json, re, sys, urllib.error, urllib.request

CANON = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f"
RETIRED = "0x7861db4efc14a1ed5dd8c96c528a3796560f1393"
AGENTCASH = "0xfbc0eb7811d477e55261d956df39f0046e192240"
PLAYGROUND = "https://rae-fleet-router.fly.dev/playground"
UA = {"User-Agent": "Mozilla/5.0 (compatible; RAEN-playground-walkthrough/1.0)",
      "Accept": "*/*", "Content-Type": "application/json"}

# Kept-live services only (BURN FREEZE, owner order). Frozen services are never
# probed - they are classified from the advertised list and labelled NOT VERIFIED.
KEEP_LIVE = {"royal-ruby", "contract-eye", "gateway", "nanobanana",
             "raen-mcp-gateway", "raen-facilitator", "settlement-collector",
             "raen-library"}

# Unpaid POST probes with a known-good body for each kept-live wall that can be
# verified from this tool. Reference walls need not appear on the playground page.
PROBES = [
    {"svc": "royal-ruby", "base": "https://royal-ruby-x402.fly.dev",
     "path": "/api/law-lookup", "body": '{"query":"FCRA 611"}'},
    {"svc": "contract-eye", "base": "https://contract-eye-x402.fly.dev",
     "path": "/api/analyze-contract",
     "body": '{"text":"liability limits and twelve month renewal"}'},
    {"svc": "gateway", "base": "https://raen-mcp-gateway.fly.dev",
     "path": "/mcp",
     "body": '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"raen_law_lookup","arguments":{"query":"FCRA"}}}'},
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


def role(addr):
    a = (addr or "").lower()
    if a == CANON:
        return "CANONICAL"
    if a == RETIRED:
        return "RETIRED"
    if a == AGENTCASH:
        return "INTERNAL_AGENTCASH"
    return "UNKNOWN"


def parse_playground(html):
    """Return list of {service, method, path, advertised_usd} from the HTML."""
    walls = []
    for m in re.finditer(r"<option value=\"\d+\">(.*?)</option>", html, re.S):
        text = re.sub(r"\s+", " ", m.group(1)).strip()
        # e.g. 'royal-ruby-x402 — POST /api/law-lookup ($0.25)'
        if "—" not in text:
            continue
        service, rest = [p.strip() for p in text.split("—", 1)]
        parts = rest.split()
        if len(parts) < 2:
            continue
        method, path = parts[0].upper(), parts[1]
        pm = re.search(r"\(\$([\d.]+)\)", rest)
        price = float(pm.group(1)) if pm else None
        walls.append({"service": service, "method": method, "path": path,
                      "advertised_usd": price, "text": text})
    return walls


def norm(svc):
    """Normalize a playground service label to a probe key."""
    s = svc.lower().strip()
    for suffix in ("-x402", "_x402"):
        if s.endswith(suffix):
            s = s[:-len(suffix)]
    s = s.replace("raen-mcp-gateway", "gateway")
    return s


def probe(spec):
    code, hdrs, _ = get(spec["base"] + spec["path"], "POST", spec["body"])
    ch = decode_challenge(hdrs)
    out = {"svc": spec["svc"], "route": spec["path"], "http": code,
           "payto": None, "payto_role": "NONE", "network": None, "scheme": None,
           "amount_usd": None, "amount_atomic": None, "ok": False}
    if ch and ch.get("accepts"):
        a = ch["accepts"][0]
        amt = a.get("amount")
        try:
            amt = int(amt)
        except (TypeError, ValueError):
            amt = None
        out.update({
            "payto": a.get("payTo"), "payto_role": role(a.get("payTo")),
            "network": a.get("network"), "scheme": a.get("scheme"),
            "amount_atomic": amt,
            "amount_usd": (amt / 1_000_000) if amt is not None else None,
            "ok": (code == 402 and role(a.get("payTo")) == "CANONICAL"
                   and a.get("network") == "eip155:8453" and a.get("scheme") == "exact"),
        })
    return out


def build(playground_url):
    code, _, html = get(playground_url)
    walls = parse_playground(html) if html else []
    probes = [probe(p) for p in PROBES]
    # Classify every advertised wall. Frozen == never probed, never recommended.
    classified = []
    for w in walls:
        key = norm(w["service"])
        live = None
        for p in probes:
            if p["svc"] == key and p["route"] == w["path"]:
                live = p
                break
        if live:
            drift = (live["amount_usd"] is not None
                     and w["advertised_usd"] is not None
                     and abs(live["amount_usd"] - w["advertised_usd"]) > 1e-9)
            classified.append({**w, "status": "VERIFIED",
                               "live_usd": live["amount_usd"],
                               "price_drift": drift,
                               "payto_role": live["payto_role"]})
        elif key in KEEP_LIVE:
            classified.append({**w, "status": "KEPT-LIVE / no probe recipe",
                               "live_usd": None, "price_drift": None,
                               "payto_role": None})
        else:
            classified.append({**w, "status": "NOT VERIFIED (frozen)",
                               "live_usd": None, "price_drift": None,
                               "payto_role": None})

    all_ok = (code == 402 or code == 200) and bool(walls) and all(p["ok"] for p in probes)
    no_drift = not any(w["price_drift"] for w in classified)
    if not walls and not any(p["http"] for p in probes):
        verdict = "UNREACHABLE"
    elif all_ok and no_drift:
        verdict = "CLEAN"
    else:
        verdict = "DRIFT"

    return {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "tool": "playground-walkthrough/1.0", "playground_url": playground_url,
        "playground_http": code, "verdict": verdict,
        "canonical_payto": CANON, "chain": "eip155:8453", "scheme": "exact",
        "truth_notes": [
            "Price truth = a fresh live 402 challenge (accepts[0].amount), never the hardcoded playground price.",
            "Many 402 challenges are scanners/bots; challenges are not sales. See Recipe 36.",
            "Internal self-pays (AgentCash) are not external revenue.",
            "Frozen walls are labelled NOT VERIFIED and are never probed (BURN FREEZE).",
            "Chain-coverage: this verifies Base (eip155:8453) only - the chain RAEN walls settle on.",
        ],
        "verified_walls": probes, "advertised_walls": classified,
        "drift_count": sum(1 for w in classified if w["price_drift"]),
    }


def markdown(rep):
    L = ["# x402 Playground — verified walkthrough content pack (Recipe 37)", "",
         "**Status:** %s · generated %s" % (rep["verdict"], rep["generated_at"]),
         "**Playground:** %s (HTTP %s)" % (rep["playground_url"], rep["playground_http"]), "",
         "This pack turns the /playground into a trustworthy *machine-buyer* asset. It",
         "re-probes kept-live walls with unpaid POSTs and uses ONLY the live 402 price.", "",
         "## Truth rules (read first)", ""]
    for n in rep["truth_notes"]:
        L.append("- " + n)
    L += ["", "Canonical payTo (full 42 chars): `%s`" % rep["canonical_payto"],
          "Chain `%s` · scheme `%s`" % (rep["chain"], rep["scheme"]), "",
          "## Verified walls (fresh unpaid 402 decode)", "",
          "| wall | HTTP | live price | payTo role | network | scheme |",
          "|------|------|-----------:|------------|---------|--------|"]
    for p in rep["verified_walls"]:
        price = ("$%.6g" % p["amount_usd"]) if p["amount_usd"] is not None else "—"
        L.append("| %s | %s | %s | %s | %s | %s |" % (
            p["svc"], p["http"], price, p["payto_role"], p["network"], p["scheme"]))
    L += ["", "## Advertised playground walls vs live truth", "",
          "| advertised wall | advertised | live | status |",
          "|-----------------|-----------:|-----:|--------|"]
    for w in rep["advertised_walls"]:
        adv = ("$%.6g" % w["advertised_usd"]) if w["advertised_usd"] is not None else "—"
        live = ("$%.6g" % w["live_usd"]) if w["live_usd"] is not None else "not probed"
        flag = " ⚠️ DRIFT" if w["price_drift"] else ""
        L.append("| %s %s | %s | %s | %s%s |" % (
            w["service"], w["path"], adv, live, w["status"], flag))
    L += ["", "Price-drift walls: **%d**" % rep["drift_count"], "",
          "## Walkthrough a machine buyer can follow", "",
          "1. **Preflight** (free): `python3 scripts/buyer-preflight.py` — verify the wall before you sign (Recipe 23).",
          "2. **Unpaid POST** to the wall → HTTP 402. Decode `payment-required` (base64 JSON); `accepts[0]` is authoritative.",
          "3. **Build the payment** for `accepts[0].amount` (micro-USDC) to the canonical payTo above on `eip155:8453`, scheme `exact` (EIP-3009 `transferWithAuthorization`).",
          "4. **Retry the POST** with the `X-PAYMENT` header. Never reuse a signature.",
          "5. **Prove it landed**: `python3 scripts/receipt-verifier.py <tx>` — chain truth, no seller trust (Recipe 27).",
          "",
          "For a first paid call, use a wall marked VERIFIED above at its **live** price —",
          "not a frozen wall and not a stale advertised price.", ""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", default=PLAYGROUND)
    ap.add_argument("--json", dest="json_path")
    ap.add_argument("--md", dest="md_path")
    a = ap.parse_args()
    rep = build(a.url)
    js = json.dumps(rep, indent=2)
    md = markdown(rep)
    if a.json_path:
        open(a.json_path, "w", encoding="utf-8").write(js)
    if a.md_path:
        open(a.md_path, "w", encoding="utf-8").write(md)
    print(js)
    print("\n" + md)
    print("\nVERDICT", rep["verdict"], "| advertised walls", len(rep["advertised_walls"]),
          "| verified probes", len(rep["verified_walls"]),
          "| drift", rep["drift_count"])
    return {"CLEAN": 0, "DRIFT": 1, "UNREACHABLE": 2}[rep["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
