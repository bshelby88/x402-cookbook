# Recipe 59 — Discovery Brochure Auditor

**What:** Read-only, stdlib-only grade of the eight public buyer-facing "brochure"
surfaces a machine buyer or its code generator reads before it ever reaches a
paid wall.

**Why:** Tools 1-58 grade the wall, the wall-adjacent docs, the payer, the ledger
and the chain. None grades the storefront window — the GitHub Pages buyer tools,
the cookbook itself, the law pages, `llms.txt`, the router catalog and the MCP
Registry. A Vercel "Ready but 404 on every path" deployment or a stale retired
payTo in published buyer copy silently kills acquisition before the buyer sees a
price. This closes that gap.

**Run:**
```
python3 scripts/discovery-brochure.py            # human-readable grade
python3 scripts/discovery-brochure.py --write    # + registry/discovery-brochure.json
python3 scripts/discovery-brochure.py --check    # exit 1 only on retired-payTo leak
```

**Verdicts:** `LIVE_CANONICAL` (200 + canonical payTo), `LIVE_INFO` (200, payTo
not expected), `PAYTO_MISSING` (payTo expected but absent), `POISON_SUSPECT`
(homoglyph near-match), `DOWN` (GAP, handed off), `HARD_DRIFT` (un-warned retired
payTo — a money-misroute risk).

**Truth discipline:** Context-aware retired-address grading — a retired payTo
wrapped in a rejection warning ("Reject the retired wallet 0x7861...") is correct
buyer guidance and does NOT drift; only an un-warned occurrence fails. Self-tested
for both cases. Full 42-char canonical compare, case-insensitive. Price/doc drift
is owner-gated and never changed here. No signing, no X-PAYMENT, no funds.

**Live 2026-11-27 18:32Z:** 8/8 surfaces 200 + non-empty, 0 hard drift, 0 warns,
`--check` exit 0, verdict CANONICAL. Snapshot `registry/discovery-brochure.json`
+ buyer card `registry/discovery-brochure.md`.
