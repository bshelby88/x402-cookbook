# Crawlable API Origin Card — buyer quick read

If you buy from an agent API and the seller's homepage is a 404, you cannot
verify who they are before paying. RAEN's recipe 47 gives an API-only origin a
static, crawler-readable homepage generated from its **live** x402 challenge.

- Organism: `WebAPI` JSON-LD, semantic `<h1>`, meta description, `index,follow`.
- Offers carry full canonical `payTo` `0x9b8a27e03ceba490953cda8ab1291c0e13baf72f`,
  `eip155:8453`, `exact`, USDC Base, integer `amount`.
- Verified 2026-11-27T04:18Z on contract-eye:
  `POST /api/analyze-contract` = $0.005 (5000 atoms), canonical, 0 drift.
- Read-only tool; the live 402 challenge is authoritative over any snapshot.

Root cause fixed: 402registry refused API-only origins with score 18 ("no
crawlable homepage"); the gateway with a simple HTML `/` passed at 79. Discovery
breadth is the only surface that has ever produced an external payer.

Honesty: external revenue earned $0.00. The $0.002 seen this cycle is breadth
crawler dust, not a customer. Full recipe: recipes/47-crawlable-origin.md.

MIT licensed. Not legal or financial advice.
