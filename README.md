# x402 Integration Cookbook — RAEN Fleet

Copy-paste recipes for paying RAEN's 12 x402 services with USDC on Base mainnet from any agent (Python, Node, curl, MCP).

**Payee (all services):** `0x9b8a27e03ceba490953cda8ab1291c0e13baf72f`
**Network:** `eip155:8453` (Base) · **Scheme:** `exact` · **Asset:** USDC `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`

## The fleet

| Service | What it does | Price |
|---|---|---|
| [royal-ruby](https://royal-ruby-x402.fly.dev/.well-known/x402.json) | US consumer-rights law citation lookup (FCRA/FDCPA/TILA/UDAP). **Free first call** (charge-and-rebate — net $0) | **$0.005** rolling out (repriced per the owner-approved 2026-11-24 ladder; deploy rolling out — until it lands, your live 402 challenge shows the pre-ladder price and is authoritative) · bulk 10-99 @ $0.002, 100-500 @ $0.001 (floor 10) · $0.001 probe (`/api/ping`, live) |
| [contract-eye](https://contract-eye-x402.fly.dev/.well-known/x402.json) | Contract risk analysis, flags one-sided clauses | **$0.005** LIVE-VERIFIED 2026-11-25 (`accepts[0].amount` = `5000`, canonical payTo) · bulk 10-99 @ $0.002, 100+ @ $0.001 · $0.001 probe |
| [tradingagents](https://tradingagents-x402.fly.dev/.well-known/x402.json) | Synthetic degraded demo payload (currently in demo mode). **RETIRED 2026-11-24** — scale-to-zero (reversible); not purchase-eligible | ~~$0.05~~ RETIRED |
| [nanobanana](https://nanobanana-x402.fly.dev/.well-known/x402.json) | Gemini image generation/editing, base64 PNG out | **$0.01** (unchanged) · bulk 10+ @ $0.008 · $0.001 liveness ack |
| [briefsnap](https://briefsnap-x402.fly.dev/.well-known/x402.json) | Document summarization + action items. **RETIRED 2026-11-24** — scale-to-zero (reversible); not purchase-eligible | ~~$1.00-$3.00~~ RETIRED |
| [nft-alpha](https://nft-alpha-x402.fly.dev/.well-known/x402.json) | OpenSea market signals for Base collections | **$0.005** rolling out (repriced per the owner-approved 2026-11-24 ladder; deploy rolling out — until it lands, your live 402 challenge shows the pre-ladder price and is authoritative) · bulk 10+ @ $0.002 · $0.001 probe |
| [dispatch](https://dispatch-x402.fly.dev/.well-known/x402.json) | NL intent router → picks the right paid fleet service | **$0.01** rolling out (repriced per the owner-approved 2026-11-24 ladder; deploy rolling out — until it lands, your live 402 challenge shows the pre-ladder price and is authoritative) · bulk 10+ @ $0.005 · $0.001 probe |
| [escrow](https://escrow-x402.fly.dev/.well-known/x402.json) | Agent-to-agent USDC escrow on Base, 1% fee, timeout-refundable | **$0.005** create fee rolling out (repriced per the owner-approved 2026-11-24 ladder; deploy rolling out — until it lands, your live 402 challenge shows the pre-ladder price and is authoritative) · batch 10+ @ $0.003 · $0.001 probe |
| [dispute-forge](https://dispute-forge-x402.fly.dev/.well-known/x402.json) | FCRA-compliant dispute letter + on-chain certificate | **$0.01** LIVE-VERIFIED 2026-11-25 (`accepts[0].amount` = `10000`, canonical payTo) · bulk 10+ @ $0.005 · $0.001 probe |
| [vault-pro](https://vault-pro-x402.fly.dev/.well-known/x402.json) | Obsidian project/agent scaffolding markdown. **RETIRED 2026-11-24** — scale-to-zero (reversible); not purchase-eligible | ~~$0.05~~ RETIRED |
| [sentry-forge](https://sentry-forge-x402.fly.dev/.well-known/x402.json) | One collection notice → 8 review-ready dispute docs. **RETIRED 2026-11-24** — scale-to-zero (reversible); not purchase-eligible (human-billed $5.00 held) | ~~$5.00~~ RETIRED |
| [settlement-collector](https://settlement-collector.fly.dev/stats) | Fleet telemetry (free, public JSON) | free |

Prices marked "see manifest" come from the live manifest — always confirm against it; it is the source of truth.

## Paid but got nothing? The claims desk (read this before paying twice)

If you settled USDC and never received your payload, **do not pay again**. Look
up your payment by **tx hash or wallet address** — the lookup confirms your
claim code (`RAEN-<sha256(tx)[:10]>`, derivable from your own tx), its delivery
state, and the self-serve register-for-redelivery path:

```bash
curl -s "https://settlement-collector.fly.dev/storefront/claims?tx=<your-tx-hash>"
# or: ?payer=<your-address>   then register: POST /storefront/register {tx_or_intent, email | callback_url}
```

Full walkthrough: **[recipe 22 — the claims desk](recipes/22-claims-desk.md)**.
This includes payments to the retired payee `0x7861…1393`: that wallet is still
served AND watched (auto order + claim code per transfer — status at
`/storefront/legacy-watch`), so a legacy-named settle is never invisible.

## Machine-buyer trust: verify the payTo BEFORE you pay

**[registry/payto-registry.json](registry/payto-registry.json)** — machine-readable
trust registry. Every entry is confirmed by decoding a LIVE 402 challenge (not the
manifest). Fetch it, decode your challenge, compare `accepts[].payTo` to
`canonical_payto` **case-insensitively**. Reject the retired wallet
`0x7861db4efc14a1ed5dd8c96c528a3796560f1393` and homoglyph lookalikes —
malicious directories have carried them. Five-line verification recipe is inside the file.

## Claims desk for machine buyers — settled but got nothing? self-recover

**<https://settlement-collector.fly.dev/storefront/claims>** — the first claims desk we
know of for machine buyers. If you settle an x402 challenge and the payload never
arrives, don't write the money off and don't email a human:

- `GET /storefront/claims?tx=<your-tx-hash>` — lookup by settlement tx
- `GET /storefront/claims?address=<your-payer-address>` — lookup by payer wallet

Both return JSON: matched settlements, open claims, and the resolve URL. No login, no
email required. Machine registration: `POST /storefront/register {tx_or_intent, agent_id,
callback_url}` — receipt + claims delivered to your `callback_url` as an HTTP POST.

Verified live 2026-11-22 (tx-hash and address lookups both answer; register flow live).
The desk exists because of our own honest zero: the only external money the fleet ever
received ($0.05, 2026-11-11, settle-crawler) initially went unfulfilled — a buyer who
paid and got nothing. The desk now shows that claim (`RAEN-8922B9225B`) registered and
**delivered via webhook**: `GET /storefront/claims?tx=0xf61129a8…c77cf37e` returns the
full record. Every recipe below carries the same fallback link.

## Recipes

1. **[curl — decode your first 402 challenge](recipes/01-curl-402-decode.md)** — understand the protocol in 60 seconds.
2. **[Python — generic paid-call client](recipes/02-python-client.md)** — a ~40-line client that fetches the challenge, signs, retries, works for any fleet service. *(Bring your own EIP-3009 signer or use the [x402 SDK](https://github.com/coinbase/x402).)*
3. **[Free first call — charge-and-rebate](recipes/03-free-first-call.md)** — try royal-ruby for net $0 with one extra header. Step-by-step walkthrough with verify-everything links: **[raen-first-call-free](https://bshelby88.github.io/raen-first-call-free/)**.
4. **[MCP — use the fleet from any MCP client](recipes/04-mcp-gateway.md)** — Bearer-gated gateway at `raen-mcp-gateway.fly.dev/mcp`.
5. **[dispatch — route intents without a services map](recipes/05-dispatch-router.md)** — one endpoint that picks the right tool.

### Per-SKU buyer recipes — decode → settle → retry, verified against the live 402 challenge (Nov 15, 2026)

Each recipe is one SKU, copy-paste, 60-second testable: unpaid call → decode the
402 challenge (real captured values) → settle + retry → claim-code fallback if
you settled but got no payload.

6. **[royal-ruby — consumer-law citations](recipes/06-royal-ruby.md)** — **$0.005** (ladder, rolling out (repriced per the owner-approved 2026-11-24 ladder; deploy rolling out — until it lands, your live 402 challenge shows the pre-ladder price and is authoritative)) with bulk 10-99 @ $0.002 / 100-500 @ $0.001, first call free (charge-and-rebate), $0.001 probe.
7. **[dispatch — route any intent](recipes/07-dispatch.md)** — **$0.01** (ladder, rolling out (repriced per the owner-approved 2026-11-24 ladder; deploy rolling out — until it lands, your live 402 challenge shows the pre-ladder price and is authoritative)), returns a ready-to-use downstream request.
8. **[contract-eye — flag one-sided clauses](recipes/08-contract-eye.md)** — **$0.005** LIVE-VERIFIED 2026-11-25 (`accepts[0].amount` = `5000`), bulk 10-99 @ $0.002.
9. **[briefsnap — summarize any document](recipes/09-briefsnap.md)** — **RETIRED 2026-11-24** (scale-to-zero, reversible; was $1.00-$3.00).
10. **[nanobanana — image generation](recipes/10-nanobanana.md)** — $0.01 (kept — real per-call model cost), bulk 10+ @ $0.008, $0.001 liveness ack, base64 PNG out.
11. **[nft-alpha — OpenSea signals on Base](recipes/11-nft-alpha.md)** — **$0.005** (ladder, rolling out (repriced per the owner-approved 2026-11-24 ladder; deploy rolling out — until it lands, your live 402 challenge shows the pre-ladder price and is authoritative)), bulk 10+ @ $0.002.
12. **[vault-pro — Obsidian project scaffolding](recipes/12-vault-pro.md)** — **RETIRED 2026-11-24** (scale-to-zero, reversible; was $0.05).
13. **[escrow — agent-to-agent USDC escrow](recipes/13-escrow.md)** — **$0.005** create fee (ladder, rolling out (repriced per the owner-approved 2026-11-24 ladder; deploy rolling out — until it lands, your live 402 challenge shows the pre-ladder price and is authoritative)), batch 10+ @ $0.003, 1% release fee.
14. **[sentry-forge — 8 dispute docs from one notice](recipes/14-sentry-forge.md)** — **RETIRED 2026-11-24** (scale-to-zero, reversible; human-billed $5.00 held).
15. **[dispute-forge — dispute letter + on-chain certificate](recipes/15-dispute-forge.md)** — **$0.01** LIVE-VERIFIED 2026-11-25 (`accepts[0].amount` = `10000`), bulk 10+ @ $0.005, $0.001 probe.
16. **[tradingagents — ticker consensus (demo)](recipes/16-tradingagents.md)** — **RETIRED 2026-11-24** (scale-to-zero, reversible; ladder would have been $0.005).
17. **[x402-enterprise — dispute letter (enterprise variant, self-identifies as dispute-forge)](recipes/17-x402-enterprise.md)** — $0.75 **HOLD** (identity-drift decision precedes any repricing).
18. **[staci-tradingagents — full pipeline run](recipes/18-staci-tradingagents.md)** — **RETIRED 2026-11-24** (scale-to-zero, reversible; was $5.00 human-billed).
19. **[suprapack — search 531 curated agent skills](recipes/19-suprapack.md)** — **$0.005** (ladder, rolling out (repriced per the owner-approved 2026-11-24 ladder; deploy rolling out — until it lands, your live 402 challenge shows the pre-ladder price and is authoritative)), bulk 10+ @ $0.002, $0.001 probe.
20. **[royal-ruby ping — $0.001 alive-check](recipes/20-royal-ruby-ping.md)** — the cheapest settled liveness probe in the ecosystem: one GET, `{status:'alive', block, latency_ms, catalog_url}`. Machine registration by webhook: `POST /storefront/register {tx_or_intent, agent_id, callback_url}` — receipt + claims delivered as HTTP POST, no email.
21. **[Machine checkout without email](recipes/21-machine-checkout.md)** — the full prepaid-pack loop for machine buyers: pay → register with `callback_url` → delivery webhook with one-time `claim_code` → redeem at the live API via `X-RAEN-CREDIT`. No email ever.
22. **[The claims desk — paid but got nothing](recipes/22-claims-desk.md)** — look up your payment by tx hash or wallet address, recover your claim code (`RAEN-<sha256(tx)[:10]>`), register for re-delivery (email or webhook), verify/redeem prepaid credits. Includes the retired-payee stranding watch.
23. **[Buyer preflight — verify the wall before you sign](recipes/23-buyer-preflight.md)** — a free, read-only, stdlib-only script that decodes a live 402 and checks `accepts[0].amount`, the x402 v2 envelope, the verified `X-PAYMENT` retry header, and the canonical `payTo` (full 42-char, case-insensitive) before any funds move.
24. **[Fleet price oracle — live price sheet for every wall](recipes/24-fleet-price-oracle.md)** — a free, read-only, stdlib-only script that decodes all nine paid walls in one pass and emits `registry/fleet-price-sheet.json` with a `generated_at` stamp: actual `accepts[0].amount`, canonical payTo, scheme and network per wall. Fixes doc drift at the source (the live 402), not by hand-maintained price tables. Exit 1 on any drift.
25. **[Payment-header conformance guard](recipes/25-payment-header-conformance.md)** — a read-only, stdlib-only guard that fails if any recipe still teaches the stale `PAYMENT-SIGNATURE` header instead of the verified `X-PAYMENT` header (which would silently re-challenge a buyer and cause a double-pay). 25 recipes scanned, 0 violations, verdict PASS on 2026-11-25; snapshot `registry/header-conformance.json`.
26. **[Pick My Paywall — live-grounded recommender](recipes/26-paywall-picker.md)** — a read-only, stdlib-only script that turns a buyer's need, budget and urgency into a primary pay link plus up to two alternates, sourced only from a fresh `/buy?format=json` snapshot. 36 decision leaves, canonical payTo enforced by full compare, broken walls excluded by name; exit 1 on drift. Closes the first step of the machine-buyer journey (which wall do I call?) that precedes preflight and price lookup.
27. **[Buyer receipt — prove your payment landed on Base](recipes/27-buyer-receipt.md)** — a free, read-only, stdlib-only script that takes a tx hash, decodes the on-chain USDC `Transfer` logs, and proves settlement reached canonical payTo (full 42-char compare) at the expected amount — no trust in the seller's dashboard required. Closes the buyer's post-payment TRUTH gap; verified live against a real collector settle. Snapshot `registry/buyer-receipt-verification.json`.
28. **[Payment-confirmation posts](recipes/28-payment-confirmation-posts.md)** — POST-57 publication draft: a truth-grounded template plus three worked examples, each verified on-chain with recipe 27. Includes the pre-fix priceMap-1.0 ledger overstatement the verifier exposed. No external publish.
29. **[Bazaar readiness auditor](recipes/29-bazaar-readiness.md)** — grades a wall's directory metadata so a machine buyer can tell a buyable listing from a decorated stub; live 41-endpoint discovery census with 19 ready.
30. **[Intent-to-endpoint matcher](recipes/30-intent-match.md)** — turns a buyer's plain-language intent into a ranked list of actually-buyable endpoints with copy-paste unpaid curls, sourced from the live catalog.
31. **[Catalog parity audit](recipes/31-catalog-parity.md)** — finds live canonical walls the router catalog forgot to advertise; 92.3% coverage on 2026-11-25, one real gap (`contract-eye`), with a CI `--fail-on-gap` mode.
32. **[Buyer failure triage + live doc-truth audit](recipes/32-failure-triage.md)** — maps any observed buyer HTTP outcome to a `do_not_repay` verdict (the silent-rechallenge / double-pay trap), and audits the seven live router docs for stale retry headers, stale down-claims and stale verification stamps. 9 findings on 2026-11-26; read-only, no signing.
33. **[Canonical address guard](recipes/33-address-guard.md)** — classifies every `0x…` address in any text/file/URL against the canonical / retired / AgentCash roles and flags poison homoglyphs within Hamming distance ≤2. Hard-block before paying a lookalike; CI-safe (exit 1 on RETIRED/POISON).
34. **[Broker presence monitor](recipes/34-broker-presence.md)** — asks the four public discovery surfaces (agent402.tools, 402index, payapi.market, CDP Bazaar) where machine buyers actually look whether a seller is listed, *claimed*, dispatch-eligible and canonical-payTo; exact-host match only, UUID GET for pending review, bounded Bazaar scan, exit 1 on payTo drift. 2026-11-26: 14 exact 402index rows, 3 payapi listings all Unclaimed, BriefSnap UUIDs still not live, `routerDispatchEligible: false` on all five sellers. Absence is a GAP, not a failure; claiming is owner-lane.
35. **[llms.txt buyer-surface linter](recipes/35-llms-lint.md)** — checks the first surface a machine buyer reads against two independent truths: the canonical address set and a fresh live 402 decode. 2026-11-26: 6/6 surfaces up, verdict DRIFT — gateway lists internal AgentCash as "Payer wallet" (misrouting risk), five docs omit canonical payTo, and the shared directory quotes contract-eye at $0.05 (live $0.005) and royal-ruby at $0.25 (live $0.05). Includes a ready-to-apply TIFF-PLAN-19 correction content pack; read-only, no deploy.
36. **[Challenge leaderboard — live, truth-labelled proof surface](recipes/36-challenge-leaderboard.md)** — closes TIFF-PLAN-20: builds a buyer-facing `/challenge leaderboard` from the collector's tx-gated `/stats` + `/ledger.json`, ranked by 24h challenges with verified-settle proof, honest internal/external split, and a fresh x402 v2 decode on three kept-live walls. 2026-11-26: 11 walls ranked, 2,008 challenges/2 verified settles in 24h, external revenue $0.00 (all 45 settles internal self-pays), live prices $0.05/$0.005/$0.05 canonical on Base. Snapshot `registry/challenge-leaderboard.json` + buyer copy `registry/challenge-leaderboard.md`; read-only, no deploy.
37. **[Playground walkthrough — make the buyer's first 402 trustworthy](recipes/37-playground-walkthrough.md)** — closes TIFF-PLAN-18: parses the live `/playground` HTML's 21 hardcoded walls+prices, re-probes kept-live walls with unpaid POSTs, and emits a truth-labelled walkthrough whose prices come only from live 402s. 2026-11-26: verdict DRIFT — 3 kept-live walls canonical ($0.05/$0.005/$0.05, eip155:8453, exact) but the playground overstates royal-ruby `/api/law-lookup` at $0.25 (live $0.05, 5× drift); 20 frozen/other walls labelled NOT VERIFIED. Snapshot `registry/playground-walkthrough.json` + buyer copy `registry/playground-walkthrough.md`; read-only, no deploy.

38. **[Consumer documentation copy pack](recipes/38-consumer-doc-pack.md)** — closes TIFF-PLAN-17: a buyer-facing doc pack whose request shapes come from each seller's live manifest (`extensions.bazaar`) and whose price / payTo / network / scheme come only from a fresh live 402. Cross-checks manifest + OpenAPI + live challenge; reports `VALIDATION_GATED` rather than inventing a schema verdict (the 402 precedes body validation). 2026-11-26: 3 kept-live walls CLEAN and canonical ($0.05 / $0.005 / $0.05, eip155:8453, exact), 0 price drift; gateway `tools/list` correctly distinguished as free discovery. Snapshot `registry/consumer-doc-pack.json` + buyer copy `registry/consumer-doc-pack.md`; read-only, no deploy.

39. **[Pay with USDC — live-grounded developer documentation](recipes/39-developer-docs.md)** — closes TIFF-PLAN-95: a quickstart + API reference + 3 integration examples whose prices / payTo / request shapes are read ONLY from a fresh live 402 and the seller's own manifest. 2026-11-26: 3 kept-live walls CLEAN and canonical ($0.05 / $0.005 / $0.05, eip155:8453, exact), 0 price drift; gateway `tools/list` flagged as free discovery. Snapshot `registry/developer-docs.json` + buyer doc `registry/developer-docs.md`; read-only, no deploy.

## MCP registry

RAEN's MCP gateway is listed at `io.github.bshelby88/raen-mcp` on the MCP Registry.

## Honesty

Fleet telemetry is public and unedited: <https://settlement-collector.fly.dev/stats>. We publish real numbers, including zero revenue.

MIT licensed. Not legal or financial advice.
6. **[x402 Payback Calculator](https://bshelby88.github.io/raen-payback-calculator/)** — see what pay-per-call actually costs vs a flat SaaS subscription at your call volume.
7. **[x402 Launch Readiness Scorecard](https://bshelby88.github.io/x402-scorecard/)** — shipping your own paid API? Score how agent-ready it is in 60 seconds.
