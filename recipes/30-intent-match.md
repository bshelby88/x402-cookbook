# Recipe 30 — Intent → Buyable Endpoint (machine-buyer discovery layer)

**For:** autonomous agents that have a *need* but not a URL. **Cost to run this tool:** $0. It only reads the public catalog.

## The gap

RAEN's router publishes `/catalog.json` — 13 walls, 44 endpoints. An agent browsing it must read 44 descriptions to find the one it wants. `buyer-preflight.py` verifies a wall's payment contract, but it needs a URL first. This recipe fills the step **between** intent and URL: it ranks actually-buyable endpoints for a natural-language intent and hands back an exact unpaid probe command.

## Use

```bash
# 1) Intent -> ranked buyable endpoints (read-only, no network cost)
python3 scripts/intent-match.py "summarize a document into bullets"
python3 scripts/intent-match.py "NFT floor price signal" --json --top 3

# 2) Rebuild the filtered index snapshot (canonical payTo, status ok, priced > 0)
python3 scripts/intent-match.py --build-index registry/intent-index-20261125.json

# 3) Use a local snapshot instead of the live catalog (offline / reproducible)
python3 scripts/intent-match.py "check a contract" --catalog registry/catalog-snapshot.json
```

Example output for "summarize a document into bullets":

```
1. briefsnap   $1   POST https://briefsnap-x402.fly.dev/api/summarize
   score 2.000  terms=bullet,document,summarize
   probe: curl -s -D h.txt -o b.txt -X POST .../api/summarize -H 'Content-Type: application/json' --data-binary '{}'
```

## The full buyer chain

1. **`intent-match.py`** → endpoint URL + method + price + unpaid probe stub.
2. Replace the stub's `'{}'` body with the request body advertised in that wall's `/.well-known/x402.json` (bazaar `extensions.bazaar.info.input.body`). The stub is deliberately generic — it is a probe, not the product call.
3. Run the probe → receive HTTP 402 with a `payment-required` header.
4. **`buyer-preflight.py <url> --method POST --body '<real body>'`** → decodes the challenge, checks canonical `payTo`, network `eip155:8453`, scheme `exact`, amount, and the `X-PAYMENT` retry header. Never signs, never pays.
5. Only then sign `transferWithAuthorization` (EIP-3009) in your own wallet and re-send with `X-PAYMENT`.

## Truth limits (read before trusting a match)

- The matcher can only rank **catalog inventory**. A live wall absent from `/catalog.json` is invisible to it — see the known gap below. Absence here does **not** mean a service does not exist.
- Only endpoints with canonical `payTo 0x9b8a…f72f`, `status: ok`, and a positive price enter the index. In the 2026-11-25 census that was **30 of 44** catalog endpoints (7 untagged/free/null-price, 1 unreachable, 5 royal-ruby `wrong_network` free routes excluded). No non-canonical payTo ever enters the buyer index.
- Ranking is lexical (tag/slug/description overlap, inverse-document-frequency weighting, cheaper-wins tiebreak), not semantic. Zero token overlap → zero matches, by design — an honest "no match" beats an invented one.
- Never signs, never sends a payment header, never moves money. Exit codes: 0 matches, 1 no match, 2 catalog unavailable.

## Known gap found while building this (2026-11-25)

`contract-eye-x402.fly.dev` serves a live canonical 402 at `POST /api/analyze` for **$0.005** (decoded: `x402Version 2`, `exact`, `eip155:8453`, `amount "5000"`, canonical `payTo`) and has ~4,820 lifetime challenges / 6 verified settles — but it is **not listed at all** in the router's `/catalog.json` 13-wall host list. An agent discovering the fleet through the catalog cannot find one of its cheapest, highest-traffic walls. Flagged to `[bean][staci]` for a catalog-coverage fix; this recipe does **not** inject it manually (that would mask the gap).
