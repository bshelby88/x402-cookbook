#!/usr/bin/env python3
"""RAEN Innovation 23 - buyer intent matcher (stdlib only, read-only).

An autonomous agent has an INTENT ("check a contract for risky clauses") but the
fleet catalog is 44 endpoints across 13 walls. This tool turns an intent into a
ranked list of actually-buyable endpoints, with an exact unpaid curl stub for
each. It is the discovery layer BETWEEN the catalog and buyer-preflight.py.

Read-only: fetches the public catalog (or a local snapshot), never signs,
never pays, never sends an X-PAYMENT header, never moves money.

Usage:
  python3 scripts/intent-match.py "summarize a document into bullets"
  python3 scripts/intent-match.py "NFT floor price signal" --json
  python3 scripts/intent-match.py "check contract clauses" --catalog registry/catalog-snapshot.json
  python3 scripts/intent-match.py --build-index registry/intent-index-20261125.json

Exit 0 = at least one match; 1 = no match; 2 = catalog unavailable.
"""
import argparse, json, re, sys, urllib.request

DEFAULT_CATALOG = "https://rae-fleet-router.fly.dev/catalog.json"
CANONICAL_PAYTO = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f"
STOP = set("a an the and or of to for in on with by from is are be as at it this that "
           "into via using use get find check do does can i my your we our".split())


def load_catalog(src):
    if src.startswith("http://") or src.startswith("https://"):
        req = urllib.request.Request(src, headers={"User-Agent": "raen-intent-match/1.0",
                                                   "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))
    with open(src, encoding="utf-8") as f:
        return json.load(f)


def doc_of(item):
    return " ".join(str(item.get(k) or "") for k in ("slug", "description", "endpoint", "tier"))


def stem(w):
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def tokens(text):
    return [stem(w) for w in re.findall(r"[a-z0-9]+", str(text).lower())
            if w not in STOP and len(w) > 1]


def build_index(cat):
    """Only canonical-payTo, live-status, priced endpoints enter the buyer index."""
    entries = []
    for wall in cat.get("walls", []):
        for it in wall.get("items", []):
            payto = str(it.get("payTo") or "").lower()
            price = it.get("price_usdc")
            if payto != CANONICAL_PAYTO or it.get("status") != "ok":
                continue
            if not isinstance(price, (int, float)) or price <= 0:
                continue
            entries.append({
                "slug": it.get("slug"), "endpoint_url": it.get("endpoint_url"),
                "method": it.get("method"), "price_usdc": price,
                "amount_micro": it.get("amount_micro"), "payTo": it.get("payTo"),
                "network": it.get("network"), "asset": it.get("asset"),
                "facilitator": it.get("facilitator"), "tags": it.get("tags") or [],
                "tier": it.get("tier"), "description": it.get("description") or "",
                "doc_tokens": sorted(set(tokens(doc_of(it)))),
            })
    # dedupe by endpoint_url (catalog carries api/* and bare duplicates)
    seen, out = set(), []
    for e in sorted(entries, key=lambda x: (x["price_usdc"], x["slug"] or "")):
        key = (e["endpoint_url"], e["method"])
        if key in seen:
            continue
        seen.add(key); out.append(e)
    return out


def df_map(index):
    df = {}
    for e in index:
        for t in e["doc_tokens"]:
            df[t] = df.get(t, 0) + 1
    return df


def rank(query, index, topn):
    q = set(tokens(query))
    if not q:
        return []
    df = df_map(index)
    n = len(index)
    scored = []
    for e in index:
        toks = set(e["doc_tokens"])
        hit = q & toks
        if not hit:
            continue
        score = 0.0
        for t in hit:
            idf = 1.0 / (1.0 + df.get(t, 0))
            if t in (e["slug"] or "").lower().split("__")[-1] or t in (e["slug"] or "").lower().split("_"):
                score += 3.0 * idf
            if any(t in str(tag).lower() for tag in e["tags"]):
                score += 2.0 * idf
            score += 1.0 * idf
        score += 0.05 * (1.0 - min(e["price_usdc"], 1.0))  # cheaper wins ties
        scored.append((score, sorted(hit), e))
    scored.sort(key=lambda x: (-x[0], x[2]["price_usdc"]))
    return scored[:topn]


def curl_stub(e):
    body = "'{}'"
    if e["method"] == "POST":
        hint = e.get("hint_body") or "{}"
        body = "'%s'" % hint
    if e["method"] == "POST":
        return "curl -s -D h.txt -o b.txt -X POST %s -H 'Content-Type: application/json' --data-binary %s" % (
            e["endpoint_url"], body)
    return "curl -s -D h.txt -o b.txt %s" % e["endpoint_url"]


def main():
    ap = argparse.ArgumentParser(description="Match a buyer intent to RAEN's buyable endpoints.")
    ap.add_argument("intent", nargs="*", help="natural-language intent")
    ap.add_argument("--catalog", default=DEFAULT_CATALOG)
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--build-index", metavar="PATH", help="write the filtered index snapshot")
    a = ap.parse_args()
    try:
        cat = load_catalog(a.catalog)
    except Exception as exc:
        print("ERROR: catalog unavailable: %s" % exc, file=sys.stderr)
        return 2
    index = build_index(cat)
    if a.build_index:
        snap = {k: v for k, v in cat.items() if k != "walls"}
        snap["generated_utc"] = cat.get("generated_utc")
        snap["buyer_index"] = index
        with open(a.build_index, "w", encoding="utf-8") as f:
            json.dump(snap, f, indent=2)
        print("wrote %d canonical-priced endpoints -> %s" % (len(index), a.build_index))
        if not a.intent:
            return 0
    query = " ".join(a.intent).strip()
    if not query:
        print("usage: intent-match.py <intent> [--json] [--top N] [--build-index PATH]", file=sys.stderr)
        return 1
    hits = rank(query, index, a.top)
    if a.json:
        print(json.dumps({"query": query, "indexed_endpoints": len(index),
                          "matches": [{"score": round(s, 4), "matched_terms": m,
                                       **{k: e[k] for k in ("slug", "endpoint_url", "method",
                                                            "price_usdc", "amount_micro", "payTo",
                                                            "network", "description", "tags")},
                                       "unpaid_probe": curl_stub(e)}
                                      for s, m, e in hits]}, indent=2))
    else:
        print('INTENT: "%s" | indexed: %d canonical-priced endpoints\n' % (query, len(index)))
        for i, (s, m, e) in enumerate(hits, 1):
            print("%d. %-30s $%-7s %s %s" % (i, e["slug"], e["price_usdc"], e["method"], e["endpoint_url"]))
            print("   score %.3f  terms=%s" % (s, ",".join(m)))
            print("   probe: %s\n" % curl_stub(e))
    return 0 if hits else 1


if __name__ == "__main__":
    sys.exit(main())
