# 43. Machine-Buyer Readiness Scorecard — one go/no-go number per wall

*Tiffany Innovation 43 · 2026-11-26 · read-only, stdlib-only, no funds moved*

## The problem

An autonomous agent deciding *where* to spend has a funnel to clear: discover the
seller, read the docs, find the price, get a parseable 402, trust the seller enough
to sign, and finally retry with the right payment header. Existing cookbook tools
each grade exactly one of those stages. A buyer (or the fleet itself) still has no
single answer to "is this wall actually ready to take my first payment, and which
wall should I try first?"

## What this tool does

`scripts/buyer-readiness.py` walks the whole funnel for each kept-live wall with
**unpaid reads only** and emits one score (0–100) plus a buyer-facing quickstart.

Scoring, all from live reads:

| Component | Points | Live source |
|---|---|---|
| Paid challenge is canonical | 40 | unpaid POST → decode `payment-required` → x402 v2, `exact`, `eip155:8453`, full canonical `payTo`, integer `amount>0` |
| Manifest canonical | 20 | `/.well-known/x402.json` priced accept block, canonical scheme/network/payTo |
| Discovery doc | 20 | `/llms.txt` 200 and names full canonical `payTo` |
| Independent trust | 10 | Lumi trust check returns a record (not `no_data`/error) |
| Explicit price | 10 | manifest accept block carries `price` |

Grade: `>=80 READY`, `50–79 PARTIAL`, `<50 NOT_READY`.

Honesty rules baked in:

- The **live 402 is authoritative**. A missing manifest price is a WARN, never a
  fake price — the real price comes from the challenge `amount`.
- CI fails **only** on a `CANONICAL_BREAK` (a wall whose paid 402 is broken or
  non-canonical). Discovery/trust/price gaps are published as friction, not hidden
  and not treated as a payment break.
- Homoglyph-safe: `payTo` is compared as the full 42-char address, case-insensitive,
  never a substring/pattern match.
- BURN FREEZE respected: only kept-live walls are probed; frozen services are never
  touched locally.

## Run it

```
python3 scripts/buyer-readiness.py
python3 scripts/buyer-readiness.py --out-json registry/buyer-readiness.json \
    --out-md registry/buyer-readiness.md
```

Exit codes: `0` no canonical break · `1` a paid path is broken · `2` no wall reachable.

## Live result — 2026-11-26T13:30Z

Verdict `OK`, no paid-path break. Scores:

| Wall | Score | Grade | Live price | Note |
|---|---|---|---|---|
| royal-ruby | 90 | READY | $0.0500 | manifest omits `price` (live 402 authoritative) |
| contract-eye | 80 | READY | $0.0050 | `/llms.txt` omits canonical payTo |
| nanobanana | 80 | READY | $0.0100 | `/llms.txt` omits canonical payTo |
| raen-mcp-gateway | 70 | PARTIAL | $0.0500 | `tools/list` free discovery; no Lumi record; llms.txt payTo gap |

All four paid POST challenges decoded as x402 v2 / `exact` / `eip155:8453` / full
canonical `0x9b8a…f72f` / positive integer `amount`. Warnings are real buyer
friction, published honestly — none is a payment break. Snapshots:
`registry/buyer-readiness.json` (machine-readable) and `registry/buyer-readiness.md`
(buyer-facing "where to spend first" card).

## Buyer takeaway

Pick the highest READY score with a `canonical` paid path, then retry with the
seller's documented `X-PAYMENT` header. Never pay a wall whose paid path reads
`BREAK` or whose `payTo` is not the full canonical address. Read-only: this tool
never signs, never sends an `X-PAYMENT` header, never moves money.
