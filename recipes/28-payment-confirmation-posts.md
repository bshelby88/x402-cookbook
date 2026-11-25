---
permalink: /recipes/28-payment-confirmation-posts.md
---

# Recipe 28 — Payment-confirmation posts (truth-grounded, per settlement)

**Backlog item POST-57 (Work Type: publication; claimed and closed 2026-11-25).** This is the draft content pack the row asked for: a reusable payment-confirmation post template plus three worked examples built from real settlement records — each verified on-chain with [recipe 27](27-buyer-receipt.md). No post is published by this recipe (no external sends without a human turn).

## The template

```markdown
RAEN receipt — {SHORT_DATE} — {SERVICE} / {ROUTE}

A machine buyer paid {AMOUNT} USDC on Base for {DELIVERABLE}.
Settlement to canonical payTo 0x9b8a27e0...f72f is confirmed on-chain, not
self-reported: {TX}

Verified with Recipe 27 (buyer receipt verifier): status VERIFIED,
Base block {BLOCK}, {N} USDC Transfer(s) to canonical payTo.

Scope: this proves the PAYMENT landed on Base. It is internal RAEN test
traffic unless the payer is an external wallet. External revenue to date:
$0.00 (chain truth).
```

Fill `{TX}` with a real hash and run the verifier — never hand-write the amount.

## Worked example 1 — royal-ruby `/api/law-lookup` ($0.05)

Live-verified 2026-11-25: tx `0x39ac4545c1fe8c4f795a1ff3562ecf8bbb0dd6c43ac4fa92507b9f7c908d0182`, Base block `0x3aafe80`, one USDC `Transfer` of **0.05** to canonical payTo. ERC-20 payer `0xfbc0eb7811d477e55261d956df39f0046e192240` (AgentCash); tx submitter is the facilitator `0xe72f0a…b1b8`. Classification: **internal** — do not count as revenue.

## Worked example 2 — contract-eye `/api/analyze-contract` ($0.05, corrected)

Live-verified 2026-11-25: tx `0xa677d8d1015c75fd020305575e5f7f9c951dc6e52182117f84b33d2bfef08466` settled **0.05** on-chain. Contrast with two older contract-eye records the collector logged at **$1.00** (txs `0xc1258329…` and `0xfad91831…`, 2026-11-21 08:13/08:17Z): the verifier shows those also transferred only **0.05 USDC** each. They are pre-fix artifacts of the priceMap-1.0 bug (corrected later that day), not real $1.00 revenue. **Lesson: draft the post from the chain read, never from the collector's `amount_usd` field alone.**

## Worked example 3 — raen-facilitator-worker `/settle` ($0.001)

Live-verified 2026-11-25: tx `0x428ddc362a871203fd7c8201162907627ce605bfe3757cc80e53094bf3435b7a`, one USDC `Transfer` of **0.001** to canonical payTo. Classification: **internal**.

## Truth constraints (TRUTH law)

- All three examples are internal test traffic. **External earned revenue is $0.00** — the posts must never imply a paying customer.
- Amounts come from decoded on-chain Transfer events, not the collector ledger.
- Chain scope is Base (`eip155:8453`) only; settlement is proven, delivery is a separate claim ([recipe 22](22-claims-desk.md)).
- No external publish. This pack is a draft asset for a human to review before any post goes live.

## Automation handoff

Per-settlement auto-generation is a natural next step: feed each new collector ledger row to `scripts/receipt-verifier.py`, then render the template above. Publishing remains human-gated. The collector and router are on the burn-freeze list, so no pipeline change was made in this run.
