#!/usr/bin/env python3
"""RAEN 'Pick My Paywall' recommender — stdlib only, read-only.

Turns a machine buyer's need/budget/urgency into a primary + up to two
alternate pay links, grounded ONLY in a fresh GET of the router's
/buy?format=json snapshot. It never signs, never sends payment, never moves
funds, and never invents a slug or a price.

Modes:
  --recommend            emit one recommendation (default)
  --generate-pack PATH   regenerate all decision-tree leaves from the snapshot
  --verify-pack PATH     fail if a pack's leaves drift from the live snapshot

Exit 0 = OK / PASS, 1 = drift or bad contract, 2 = transport failure.
"""
import argparse, datetime, json, os, sys, urllib.request

BUY_URL = "https://rae-fleet-router.fly.dev/buy?format=json"
CANONICAL_PAYTO = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f"
BASE_LINK = "https://rae-fleet-router.fly.dev/buy/"

NEEDS = ["data", "code", "content", "image", "legal", "security"]
BUDGETS = ["penny", "value", "pro"]
URGENCIES = ["quick", "thorough"]

QUESTION_COPY = [
    {"id": "need", "prompt": "What do you need from the fleet?",
     "options": [
         {"value": "data", "label": "Data / signals", "copy": "Market, NFT, skill or bundle data you can act on."},
         {"value": "code", "label": "Code / tooling", "copy": "Scaffolds, validators and audit helpers for agents."},
         {"value": "content", "label": "Text / summaries", "copy": "Summarize, simplify, extract or compare documents."},
         {"value": "image", "label": "Images", "copy": "Generate or edit an image from a prompt."},
         {"value": "legal", "label": "Compliance / disputes", "copy": "Compliance bundles and dispute packs."},
         {"value": "security", "label": "Security / audit", "copy": "Site and x402 configuration audits."}]},
    {"id": "budget", "prompt": "What is your per-call budget?",
     "options": [
         {"value": "penny", "label": "Penny tier (<= $0.01)", "copy": "Cheapest possible first call."},
         {"value": "value", "label": "Value tier (<= $0.05)", "copy": "A little more depth for a few cents."},
         {"value": "pro", "label": "Pro tier (> $0.05)", "copy": "Higher-value, multi-step deliverables."}]},
    {"id": "urgency", "prompt": "How do you want to start?",
     "options": [
         {"value": "quick", "label": "Quickest / cheapest", "copy": "Lowest price in your tier, fastest first result."},
         {"value": "thorough", "label": "Most capable", "copy": "Richest deliverable available in your tier."}]},
]

OUTPUT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "RAEN paywall recommendation",
    "type": "object",
    "required": ["generated_utc", "snapshot_generated_utc", "need", "budget", "urgency", "primary", "alternates"],
    "properties": {
        "generated_utc": {"type": "string"},
        "snapshot_generated_utc": {"type": "string"},
        "need": {"enum": NEEDS}, "budget": {"enum": BUDGETS}, "urgency": {"enum": URGENCIES},
        "primary": {"$ref": "#/$defs/paylink"},
        "alternates": {"type": "array", "items": {"$ref": "#/$defs/paylink"}, "maxItems": 2}},
    "$defs": {"paylink": {"type": "object", "required": ["slug", "price_usdc", "buy_url", "method", "host", "endpoint"],
        "properties": {"slug": {"type": "string"}, "price_usdc": {"type": "number"},
                       "amount_micro": {"type": "string"}, "buy_url": {"type": "string"},
                       "method": {"type": "string"}, "host": {"type": "string"}, "endpoint": {"type": "string"}}}},
}

# Need tags: exact slug or slug prefix. A slug may serve more than one need.
NEED_TAGS = {
    "data": ("nft-alpha", "suprapack", "tradingagents", "rae-fleet-router__bundle_market",
             "rae-fleet-router__bundle_full-fleet-sampler", "rae-fleet-router__bundle_full-stack"),
    "code": ("vault-pro", "royal-ruby__cold-start-kit", "royal-ruby__validate-json",
             "royal-ruby__address-check", "royal-ruby__x402-audit", "rae-fleet-router__bundle"),
    "content": ("briefsnap", "nanobanana", "royal-ruby__udap-citations"),
    "image": ("nanobanana",),
    "legal": ("dispute-forge", "royal-ruby__buy-compliance", "rae-fleet-router__bundle_compliance-kit", "royal-ruby"),
    "security": ("dispute-forge", "royal-ruby__site-audit", "royal-ruby__x402-audit", "vault-pro"),
}


def load_snapshot(source, save_path=None):
    try:
        if source.startswith("http://") or source.startswith("https://"):
            req = urllib.request.Request(source, headers={"User-Agent": "RAEN-paywall-picker/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read()
        else:
            with open(source, "rb") as f:
                raw = f.read()
        if save_path:
            with open(save_path, "wb") as f:
                f.write(raw)
        return json.loads(raw.decode("utf-8"))
    except Exception as exc:
        print("TRANSPORT_FAILURE: " + str(exc), file=sys.stderr)
        sys.exit(2)


def healthy(snapshot):
    good, excluded = [], []
    for it in snapshot.get("items", []):
        slug = it.get("slug", "")
        p = it.get("price_usdc")
        payto = str(it.get("payTo", ""))
        reasons = []
        if str(it.get("status")) != "ok":
            reasons.append("status=" + str(it.get("status")))
        if not isinstance(p, (int, float)) or isinstance(p, bool) or p <= 0:
            reasons.append("no positive price")
        if payto.lower() != CANONICAL_PAYTO.lower():
            reasons.append("non-canonical payTo")
        if reasons:
            excluded.append({"slug": slug, "reason": "; ".join(reasons)})
        else:
            good.append(it)
    return good, excluded


def tier(price):
    if price <= 0.01:
        return "penny"
    if price <= 0.05:
        return "value"
    return "pro"


def paylink(it):
    return {"slug": it["slug"], "price_usdc": it["price_usdc"], "amount_micro": str(it.get("amount_micro", "")),
            "buy_url": BASE_LINK + it["slug"], "method": it.get("method", ""),
            "host": it.get("host", ""), "endpoint": it.get("endpoint", "")}


def pick(good, need, budget, urgency):
    pool = [it for it in good if tier(it["price_usdc"]) == budget]
    matched = [it for it in pool if it["slug"].startswith(NEED_TAGS[need])]
    cand = matched if matched else pool
    if urgency == "quick":
        cand = sorted(cand, key=lambda i: (i["price_usdc"], i.get("method") != "GET", i["slug"]))
    else:
        cand = sorted(cand, key=lambda i: (-i["price_usdc"], not i["slug"].startswith("rae-fleet-router__bundle"), i["slug"]))
    if not cand:
        return None
    return {"need": need, "budget": budget, "urgency": urgency,
            "primary": paylink(cand[0]), "alternates": [paylink(i) for i in cand[1:3]]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", default=BUY_URL)
    ap.add_argument("--need", choices=NEEDS, default="data")
    ap.add_argument("--budget", choices=BUDGETS, default="penny")
    ap.add_argument("--urgency", choices=URGENCIES, default="quick")
    ap.add_argument("--generate-pack")
    ap.add_argument("--verify-pack")
    ap.add_argument("--save-snapshot", help="write the exact snapshot bytes used to this path")
    a = ap.parse_args()

    snap = load_snapshot(a.snapshot, a.save_snapshot)
    good, excluded = healthy(snap)
    if not good:
        print("NO_HEALTHY_PRICED_WALLS", file=sys.stderr)
        sys.exit(1)

    all_leaves = [x for x in (pick(good, n, b, u) for n in NEEDS for b in BUDGETS for u in URGENCIES) if x is not None]
    if len(all_leaves) != len(NEEDS) * len(BUDGETS) * len(URGENCIES):
        print("UNRESOLVED_LEAF (a budget tier has no healthy priced wall)", file=sys.stderr)
        sys.exit(1)

    if a.generate_pack:
        pack = {"artifact": "PLAN-78 Pick My Paywall — guided recommender copy pack", "version": 1,
                "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "snapshot_url": a.snapshot if a.snapshot.startswith("http") else "local-file",
                "snapshot_generated_utc": snap.get("generated_utc"), "snapshot_count": snap.get("count"),
                "healthy_priced_count": len(good), "excluded_from_picker": excluded,
                "questions": QUESTION_COPY, "output_schema": OUTPUT_SCHEMA,
                "leaves": all_leaves, "leaf_count": len(all_leaves)}
        with open(a.generate_pack, "w", encoding="utf-8") as f:
            json.dump(pack, f, indent=2, ensure_ascii=False)
        print("WROTE", a.generate_pack, "leaves:", len(all_leaves), "healthy:", len(good))
        return

    if a.verify_pack:
        try:
            pack = json.load(open(a.verify_pack, encoding="utf-8"))
        except Exception as exc:
            print("PACK_UNREADABLE: " + str(exc), file=sys.stderr)
            sys.exit(1)
        live = {(x["need"], x["budget"], x["urgency"]): [x["primary"]["slug"]] + [z["slug"] for z in x["alternates"]]
                for x in all_leaves}
        bad = []
        for leaf in pack.get("leaves", []):
            k = (leaf["need"], leaf["budget"], leaf["urgency"])
            got = [leaf["primary"]["slug"]] + [z["slug"] for z in leaf.get("alternates", [])]
            if live.get(k) != got:
                bad.append({"leaf": k, "pack": got, "live": live.get(k)})
        verdict = {"generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   "snapshot_generated_utc": snap.get("generated_utc"), "leaves_checked": len(pack.get("leaves", [])),
                   "drift": bad, "verdict": "PASS" if not bad and len(pack.get("leaves", [])) == len(all_leaves) else "FAIL"}
        print(json.dumps(verdict, indent=2))
        sys.exit(0 if verdict["verdict"] == "PASS" else 1)

    rec = {"generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "snapshot_generated_utc": snap.get("generated_utc"),
           "healthy_priced_count": len(good),
           "recommendation": pick(good, a.need, a.budget, a.urgency)}
    print(json.dumps(rec, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
