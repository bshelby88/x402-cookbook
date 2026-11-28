# Acquisition-Offer Disclosure Auditor — buyer card ( Innovation 64 )

Live snapshot: `registry/offer-disclosure.json` · generated 2026-11-28T00:20Z · verdict `DISCLOSURE_GAPS`.

An autonomous buyer reads the **live 402 body** at the moment of sale, not the marketing manifest. This tool compares the two.

| wall | 402 | first-call-free | bulk tier | redeem path | free dev key |
|---|---|---|---|---|---|
| royal-ruby | $0.005 canonical | **not disclosed** (manifest promises it) | disclosed | disclosed | — |
| contract-eye | $0.005 canonical | — | — | — | — |
| nanobanana | $0.01 canonical | — | — | — | — |
| raen-mcp-gateway | $0.005 canonical | disclosed | — | — | disclosed |

**Buyer note:** royal-ruby's first call is free (charge-and-rebate, net $0) if you set `x-payer-address` to your 0x wallet on the paid request — the hook is in the public manifest but missing from the 402. The gateway discloses its equivalent hook in `payment_instructions`. All four walls are canonical: `exact` / `eip155:8453` / `0x9b8a27e03ceba490953cda8ab1291c0e13baf72f`. No free backdoors, no retired payTo.

Disclosure gap is a docs handoff, not a paywall defect. Pricing and deploys are owner-gated.
