# Buyer card — Lapsed Machine-Buyer Churn & Reactivation Auditor (tool 56)

Generated from live data by `scripts/buyer-churn.py`. The live 402 is authoritative.

## What this answers
Tools 1-55 grade the wall, the docs, the payer, the ledger, the chain and the first
passport. None measures the **retention** half of the owner's KPI: *repeat buyers x
calls/payer*. This tool reads the collector ledger, removes internal wallets and
behaviour-discovered breadth crawlers, then reports how many genuine external buyers
are active vs lapsed, and sizes a return credit from a live price.

## Live read (2026-11-27)
- Collector ledger: 61 tx = 58 internal + 3 breadth-crawler + **0 genuine external**.
- Verdict: `NO_GENUINE_BUYERS`. Active 0, lapsed 0, reactivation candidates 0.
- Honest external earned: **$0.00**. The collector's $0.012/24h is recorded
  breadth-crawler dust (`0x171d8021…50fca`, `0xc9c7b38c…1670`) — NOT demand.
- Live wall: royal-ruby `/api/law-lookup` 402 `exact` / `eip155:8453` / 5000 atoms
  ($0.005) / full canonical payTo.

## Return credit (no funds moved)
If a genuine buyer lapses (>= 7 days), a return credit of `min(3 x live price, $0.05)`
is suggested, redeemed through the claims desk (recipe 22). This tool NEVER signs,
sends, moves funds or deploys — it only measures and publishes.

## Verify yourself
```sh
python3 scripts/buyer-churn.py --check   # exit 1 only on payTo drift / misclassification
python3 scripts/buyer-churn.py           # full snapshot
```
Truth layers: coordination=Library, money=chain, code=GitHub, runtime=live services.
