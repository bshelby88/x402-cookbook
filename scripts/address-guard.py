#!/usr/bin/env python3
"""Recipe 33 - canonical address guard (Tiffany, machine-buyer acquisition).

Zero-cost, read-only, stdlib-only. Scans any text (files, URLs, stdin) for 42-character
hex addresses and classifies each against the known RAEN wallet roles. Catches the
single most expensive buyer mistake: paying a RETIRED address or a poison homoglyph
that differs from canonical by one or two characters.

NO signing, NO payment header, NO RPC money calls, NO funds movement, NO external sends.

Classifications:
  CANONICAL      0x9b8a27e03ceba490953cda8ab1291c0e13baf72f  (pay here)
  RETIRED        0x7861db4efc14a1ed5dd8c96c528a3796560f1393  (never pay)
  AGENTCASH      0xfbc0eb7811d477e55261d956df39f0046e192240  (internal funding wallet)
  POISON_SUSPECT hamming distance <=2 from a known role but not equal - DO NOT PAY
  UNKNOWN        not a known RAEN address - verify out of band

Usage:
  python3 scripts/address-guard.py <file|url|-> [<file|url|-> ...]
  python3 scripts/address-guard.py --url https://host/pricing.md
  echo "$TEXT" | python3 scripts/address-guard.py -
"""
import argparse
import json
import re
import sys
import urllib.request

CANONICAL = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f"
RETIRED   = "0x7861db4efc14a1ed5dd8c96c528a3796560f1393"
AGENTCASH = "0xfbc0eb7811d477e55261d956df39f0046e192240"
ROLES = {"CANONICAL": CANONICAL, "RETIRED": RETIRED, "AGENTCASH": AGENTCASH}

ADDR_RE = re.compile(r"0x[0-9a-fA-F]{40}")
UA = "Mozilla/5.0 (compatible; raen-address-guard/1.0)"


def hamming(a, b):
    """Number of differing hex characters (both are 0x + 40 hex)."""
    return sum(x.lower() != y.lower() for x, y in zip(a[2:], b[2:]))


def classify(addr):
    low = addr.lower()
    for role, known in ROLES.items():
        if low == known:
            return role, None
    # Poison homoglyph: within 2 chars of a role but not equal. Report nearest.
    best_role, best_d = None, 99
    for role, known in ROLES.items():
        d = hamming(low, known)
        if d < best_d:
            best_role, best_d = role, d
    if best_d <= 2:
        return "POISON_SUSPECT", {"nearest": best_role, "hamming_distance": best_d}
    return "UNKNOWN", {"nearest_hamming": best_d}


def read_source(src, timeout):
    if src == "-":
        return sys.stdin.read(), "stdin"
    if src.startswith("http://") or src.startswith("https://"):
        req = urllib.request.Request(src, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
        return raw, src
    with open(src, "r", encoding="utf-8", errors="replace") as f:
        return f.read(), src


def main():
    ap = argparse.ArgumentParser(description="Classify 0x addresses found in text against RAEN roles.")
    ap.add_argument("sources", nargs="*", help="file paths, URLs, or '-' for stdin")
    ap.add_argument("--url", action="append", default=[], help="URL to scan (repeatable)")
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--json", action="store_true", help="emit JSON only")
    ap.add_argument("--no-fail", action="store_true", help="exit 0 even when a bad address is found")
    args = ap.parse_args()

    sources = list(args.sources) + list(args.url)
    if not sources:
        sources = ["-"]

    findings = []
    errors = []
    for src in sources:
        try:
            text, label = read_source(src, args.timeout)
        except Exception as e:  # noqa: BLE001 - report, never crash the buyer
            errors.append({"source": src, "error": "%s: %s" % (type(e).__name__, e)})
            continue
        # de-dupe repeated addresses within one source, keep first position
        seen = set()
        for m in ADDR_RE.finditer(text):
            addr = m.group(0)
            if addr.lower() in seen:
                continue
            seen.add(addr.lower())
            role, detail = classify(addr)
            findings.append({
                "source": label,
                "offset": m.start(),
                "address": addr,
                "classification": role,
                "detail": detail,
            })

    bad = [f for f in findings if f["classification"] in ("RETIRED", "POISON_SUSPECT")]
    out = {
        "tool": "recipe-33-address-guard",
        "canonical": CANONICAL,
        "scanned_sources": len(sources),
        "addresses_found": len(findings),
        "counts": {
            "CANONICAL": sum(f["classification"] == "CANONICAL" for f in findings),
            "RETIRED": sum(f["classification"] == "RETIRED" for f in findings),
            "AGENTCASH": sum(f["classification"] == "AGENTCASH" for f in findings),
            "POISON_SUSPECT": sum(f["classification"] == "POISON_SUSPECT" for f in findings),
            "UNKNOWN": sum(f["classification"] == "UNKNOWN" for f in findings),
        },
        "verdict": "UNSAFE" if bad else ("CLEAN" if findings else "NO_ADDRESSES"),
        "findings": findings,
        "errors": errors,
    }
    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print("address-guard: %d address(es) across %d source(s)" % (len(findings), len(sources)))
        for f in findings:
            print("  %-14s %s  %s" % (f["classification"], f["address"], f["source"]))
            if f["detail"]:
                print("      -> %s" % json.dumps(f["detail"]))
        for e in errors:
            print("  ERROR %s" % json.dumps(e))
        print("VERDICT: %s" % out["verdict"])
    if bad and not args.no_fail:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
