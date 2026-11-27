# 47. Crawlable API Origin Card — give an API-only wall a homepage buyers can read

The first 46 cookbook tools assume the buyer already found you. This one fixes
the step *before* that: an API-only x402 origin whose `/` returns 404 is graded
by directory/trust crawlers as having **no crawlable homepage** and is refused
or invisible — even when its paid route is healthy and canonical.

This is not hypothetical. Staci's 2026-11-26 trust-badge exec ran 402registry
audits and got **`contract-eye-x402.fly.dev` and `dispute-forge-x402.fly.dev`
refused (score 18, 13 findings)**, root cause: "API-only services whose `/` has
no crawlable HTML homepage — 402registry audits what GPTBot/ClaudeBot see."
The gateway passed at 79 with a simple HTML `/`. Discovery breadth is the only
surface that has ever produced an external payer for RAEN, so an uncrawlable
origin is a real acquisition defect, not a cosmetic one.

`scripts/crawlable-origin.py` is a read-only, stdlib-only generator that turns a
**live-decoded** x402 offer set into a static, crawler-readable `index.html`:
semantic `<h1>`, meta description, `index,follow` robots meta, a JSON-LD `WebAPI`
block whose `offers[]` carry `price`, `priceCurrency: USD`, the full canonical
`payTo`, `eip155:8453`, `exact` scheme and integer `amount`, a visible price
table, and links to `x402.json` / `agent-card.json` / `llms.txt` / public
settlement telemetry. No JavaScript, no external assets — readable by
GPTBot, ClaudeBot and plain HTTP clients alike.

## Why this is a machine-buyer acquisition asset

- **Repairs the proven path.** Directory/crawler discovery, not outreach, is the
  only surface that has ever converted an external payer. This makes refused
  API-only origins crawlable and listable.
- **Live-grounded, not hand-typed.** `--probe` sends one **unpaid** POST, decodes
  the base64 `payment-required` header (or the enriched `accepts[]` body), and
  reads price / payTo / network / scheme from the challenge itself. The live 402
  is declared authoritative over the snapshot.
- **Drift guard is structural.** The generator refuses to emit a page unless
  every offer has the FULL canonical payTo (case-insensitive, homoglyph-safe),
  `eip155:8453`, `exact`, USDC Base and a positive integer `amount`. Any drift
  returns `FAIL_DRIFT` and writes nothing.
- **CI-grade validator.** `--check` parses the emitted HTML and JSON-LD and
  re-verifies canonical facts, so a stale or hand-edited page is caught.

## Run

```bash
# 1) build a spec, then fill its challenge from a live unpaid 402
python scripts/crawlable-origin.py --spec registry/crawlable-origin.json \
  --probe https://contract-eye-x402.fly.dev/api/analyze-contract --method POST \
  --body '{"text":"sample contract text for crawlable discovery probe"}'
# 2) generate the crawlable homepage
python scripts/crawlable-origin.py --spec registry/crawlable-origin.json --out index.html
# 3) validate before publishing
python scripts/crawlable-origin.py --spec registry/crawlable-origin.json --check index.html
```

Publishing the generated HTML at the origin's `/` is a deploy-lane action
(Bean/Kip). This recipe only builds and validates the artifact; it deploys
nothing, signs nothing and spends nothing.

## Live verification (2026-11-27T04:18Z)

- **Live probe PASS:** contract-eye `POST /api/analyze-contract` → HTTP 402,
  `accepts[0]` = `scheme exact`, `network eip155:8453`, `amount "5000"`
  ($0.005), asset USDC Base, payTo `0x9b8a27e03CEbA490953cDa8AB1291c0E13bAf72f`
  (mixed-case full canonical match) — no drift.
- **Generate PASS:** 1 offer, 3337-byte HTML, `VERDICT CANONICAL`; JSON-LD
  `WebAPI` with `offers[]`, full canonical payTo present in page.
- **Validate PASS:** `--check` on the generated file → `VERDICT CANONICAL`,
  exit 0.
- **Drift guard PASS:** a deliberately homoglyph-poisoned payTo
  (`...af72e`) → `FAIL_DRIFT`, no page generated.
- Read-only. No signing, no X-PAYMENT, no RPC money call, no funds moved, no
  external send, no deploy.

## Honesty

A crawlable homepage removes a discovery *defect*; it does not manufacture
demand. Fleet external revenue earned remains **$0.00**. The one $0.002 payment
observed this cycle came from breadth-class crawler `0xc9c7b38c...1670`
(156 payees / 6.4 days, p50 $0.003) and is U5-excluded breadth traffic — not a
customer — per the standing TIFF-BUYER-05 falsifier. See recipe 41 for the
independent trust-coverage gaps.

MIT licensed. Not legal or financial advice.
