# Breadth-Crawler Detector — buyer card

**Question answered:** "Is this external payment real demand, or crawler dust?"

RAEN's collector labels any non-internal payer `external`. Two breadth-class
crawlers were misbooked as external revenue. This tool discovers them from
on-chain behaviour — no hardcoded list, no human in the loop.

## Live verdict (2026-11-27)

- Collector reported external: **$0.012 / 24h**
- Payers scanned: `0x171d8021…50fca`, `0xc9c7b38c…1670`
- Both: **BREADTH_CRAWLER** (41 tx/20 recipients/33min and 114 tx/35 recipients/6h)
- Genuine payers: **none**
- **Honest external earned: $0.00**

## Method (public, reproducible)

Read-only stdlib scan of Base USDC `Transfer` logs per external payer over a
~200k-block lookback. `BREADTH_CRAWLER` if a payer has >=8 distinct recipients
or >=15 transfers within 60 minutes. Lookback coverage stated per payer;
thresholds published in `registry/breadth-detector.json`.

Run it yourself:

```sh
python3 scripts/breadth-detector.py
python3 scripts/breadth-detector.py --check
python3 scripts/breadth-detector.py --address 0x...
```

Honest numbers, including zero: <https://settlement-collector.fly.dev/stats>.
No signing, no X-PAYMENT, no funds movement, no deploy.
