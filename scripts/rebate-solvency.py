#!/usr/bin/env python3
"""
rebate-solvency.py -- Rebate Promise Solvency Auditor (x402-cookbook tool 67)

THE GAP (why this tool exists):
  Tools 23/24/46/61 grade the price, 42/48/57/62/65 grade the challenge,
  64 grades whether a first-call-free / charge-and-rebate hook is DISCLOSED
  in the live 402. NONE checks whether the promise is actually SOLVENT -- i.e.
  whether the rebater rail is enabled, its treasury is the expected internal
  wallet, and that wallet holds enough USDC AND Base gas to honour the rebate.
  A "net cost $0" hook backed by a dry or disabled rail is a conversion killer
  and a TRUTH violation: the buyer pays full price expecting a rebate.

WHAT IT DOES (all read-only, stdlib-only):
  1. Reads the advertised rebate promise from the wall's live manifest + OpenAPI.
  2. Decodes the live unpaid POST 402 (price/payTo/scheme/network) -- the
     "full charged amount" that the promise says will be rebated.
  3. Fetches rebater /health (non-secret facts: treasury, enabled, caps).
  4. Classifies the treasury against full-form known internal addresses
     (poison-homoglyph safe) -- a drift to an unknown address is a hard fail.
  5. Reads treasury USDC + native gas on Base via eth_call, chainId 0x2105
     validated on >=2 independent RPCs with consensus (a single RPC is not
     evidence).
  6. Grades SOLVENT / UNFUNDED / DISABLED / TREASURY_DRIFT / LOW_GAS /
     CAP_EXCEEDS_FLOAT / PROMISE_PRICE_MISMATCH / NO_PROMISE / NO_CONSENSUS.

NEVER: signs, pays, sends X-PAYMENT, moves funds, changes a price, deploys,
or displays a secret. `--check` fails only on a hard solvency break.
"""
import argparse, base64, json, sys, time, urllib.error, urllib.request

WALL = "https://royal-ruby-x402.fly.dev"
PAID_ROUTE = WALL + "/api/law-lookup"
MANIFEST = WALL + "/.well-known/x402.json"
OPENAPI = WALL + "/openapi.json"
REBATER_HEALTH = "https://royal-ruby-rebater.fly.dev/health"

USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
BASE_CHAIN_ID = "0x2105"
RPCS = [
    "https://base.publicnode.com",
    "https://mainnet.base.org",
    "https://base.drpc.org",
]

# FULL 42-char addresses only -- poison homoglyphs differ by 1-2 chars.
INTERNAL = {
    "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f": "INTERNAL_CANONICAL",
    "0x7861db4efc14a1ed5dd8c96c528a3796560f1393": "INTERNAL_RETIRED",
    "0xfbc0eb7811d477e55261d956df39f0046e192240": "INTERNAL_AGENTCASH",
}
REBATE_KEYWORDS = ("rebate", "free first call", "free-first", "net cost",
                   "charge-and-rebate", "x-payer-address")
HARD_FAIL = {"UNFUNDED", "DISABLED", "TREASURY_DRIFT", "NO_CONSENSUS",
             "MALFORMED", "NO_PROMISE_HEALTH_UNREACHABLE"}
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def fetch(url, method="GET", data=None, headers=None):
    h = dict(UA)
    if headers:
        h.update(headers)
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        r = urllib.request.urlopen(req, timeout=25)
        return r.status, r.read().decode("utf-8", "replace"), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), dict(e.headers)
    except Exception as e:
        return 0, "ERR:" + str(e), {}


def decode_challenge(header_or_body, label):
    """Decode an x402 v2 payment-required base64 JSON blob."""
    if not header_or_body:
        return None
    raw = header_or_body.strip()
    try:
        if raw.startswith("ey") or raw.startswith("{"):
            try:
                obj = json.loads(base64.b64decode(raw + "===").decode("utf-8"))
            except Exception:
                obj = json.loads(raw)
            return obj
    except Exception:
        return None
    return None


def advertised_promise():
    """Return (promise_found, advertised_usd, evidence[]) from public docs."""
    evidence = []
    corpus = []
    for url in (MANIFEST, OPENAPI):
        s, b, _ = fetch(url)
        if s == 200:
            corpus.append(b)
            low = b.lower()
            for kw in REBATE_KEYWORDS:
                if kw in low:
                    evidence.append("%s: contains %r" % (url.split("/")[-1], kw))
    text = "\n".join(corpus).lower()
    found = any(k in text for k in REBATE_KEYWORDS)
    adv = None
    # "rebated $0.005 USDC" / "rebates the full $0.005" etc.
    import re
    # Anchor on the explicit rebate figure, NOT on "net cost $0" (which would
    # falsely parse as $0). Prefer "rebated $0.005 USDC"; fall back to the
    # "normal $0.005 challenge ... immediately rebated" phrasing.
    for pat in (r"rebate\w*\s*\$\s*([0-9]+\.?[0-9]*)\s*usdc",
                r"\$\s*([0-9]+\.?[0-9]*)\s*challenge[^.]{0,80}?rebate\w*"):
        m = re.search(pat, text)
        if m:
            try:
                adv = float(m.group(1))
                break
            except ValueError:
                pass
    return found, adv, evidence


def live_402():
    """Unpaid POST probe -> canonical envelope + amount in USD."""
    s, b, h = fetch(PAID_ROUTE, method="POST",
                    data={"topic": "consumer rights", "state": "federal-only",
                          "scope": "federal"})
    hdr = None
    for k, v in h.items():
        if k.lower() in ("payment-required", "x-payment-required"):
            hdr = v
    obj = decode_challenge(hdr, "header")
    if obj is None:
        obj = decode_challenge(b, "body")
    if not obj:
        return {"probe_status": s, "decoded": False}
    acc = (obj.get("accepts") or [{}])[0]
    try:
        amount_usd = int(acc.get("amount", "0")) / 1e6
    except (TypeError, ValueError):
        amount_usd = None
    return {
        "probe_status": s,
        "decoded": True,
        "x402_version": obj.get("x402Version"),
        "scheme": acc.get("scheme"),
        "network": acc.get("network"),
        "payTo": acc.get("payTo"),
        "amount_usd": amount_usd,
        "max_timeout_seconds": acc.get("maxTimeoutSeconds"),
    }


def rebater_health():
    s, b, _ = fetch(REBATER_HEALTH)
    if s != 200:
        return {"status": s, "reachable": False}
    try:
        o = json.loads(b)
    except Exception:
        return {"status": s, "reachable": False, "error": "non-JSON health"}
    return {
        "status": s,
        "reachable": True,
        "service": o.get("service"),
        "treasury": o.get("treasury"),
        "rebatesEnabled": o.get("rebatesEnabled"),
        "rebateCountToday": o.get("rebateCountToday"),
        "dailyCap": o.get("dailyCap"),
    }


def treasury_role(addr):
    if not isinstance(addr, str) or len(addr) != 42 or not addr.startswith("0x"):
        return "MALFORMED"
    try:
        int(addr[2:], 16)
    except ValueError:
        return "MALFORMED"
    return INTERNAL.get(addr.lower(), "UNKNOWN_ADDRESS")


def balance_consensus(treasury):
    """Return dict with USDC + gas from >=2 agreeing RPCs (chainId guarded)."""
    bal_sel = "0x70a08231" + "0" * 24 + treasury[2:].lower()
    clean = []
    for url in RPCS:
        cid, _, _ = rpc(url, "eth_chainId", [])
        if cid != BASE_CHAIN_ID:
            continue
        usdc_raw, _, _ = rpc(url, "eth_call",
                             [{"to": USDC_BASE, "data": bal_sel}, "latest"])
        gas_raw, _, _ = rpc(url, "eth_getBalance", [treasury, "latest"])
        if not (isinstance(usdc_raw, str) and usdc_raw.startswith("0x")):
            continue
        if not (isinstance(gas_raw, str) and gas_raw.startswith("0x")):
            continue
        clean.append((int(usdc_raw, 16) / 1e6, int(gas_raw, 16) / 1e18))
        time.sleep(0.5)
    if len(clean) < 2:
        return {"consensus": False, "clean_rpcs": len(clean)}
    usdc_vals = [round(x[0], 6) for x in clean]
    if len(set(usdc_vals)) != 1:
        return {"consensus": False, "clean_rpcs": len(clean),
                "usdc_values": usdc_vals}
    return {"consensus": True, "clean_rpcs": len(clean),
            "usdc": usdc_vals[0], "gas_eth": clean[0][1]}


def rpc(url, method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1,
                       "method": method, "params": params}).encode()
    req = urllib.request.Request(url, data=body, headers=UA, method="POST")
    try:
        r = urllib.request.urlopen(req, timeout=25)
        o = json.loads(r.read().decode("utf-8", "replace"))
        return o.get("result"), None, o.get("error")
    except Exception as e:
        return None, None, str(e)


def grade(promise, health, bal, ch):
    adv = promise.get("advertised_usd")
    live = ch.get("amount_usd")
    rebate = live if live is not None else adv
    notes = []
    verdict = "SOLVENT"
    if not promise.get("found"):
        return "NO_PROMISE", rebate, ["no rebate promise found in public docs"]
    if not health.get("reachable"):
        return "NO_PROMISE_HEALTH_UNREACHABLE", rebate, ["rebater /health unreachable"]
    if health.get("rebatesEnabled") is not True:
        return "DISABLED", rebate, ["rebatesEnabled is not true"]
    role = treasury_role(health.get("treasury"))
    if role in ("MALFORMED", "UNKNOWN_ADDRESS"):
        return "TREASURY_DRIFT", rebate, ["treasury=%s role=%s" % (health.get("treasury"), role)]
    if not bal.get("consensus"):
        return "NO_CONSENSUS", rebate, ["USDC balance consensus failed"]
    usdc = bal["usdc"]
    gas = bal.get("gas_eth", 0)
    if rebate is None or rebate <= 0:
        return "MALFORMED", rebate, ["could not resolve rebate amount"]
    if usdc < rebate:
        return "UNFUNDED", rebate, ["treasury USDC %.6f < rebate %.6f" % (usdc, rebate)]
    coverage = int(usdc / rebate)
    cap = health.get("dailyCap")
    if isinstance(cap, int) and cap * rebate > usdc:
        notes.append("CAP_EXCEEDS_FLOAT: dailyCap %d x $%.4f > float $%.4f"
                     % (cap, rebate, usdc))
        if verdict == "SOLVENT":
            verdict = "CAP_EXCEEDS_FLOAT"
    if gas < 0.00005:
        notes.append("LOW_GAS: treasury Base gas %.6f ETH" % gas)
        if verdict == "SOLVENT":
            verdict = "LOW_GAS"
    if adv is not None and live is not None and abs(adv - live) > 1e-9:
        notes.append("PROMISE_PRICE_MISMATCH: advertised $%.4f vs live 402 $%.4f"
                     % (adv, live))
        if verdict == "SOLVENT":
            verdict = "PROMISE_PRICE_MISMATCH"
    notes.insert(0, "SOLVENT: %d rebates coverable at $%.4f; float $%.4f; gas %.6f ETH"
                 % (coverage, rebate, usdc, gas))
    return verdict, rebate, notes


def main():
    ap = argparse.ArgumentParser(description="Rebate Promise Solvency Auditor")
    ap.add_argument("--out", help="write JSON report to this path")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 only on a hard solvency break")
    args = ap.parse_args()

    promise_found, adv, evidence = advertised_promise()
    ch = live_402()
    health = rebater_health()
    bal = {}
    if health.get("reachable"):
        bal = balance_consensus(health.get("treasury") or "")
    verdict, rebate, notes = grade(
        {"found": promise_found, "advertised_usd": adv}, health, bal, ch)

    report = {
        "tool": "rebate-solvency",
        "version": 1,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "verdict": verdict,
        "promise": {"found": promise_found, "advertised_rebate_usd": adv,
                    "evidence": evidence},
        "live_402": ch,
        "rebater": health,
        "treasury_role": treasury_role(health.get("treasury")) if health.get("reachable") else None,
        "treasury_balance": bal,
        "rebate_per_call_usd": rebate,
        "notes": notes,
        "hard_fail": verdict in HARD_FAIL,
        "read_only": True,
    }
    out = json.dumps(report, indent=2)
    print(out)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out + "\n")
    if args.check and verdict in HARD_FAIL:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
