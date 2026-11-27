#!/usr/bin/env python3
"""RAEN Innovation 48 - x402 Buyer Schema Parity Auditor.

A machine buyer that generates its client from published docs must find the SAME
request fields in the manifest (.well-known/x402.json) and the OpenAPI spec.
When the manifest advertises {text, focus?} but OpenAPI declares no requestBody
schema, the buyer builds a wrong request and never reaches the price.

This tool is READ-ONLY and stdlib-only. It fetches only the two free surfaces
(x402.json + openapi.json), compares advertised request fields, and emits a
machine-readable parity report. It never signs, never attaches a payment
header, never pays, and never moves money.

Usage:
  python3 scripts/schema-parity.py
  python3 scripts/schema-parity.py --out registry/schema-parity.json
  python3 scripts/schema-parity.py --check    # exit 1 on drift (CI gate)

Exit: 0 = clean, 1 = drift/missing schema on a kept-live paid wall, 2 = fetch error.
"""
import argparse, json, re, sys, urllib.error, urllib.request

CANON = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f"
RETIRED = "0x7861db4efc14a1ed5dd8c96c528a3796560f1393"

TARGETS = [
    ("royal-ruby", "https://royal-ruby-x402.fly.dev"),
    ("contract-eye", "https://contract-eye-x402.fly.dev"),
    ("nanobanana", "https://nanobanana-x402.fly.dev"),
    ("raen-mcp-gateway", "https://raen-mcp-gateway.fly.dev"),
    ("shipgate402", "https://shipgate402.fly.dev"),
]

# A field advertised as {text, focus?}, { url, expect?: {...}, probe? }, etc.
BRACE = re.compile(r"\{([^{}]+)\}")
IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*")
PAID_METHODS = ("POST", "PUT", "PATCH")
# Brace lists in a "returns {...}" / "-> {...}" clause are RESPONSE shapes,
# not request fields. Exclude those tokens so ping/preview routes never drift.
RESPONSE_TOKENS = {"status", "latency_ms", "catalog_url", "price_usdc", "service",
                   "block", "version", "uptime", "ok", "data", "result", "error",
                   "price", "amount", "currency", "timestamp", "payto", "network"}
REQUEST_CONTEXT = ("post", "send", "body", "request", "input")


def get_json(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "raen-schema-parity/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _balanced_braces(text):
    """Yield (start, end, inner) for each OUTER balanced {...} group."""
    i = 0
    n = len(text)
    while i < n:
        if text[i] != "{":
            i += 1
            continue
        depth, j = 1, i + 1
        while j < n and depth:
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
            j += 1
        if depth == 0:
            yield (i, j, text[i + 1:j - 1])
            i = j
        else:
            i += 1


def fields_from_braces(text):
    """Top-level fields the buyer is told to SEND, parsed from descriptions.

    Only brace lists introduced by a POST/send/body/request clause count as
    request fields; "returns {...}" response shapes are ignored. Nested
    objects (e.g. expect?: {amountAtoms,...}) collapse to their outer key.
    """
    out = set()
    text = text or ""
    for start, end, inner in _balanced_braces(text):
        context = text[max(0, start - 45):start].lower()
        if not any(k in context for k in REQUEST_CONTEXT):
            continue
        depth = 0
        parts, cur = [], []
        for ch in inner:
            if ch in "{[(":
                depth += 1
            elif ch in "}])":
                depth -= 1
            if ch == "," and depth == 0:
                parts.append("".join(cur)); cur = []
            else:
                cur.append(ch)
        parts.append("".join(cur))
        for part in parts:
            tok = part.strip()
            tok = tok.split(":")[0].strip().rstrip("?").strip()
            if IDENT.match(tok) and tok.lower() not in RESPONSE_TOKENS:
                out.add(tok)
    return out


def advertised_fields(resource):
    """Fields a buyer is told to send, parsed from resource description."""
    return fields_from_braces(resource.get("description", ""))


def spec_fields_for_path(openapi, path):
    item = (openapi.get("paths") or {}).get(path) or {}
    fields, required = set(), []
    for method in ("post", "put", "patch"):
        op = item.get(method) or {}
        rb = op.get("requestBody") or {}
        schema = ((rb.get("content") or {}).get("application/json") or {}).get("schema") or {}
        props = schema.get("properties") or {}
        fields.update(props.keys())
        if schema.get("required"):
            required = sorted(set(required) | set(schema["required"]))
    return fields, required


def canonical_ok(resource):
    a = resource.get("accepts") or {}
    payto = a.get("payTo") or (resource.get("accepts") or {}).get("payTo")
    return (payto or "").lower() == CANON


def is_paid(resource):
    """True only for a billable POST/PUT/PATCH route carrying a price/amount."""
    method = str(resource.get("method") or "").upper()
    if method not in PAID_METHODS:
        return False
    a = resource.get("accepts") or {}
    return bool(a.get("price") or a.get("amount") or a.get("maxAmountRequired"))


def audit():
    report = {"tool": "schema-parity", "version": 1, "walls": [], "findings": []}
    for name, base in TARGETS:
        wall = {"name": name, "base": base, "routes": [], "fetch_error": None}
        try:
            manifest = get_json(base + "/.well-known/x402.json")
            openapi = get_json(base + "/openapi.json")
        except Exception as e:
            wall["fetch_error"] = repr(e)
            report["walls"].append(wall)
            report["findings"].append({"wall": name, "severity": "FETCH_ERROR", "detail": repr(e)})
            continue

        resources = manifest.get("resources") or []
        skipped_free = 0
        for res in resources:
            if not is_paid(res):
                skipped_free += 1
                continue  # free/preview/discovery routes are not paid walls
            path = res.get("path") or ""
            method = str(res.get("method") or "POST").upper()
            doc_fields = sorted(advertised_fields(res))
            spec_fields, required = spec_fields_for_path(openapi, path)
            spec_list = sorted(spec_fields)
            doc_only = sorted(set(doc_fields) - spec_fields)
            spec_only = sorted(spec_fields - set(doc_fields))
            no_spec = bool(doc_fields) and not spec_list
            canon = canonical_ok(res)
            verdict = "PASS"
            if doc_only or no_spec:
                verdict = "DRIFT"
            elif not canon:
                verdict = "PAYTO_DRIFT"
            route = {
                "path": path, "method": method,
                "advertised_in_manifest": doc_fields,
                "declared_in_openapi": spec_list,
                "openapi_required": required,
                "doc_only_fields": doc_only,
                "spec_only_fields": spec_only,
                "openapi_schema_missing_for_advertised_fields": no_spec,
                "payto_canonical": canon,
                "verdict": verdict,
            }
            wall["routes"].append(route)
            if verdict != "PASS":
                report["findings"].append({
                    "wall": name, "path": path, "severity": verdict,
                    "doc_only_fields": doc_only,
                    "openapi_schema_missing": no_spec,
                    "detail": ("manifest advertises %s but OpenAPI declares %s"
                               % (doc_fields, spec_list)),
                })
        wall["free_routes_skipped"] = skipped_free
        report["walls"].append(wall)
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="write JSON report to this path")
    ap.add_argument("--check", action="store_true", help="exit 1 on any non-PASS finding")
    args = ap.parse_args()
    report = audit()
    text = json.dumps(report, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    for f in report["findings"]:
        print("[%s] %s %s :: %s" % (f["severity"], f["wall"], f.get("path", ""), f.get("detail", "")))
    if not report["findings"]:
        print("ALL PASS: manifest/OpenAPI request-field parity clean on all walls")
    if args.check and any(f["severity"] != "FETCH_ERROR" for f in report["findings"]):
        return 1
    if any(f["severity"] == "FETCH_ERROR" for f in report["findings"]) and not report["walls"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
