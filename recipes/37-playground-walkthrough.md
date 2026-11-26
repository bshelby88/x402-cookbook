---
permalink: /recipes/37-playground-walkthrough.md
---

# Recipe 37 — Playground walkthrough: make the buyer's first 402 trustworthy

**Status:** shipped 2026-11-26 (Tiffany, machine-buyer acquisition, TIFF-PLAN-18). Free, read-only, unpaid-HTTP-only, stdlib-only. No signing, no `X-PAYMENT`, no RPC money calls, no funds movement, no POST to any directory, no external sends.

The `/playground` at `rae-fleet-router.fly.dev/playground` is RAEN's most buyer-facing surface: it walks an agent through a real 402 handshake in the browser and hands it a curl recipe. But its wall list and prices are **hardcoded HTML**. A hardcoded buyer price is a doc claim, and like any doc claim it drifts from the live 402 — the only price truth. A machine buyer who follows a stale price either misroutes funds or abandons the first paid call. This tool makes the playground honest.

The script: [`scripts/playground-walkthrough.py`](../scripts/playground-walkthrough.py).

## What it does

1. GETs the live `/playground` HTML (free) and parses every advertised `service — METHOD /path ($price)` option.
2. Re-probes **only kept-live walls** with an unpaid POST and decodes the x402 v2 challenge (`accepts[0].amount` / `payTo` / `network` / `scheme`). Frozen walls are never probed (BURN FREEZE) — they are labelled `NOT VERIFIED`.
3. Compares each advertised price to the live price and flags drift; verifies `payTo` against the full 42-character canonical address (case-insensitive, homoglyph-safe), `network == eip155:8453`, `scheme == exact`.
4. Emits a machine-readable registry (`registry/playground-walkthrough.json`) and a buyer-facing Markdown content pack (`registry/playground-walkthrough.md`) whose prices come **only** from live 402s.

Exit codes: `0` CLEAN (all probed walls canonical, no price drift), `1` DRIFT, `2` UNREACHABLE.

## Run it

```bash
python3 scripts/playground-walkthrough.py \
  --json registry/playground-walkthrough.json \
  --md registry/playground-walkthrough.md
```

No dependencies. Python 3 stdlib only. Works against any URL with `--url`.

## Live result (2026-11-26 00:2x CT) — verdict DRIFT

- Playground HTTP 200; **21** advertised walls parsed.
- **3** kept-live walls probed, all HTTP 402, all `payTo` CANONICAL, `eip155:8453`, `exact`:
  - royal-ruby `/api/law-lookup` — live **$0.05** (`amount = 50000`)
  - contract-eye `/api/analyze-contract` — live **$0.005** (`amount = 5000`)
  - gateway `/mcp` — live **$0.05** (`amount = 50000`)
- **1 real price drift:** the playground page advertises royal-ruby `/api/law-lookup` at **$0.25**, but the live 402 charges **$0.05** — a **5× overstatement** in a buyer-facing surface. The other 20 walls are frozen/kept-live-without-recipe and are labelled `NOT VERIFIED`, not recommended for a first paid call.

This is the same doc-drift family recipe 35 found in `llms.txt` and the shared directory (royal-ruby $0.25 vs live $0.05). It is a **finding, not a fix this run**: `rae-fleet-router` is BURN-FROZEN and the correction needs the owner-approved source window (handoff below). No live page was edited, no service redeployed.

## Why this is acquisition, not cosmetics

A machine buyer's first paid call is the highest-friction moment in the funnel. A wrong price at that moment is a lost buyer and a TRUTH-law violation. This tool turns the playground from an unverified price list into a **proof surface**: it tells the buyer which walls are currently canonical, what they actually cost, and which walls to avoid — before any funds move. It complements recipe 23 (preflight), 27 (receipt proof) and 36 (challenge leaderboard).

## Truth boundaries

- Price truth = a fresh live 402 (`accepts[0].amount`), never the hardcoded playground price.
- Many 402 challenges are scanners/bots — challenges are a demand signal, not sales (recipe 36).
- Internal self-pays from AgentCash are not external revenue.
- Chain-coverage: this verifies Base (`eip155:8453`) only — the chain RAEN walls settle on.

## Handoff

- **[owner][kip]:** apply the royal-ruby `$0.25 → $0.05` correction on the `/playground` wall list and the recipe-35/32 doc packs in one owner-approved source window. BURN FREEZE blocks agent-side edits this run.

MIT licensed. Not legal or financial advice.
