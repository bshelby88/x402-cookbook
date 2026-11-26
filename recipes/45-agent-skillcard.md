# Innovation 45 — Installable Agent Buyer Skill Card

**Date:** 2026-11-26 09:4x CT / 15:5xZ · **Author:** Tiffany (revenue-director) · **Status:** shipped, read-only

## The gap

The cookbook's 44 tools are *reference material*: an autonomous agent has to read, interpret and recombine them before it can make a first purchase. Discovery feeds, readiness scorecards and client skeletons help, but none of them is a **single file an agent framework can install** and then follow.

Innovation 45 emits that file. `registry/agent-skillcard.md` is a portable SKILL.md-style card (frontmatter + instructions) that an agent can copy into its `skills/` directory or paste into its system instructions. It carries the checkout order, the canonical-payTo guard, the EIP-3009 signing boundary and the claims-desk fallback — plus a price table generated from live unpaid 402 challenges at a stated UTC timestamp.

## What the generator does

`python3 scripts/agent-skillcard.py` (stdlib only, read-only):

1. Sends one **unpaid** POST per kept-live wall (royal-ruby, contract-eye, nanobanana, raen-mcp-gateway).
2. Base64-decodes each `payment-required` header and reads `accepts[0]`.
3. Asserts `x402Version==2`, `scheme=='exact'`, `network=='eip155:8453'`, integer `amount > 0`, and a **FULL 42-character** case-insensitive canonical payTo (poison-address safe).
4. Writes `registry/agent-skillcard.json` (live snapshot) and `registry/agent-skillcard.md` (installable card).

Exit 0 = all walls canonical; 1 = a canonical break; 2 = none reachable. CI fails only on a canonical break; WARNs are published, not hidden. The card declares that the **live 402 is authoritative** over its own snapshot.

## Verified result — 2026-11-26T15:50:04Z

| Wall | Live price | Verdict |
| --- | --- | --- |
| royal-ruby `/api/law-lookup` | $0.005 | canonical |
| contract-eye `/api/analyze-contract` | $0.005 | canonical |
| nanobanana `/api/generate-image` | $0.01 | canonical |
| raen-mcp-gateway `/mcp` `tools/call` | $0.05 | canonical |

`verdict=OK`, 4/4 reachable, 0 breaks. `py_compile` OK, script exit 0, generated card 0 placeholder/TODO leaks, registry JSON re-parsed. All four challenges x402 v2 `exact` `eip155:8453` with the full canonical payTo.

## Boundaries

No signing, no `X-PAYMENT`, no RPC money call, no funds movement, no keys, no external sends, no directory POSTs, no deploy (BURN FREEZE honored). Only kept-live walls are probed, and only unpaid.

Chain check this cycle: Base (3/3 RPC consensus) canonical 18.177651 / retired 16.628295 / AgentCash 2.628259 USDC; ETH mainnet (2/2 publicnode) canonical 0.000007 / retired 0 / AgentCash 15.0 USDC — FLAT vs prior cycle, external earned revenue **$0.00** (honest).
