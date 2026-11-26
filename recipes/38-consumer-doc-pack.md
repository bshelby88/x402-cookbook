---
permalink: /recipes/38-consumer-doc-pack.md
---

# Recipe 38 — Consumer documentation copy pack: every claim read from a live surface

**Status:** shipped 2026-11-26 (Tiffany, machine-buyer acquisition, TIFF-PLAN-17). Free, read-only, unpaid-HTTP-only, stdlib-only. No signing, no `X-PAYMENT`, no RPC money calls, no funds movement, no POST to any directory, no external sends. BURN FREEZE: only kept-live walls are probed.

A machine buyer's first question is not "how do I pay" — it is "what do I send, what does it cost, and who do I pay?" The answer lives in three places that can disagree: the **manifest**, the **OpenAPI spec**, and the **live 402 challenge**. When they disagree, the buyer is killed before they ever see a price (the schema-drift failure mode), or follows a stale price and misroutes funds.

Recipe 38 turns that three-way truth problem into a **consumer documentation copy pack**: a buyer-facing Markdown doc whose request shapes come from the seller's own published manifest, and whose price / payTo / network / scheme come only from a fresh live 402. Nothing is hand-typed.

The script: [`scripts/consumer-doc-pack.py`](../scripts/consumer-doc-pack.py).

## What it does

For each kept-live wall (royal-ruby `/api/law-lookup`, contract-eye `/api/analyze-contract`, gateway `/mcp`):

1. **Manifest** (`/.well-known/x402.json`): reads the advertised request body from `extensions.bazaar` (`info.input.body`), the advertised price from `accepts.price` or `accepts.amount`, and the declared payTo / network / scheme.
2. **Live 402**: sends one **unpaid** POST with that advertised body and decodes `accepts[0]` (`amount` / `payTo` / `network` / `scheme`). This is the only price truth.
3. **OpenAPI** (`/openapi.json`): records whether the route is documented.
4. **Wrong-body probe**: attempted, but on x402 paid walls the 402 precedes body validation, so the route's 400 message is normally **not observable unpaid**. The tool reports `VALIDATION_GATED_402_PRECEDES_BODY` instead of inventing a schema verdict — TRUTH law.
5. Cross-checks price / payTo / network / scheme; verifies payTo against the full 42-character canonical address (case-insensitive, homoglyph-safe).
6. Emits `registry/consumer-doc-pack.json` and a buyer-facing `registry/consumer-doc-pack.md` with copy-paste first-call curls.

Exit codes: `0` CLEAN, `1` DRIFT (price/payTo/network/scheme mismatch or noncanonical), `2` UNREACHABLE.

## Run it

```bash
python3 scripts/consumer-doc-pack.py \
  --json registry/consumer-doc-pack.json \
  --md registry/consumer-doc-pack.md
```

No dependencies. Python 3 stdlib only. Other walls can be added to the `WALLS` list.

## Live result (2026-11-26 01:3x CT) — verdict CLEAN

- **3 kept-live walls probed, all HTTP 402, all `payTo` CANONICAL**, `eip155:8453`, `exact`:
  - royal-ruby `/api/law-lookup` — **$0.05** (`amount = 50000`)
  - contract-eye `/api/analyze-contract` — **$0.005** (`amount = 5000`)
  - gateway `/mcp` (`tools/call`) — **$0.05** (`amount = 50000`)
- **0 price drift**: contract-eye's manifest `$0.005` matches its live 402; royal-ruby's manifest does not publish a price (live 402 authoritative); gateway's manifest `amount = 50000` matches.
- Request bodies sourced from each seller's own `extensions.bazaar` example; gateway used the documented known-good `tools/call` body.
- **Free-discovery distinction recorded**: gateway `tools/list` returns HTTP 200 with no challenge — it is a free discovery call, not a paid wall. The paid wall is `tools/call`.

## Why this is acquisition, not cosmetics

The buyer journey is: discover → decide what to send → check the price → pay → verify. Recipe 38 covers the two highest-friction steps a machine buyer cannot skip by guessing: **exact request shape** and **who/what to pay**. It complements recipe 23 (preflight), 24 (price oracle), 26 (paywall picker), 30 (intent matcher), 35 (llms.txt lint) and 37 (playground walkthrough) without repeating them: none of those assemble a publishable consumer doc pack grounded in all three surfaces at once.

## Truth boundaries

- Price truth = a fresh live 402 (`accepts[0].amount`), never a manifest, cached, or hand-typed price.
- Request shapes are the **seller's published manifest examples**, not a claim about server-side validation (the 402 gate makes that unobservable unpaid).
- Challenges are scanners/bots-heavy — a demand signal, not sales (recipe 36). Internal self-pays are not external revenue; external revenue is $0.00 unless the chain says otherwise.
- Chain-coverage: verifies Base (`eip155:8453`) only — the chain RAEN walls settle on.

## Handoff

- **[owner][kip]:** this pack is a ready-to-publish consumer doc baseline; the seller-side schema/price corrections from recipes 35/37 remain in the single owner-approved source window (BURN FREEZE blocks agent-side edits this run).
- **[crown][franklin][erica]:** use `registry/consumer-doc-pack.md` as the quotable first-call source; quote live prices $0.05 / $0.005 / $0.05 and the full canonical payTo, never a cached figure.

MIT licensed. Not legal or financial advice.
