#!/usr/bin/env python3
"""Innovation 66 - x402 Facilitator Capability-Discovery Auditor.

The acquisition face tools 1-65 never grade: a spec-compliant autonomous buyer
client discovers a facilitator's supported schemes/networks with GET /supported
(x402 spec v1+v2 section 7.3) BEFORE it builds an EIP-3009 authorization. If that
contract is missing or the wall's advertised kind is not covered, the buyer
cannot even start - regardless of how good the 402 body looks (tools 42/62/65).

Read-only, stdlib-only. Never signs, never pays, never sends X-PAYMENT, never
changes a price, never moves funds.

Usage:  python3 facilitator-support.py [--check] [--json]
"""
import argparse, base64, json, sys, urllib.error, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
FACILITATOR = "https://raen-facilitator.fly.dev"
SPEC_PATH = "/supported"          # x402 spec 7.3, canonical location
RAEN_PATH = "/facilitator/supported"  # RAEN FastAPI prefix (discovered via /openapi.json)
META_PATH = "/facilitator"        # servedPayees / facilitatorAddress
CANON = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f"

# Each kept-live paid surface: (name, url, body). Unpaid POST -> 402 challenge.
WALLS = [
    ("royal-ruby", "https://royal-ruby-x402.fly.dev/api/ping", {"prompt": "ping"}),
    ("contract-eye", "https://contract-eye-x402.fly.dev/api/analyze", {"address": "0x" + "0" * 40}),
    ("nanobanana", "https://nanobanana-x402.fly.dev/api/generate-image", {"prompt": "ping"}),
    ("gateway", "https://raen-mcp-gateway.fly.dev/mcp",
     {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
      "params": {"name": "raen_law_lookup", "arguments": {"query": "ping"}}}),
]


def http(url, method="GET", data=None, timeout=25):
    headers = dict(UA)
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    try:
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()
    except Exception as e:  # noqa: BLE001 - report transport failures, never crash
        return 0, {}, str(e).encode()


def challenge(url, data):
    """Return (requirement dict | None, error str | None) from one unpaid POST."""
    status, headers, body = http(url, "POST", data)
    if status != 402:
        return None, f"HTTP {status} (no 402 challenge)"
    raw = None
    for k, v in headers.items():
        if k.lower() in ("payment-required", "x-payment-required"):
            raw = v
            break
    doc = None
    if raw:
        try:
            doc = json.loads(base64.b64decode(raw))
        except Exception as e:  # noqa: BLE001
            return None, f"bad header base64: {e}"
    if doc is None:
        try:
            parsed = json.loads(body)
            if isinstance(parsed, dict) and "accepts" in parsed:
                doc = parsed
        except Exception:  # noqa: BLE001
            pass
    if doc is None:
        return None, "no decodable payment-required payload"
    acc = (doc.get("accepts") or [None])[0]
    if not isinstance(acc, dict):
        return None, "empty accepts[]"
    return {
        "x402Version": doc.get("x402Version"),
        "scheme": acc.get("scheme"),
        "network": acc.get("network"),
        "asset": acc.get("asset"),
        "payTo": acc.get("payTo"),
        "amount": acc.get("amount"),
    }, None


def supported(path):
    """Probe a facilitator capability-discovery path; validate the spec contract."""
    status, _, body = http(FACILITATOR + path)
    out = {"path": path, "http_status": status, "valid_contract": False,
           "kinds": [], "extensions_present": False, "signers_present": False, "error": None}
    if status != 200:
        out["error"] = f"HTTP {status}"
        return out
    try:
        doc = json.loads(body)
    except Exception as e:  # noqa: BLE001
        out["error"] = f"invalid JSON: {e}"
        return out
    kinds = doc.get("kinds")
    if not isinstance(kinds, list) or not kinds:
        out["error"] = "missing/empty kinds[]"
        return out
    valid = True
    parsed = []
    for k in kinds:
        if not isinstance(k, dict) or not all(x in k for x in ("x402Version", "scheme", "network")):
            valid = False
            continue
        parsed.append({"x402Version": k["x402Version"], "scheme": k["scheme"], "network": k["network"]})
    out["kinds"] = parsed
    out["valid_contract"] = valid and "extensions" in doc and "signers" in doc
    out["extensions_present"] = "extensions" in doc
    out["signers_present"] = "signers" in doc
    out["signers"] = doc.get("signers")
    if not valid:
        out["error"] = "kind entries missing required fields"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="nonzero exit on BLOCKED only")
    ap.add_argument("--json", action="store_true", help="emit JSON report")
    args = ap.parse_args()

    spec = supported(SPEC_PATH)
    alt = supported(RAEN_PATH)

    # meta: servedPayees + facilitatorAddress
    mstatus, _, mbody = http(FACILITATOR + META_PATH)
    meta = {}
    if mstatus == 200:
        try:
            meta = json.loads(mbody)
        except Exception:  # noqa: BLE001
            pass
    served = {str(a).lower() for a in (meta.get("servedPayees") or [])}

    wall_reports = []
    for name, url, body in WALLS:
        req, err = challenge(url, body)
        rep = {"name": name, "url": url, "requirement": req, "error": err}
        if req is None:
            rep["kind_parity"] = "UNKNOWN"
            rep["payee_parity"] = "UNKNOWN"
            wall_reports.append(rep)
            continue
        key = (req.get("x402Version"), req.get("scheme"), req.get("network"))
        active = alt if alt["valid_contract"] else spec
        kinds = {(k["x402Version"], k["scheme"], k["network"]) for k in active["kinds"]}
        rep["kind_parity"] = "COVERED" if key in kinds else "GAP"
        rep["payee_parity"] = ("COVERED" if str(req.get("payTo", "")).lower() in served
                               else "NOT_COVERED")
        wall_reports.append(rep)

    any_gap = any(r["kind_parity"] == "GAP" for r in wall_reports)
    no_discovery = not (spec["valid_contract"] or alt["valid_contract"])
    spec_gap = not spec["valid_contract"] and alt["valid_contract"]
    if no_discovery or any_gap:
        verdict = "BLOCKED"
    elif spec_gap:
        verdict = "COMPAT_GAP"  # capability is discoverable, but not at the spec path
    else:
        verdict = "READY"

    report = {
        "tool": "Innovation 66 - facilitator capability-discovery auditor",
        "facilitator": FACILITATOR,
        "spec_path": spec,
        "raen_path": alt,
        "meta": {"facilitatorAddress": meta.get("facilitatorAddress"),
                 "servedPayees": meta.get("servedPayees"),
                 "networks": meta.get("networks")},
        "walls": wall_reports,
        "verdict": verdict,
        "notes": [
            "x402 spec v1+v2 section 7.3 mandates GET /supported at the facilitator root.",
            "RAEN publishes the same kinds contract at /facilitator/supported (FastAPI prefix).",
            "COMPAT_GAP is report-only: payment path works, spec-path discovery does not.",
            "Pricing is owner-gated; this tool never reads a price as a defect.",
        ],
    }
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"FACILITATOR CAPABILITY-DISCOVERY AUDIT  verdict={verdict}")
        for label, s in (("spec /supported", spec), ("raen /facilitator/supported", alt)):
            print(f"  {label:30s} HTTP {s['http_status']} valid={s['valid_contract']} "
                  f"kinds={len(s['kinds'])} {s.get('error') or ''}")
        for r in wall_reports:
            q = r.get("requirement") or {}
            print(f"  {r['name']:14s} kind={r['kind_parity']:11s} payee={r['payee_parity']:12s} "
                  f"v{q.get('x402Version')}/{q.get('scheme')}/{q.get('network')} {r.get('error') or ''}")
        print("  kinds:", sorted({(k['x402Version'], k['scheme'], k['network'])
                                  for k in (alt if alt['valid_contract'] else spec)['kinds']}))
        print("  servedPayees:", served)
    if args.check and verdict == "BLOCKED":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
