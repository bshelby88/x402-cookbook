# 55. Machine-Buyer Repeat Passport — verifiable spend, honest repeat KPI

**Read-only, stdlib-only, no signing, no X-PAYMENT, no deploy, no funds.**

Tools 41–54 grade the wall, the manifest, the schema, the payer wallet, the receipt,
trust, crawlers, chain, funnel and settlement dependability. None answers the buyer's
own question *after* it has paid: **"can I prove my spend to a machine, and does the
fleet actually count repeat buyers?"** A canonical 402 is a promise; a settlement is
a fact; a *repeat* settlement is a relationship. This tool turns a payer's own
verified on-chain settlement history into a portable **spend passport** — an
agent-readable credential an autonomous buyer can present — and publishes the honest
KPI the owner actually set: **repeat buyers × calls/payer**.

## Why this is an acquisition tool

An autonomous buyer has no account, no inbox, no support ticket. The only reputation
it can carry between services is **verifiable on-chain spend**. A portable passport
gives it a reason to consolidate calls on RAEN (build a track record) and gives RAEN
a way to recognise a returning machine buyer instead of treating every call as a
stranger. That is the repeat-buyer mechanic the owner's KPI rewards.

But the credential is worthless if it is handed to scanners. So the tool's most
important behaviour is a **refusal**: it will not issue a passport to bread-class
crawler dust, no matter how many transfers that wallet made.

## What it measures (chain truth, not collector claims)

1. **Player list** from the public collector ledger (`/ledger.json`) — a candidate
   list only.
2. **On-chain verification** per external payer: `eth_getTransactionReceipt` on Base
   with a chainId `0x2105` guard, ERC-20 `Transfer` decoded from the receipt logs,
   confirming `to == canonical`, `from == payer` (EIP-3009 relayers are *not*
   attributed as the buyer), `value` and status `0x1`. A claim with no verified
   receipt is never counted.
3. **Exclusion first, credential second.** Internal fleet wallets (AgentCash full
   address, retired wallet) are test traffic. Behaviour-classified breadth-crawlers
   from tools 51/52 are machine discovery, not demand. Both are recorded transparently
   as `crawler_exclusions` with the evidence for the refusal — never silently skipped.
4. **KPI**: genuine external payers, repeat buyers (≥2 verified calls or ≥2 walls),
   calls-per-payer, verified received USD, and **honest external earned = $0.00**
   unless a delivery signal exists (a settle without delivery is RECEIVED, not EARNED — ARC-60).

## Passport vs exclusion

| Payer class | Calls | Passport | In KPI |
|---|---|---|---|
| Genuine external, ≥2 verified calls | 2+ | `REPEAT_BUYER` | counted |
| Genuine external, 1 verified call | 1 | `TOURIST` | counted |
| Internal (AgentCash / retired) | any | none | excluded (test traffic) |
| Breadth-crawler dust | any | **NO PASSPORT** | excluded (not demand) |

## 2026-11-27 live run (13:52Z)

```
verdict OK   chain_verified true (base.publicnode.com, chainId 0x2105)
external_payers 0   repeat_buyers 0   calls/payer 0.0   honest_external_earned $0.00
NO PASSPORT 0x171d8021b98c53dc  calls 2  logged_usd 0.01   breadth-crawler dust
NO PASSPORT 0xc9c7b38c0942914f  calls 1  logged_usd 0.002  breadth-crawler (TIFF-BUYER-05)
```

The two wallets an earlier cycle read as "the first multi-service repeat machine
payer" are **both** behaviour-classified breadth-crawlers (tool 51: `0x171d…50fca`
= 41 tx / 20 recipients / 33 min; tool 52: its $0.10 is scatter, not demand). This
tool compared to that acquired data *before* acting and issued **no passport** — the
honest repeat-buyer count is **0**, which is exactly what the Dec 8 baseline must
measure from. When a genuine external payer appears, the same run will mint its
passport automatically; no code change needed.

## Snapshots

- `registry/repeat-passport.json` — full live report (KPI + passports + crawler exclusions).
- `registry/repeat-passport.md` — buyer-facing "how to earn a passport" card.

## Truth and scope

Frozen apps are never touched. No payment, signing, deploy or external send is made.
The collector ledger is a candidate list; the chain is authoritative. Live 402 decode
and receipts outrank any snapshot. Honest external earned stays **$0.00**; the
passport is a *repeat-buyer credential*, and the tool refuses to counterfeit one.
