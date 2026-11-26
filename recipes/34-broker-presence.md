# Recipe 34 — Broker presence monitor (is the listing actually buyable?)

**Status:** shipped 2026-11-26 (Tiffany, machine-buyer acquisition). Free, read-only,
GET-only, stdlib-only. No signing, no `X-PAYMENT`, no RPC money calls, no funds
movement, no POST to any directory, no external sends.

A machine buyer does not start at your API. It starts at an index — agent402.tools,
402index, payapi.market, the CDP Bazaar — and only calls a wall if the listing looks
buyable. "Listed" is not the same as "buyable". A listing can be present but:

- carry an `Unclaimed` provider with `payment_verified: false` (payapi.market),
- sit in pending review and 404 on its own UUID GET (402index),
- show `routerDispatchEligible: false` because the reciprocal-metering floor is
  still unmet (agent402.tools),
- or point at a retired/poison payTo that silently strands the payment.

This script separates those states across four surfaces in one pass and hard-blocks
on payTo drift. It is the discovery-stage companion to recipe 23 (live 402
preflight), 27 (receipt proof), 29 (bazaar readiness), 31 (catalog parity),
32 (failure triage) and 33 (address guard).

## Run it

```bash
python3 scripts/broker-presence.py --json
python3 scripts/broker-presence.py --host contract-eye-x402.fly.dev \
    --check-id b82f0aab-b5a2-40aa-a982-dc48bf526d66 --json
python3 scripts/broker-presence.py --cdp-pages 5 --payapi-pages 40
```

`--json` emits `registry/broker-presence.json`-shaped output: per-host
`agent402`, `bazaar402index`, `payapi` blocks plus a bounded `cdp` block, a
`findings` list and a `verdict`.

Exit codes: `0` CLEAN, `1` DRIFT (RETIRED or POISON_SUSPECT payTo — CI hard-block),
`2` is reserved for all-surfaces-unreachable (reported as a finding, not a crash).
**Absence from a broker is a GAP, not a failure** — it is an acquisition
opportunity, and claiming a listing is an owner-lane action under the charter.

## Truth rules baked in

1. **Exact host match only.** The 402index `q` parameter is fuzzy and echoes the
   query; the script matches on the parsed URL's `netloc`, so a random
   `x402.cultofjames.org` row cannot be counted as a RAEN presence.
2. **A UUID GET is the review gate.** `--check-id` calls
   `GET /api/v1/services/{id}`. `{"error":"Service not found"}` means the pending
   submission is *not live* and must not be advertised as delivered.
3. **Claimed ≠ unclaimed.** payapi.market rows with `provider: "Unclaimed"` and
   `payment_verified: false` are visible but cannot be routed/claimed by a
   machine buyer. Do not cite them as demand.
4. **Bounded CDP scan.** The Bazaar has ~88k resources; the default walk reads
   10 × 200 = 2,000 items. Zero hits is reported as "zero in the scanned prefix",
   never as a full-index absence claim.
5. **payTo roles are full 42-char, case-insensitive**, reusing recipe 33's
   classification (CANONICAL / RETIRED / AGENTCASH / POISON_SUSPECT within Hamming
   distance ≤2 / UNKNOWN). A one-character homoglyph is drift, not a formatting
   difference.
6. **dispatch eligibility is its own metric.** `routerDispatchEligible: false`
   with `settlement_required` means the broker will not dispatch work to the
   fleet until a real non-self settlement lands. No checkout traffic = no
   dispatch, no matter how many listings exist.

## Grounded baseline — 2026-11-26 ~02:5xZ (this run)

Live reads, recorded with URI + as-of in the TIFFANY EXEC artifact:

- **agent402.tools** — all five seller hosts present, `health: 1`,
  `payTosByNetwork.eip155:8453` = canonical on every one; tool counts
  router 12 (7 paid), escrow 1, vault-pro 2, tradingagents 2, dispatch 3;
  `routerDispatchEligible: false` on all five. No payTo drift.
- **402index.io** — 14 exact-host rows in the `q=raen` page: nft-alpha,
  contract-eye ×2, gateway, opensea-data, nanobanana ×2, escrow, router ×5,
  royal-ruby cold-start-kit. Two BriefSnap UUIDs handed off by CROWN
  (`8fe87664…`, `caadc473…`) still return `Service not found` — pending review
  never went live. Honest: not delivered.
- **payapi.market** — full walk of all 3,581 listings found exactly 3 RAEN
  rows: Nanobanana, OpenSea Collection Data, RAE Fleet Router bundle. All three
  `provider: "Unclaimed"`, `payment_verified: false`. Visible, not claimable.
- **CDP discovery** — 0 canonical/RAEN hits in the first 4,000 of 88,438
  resources (bounded; not a full-index claim). Passive indexing decays without
  settles, so this is consistent with $0 external revenue, not a defect.

Collector truth at the same time: 1,994 challenges / 2 settled (both internal
$0.002 self-pays) / 222 failed, external revenue `$0.00`. Chain truth: canonical
18.176651 USDC on Base, retired 16.628295 on Base, AgentCash 2.629259 Base +
15.0 ETH mainnet — unchanged. **External earned revenue: $0.00, honest.**

## Owner-gated handoff

Claiming the three payapi.market listings, activating a real non-self settlement
to lift `routerDispatchEligible`, and re-registering the two BriefSnap UUIDs are
all owner/identity-lane or require a funded payer. This recipe never performs
them; it produces the evidence for the handoff.

No publish, no deploy, no outbound post. Staged on GitHub as code and docs only.
