# Recipe 29 — Bazaar readiness audit (make a paywall findable by machine buyers)

**Status:** live-verified 2026-11-25 · read-only · no wallet, no signing, no POST

## The problem this closes

A wall can be healthy, canonical, and priced — and still earn **$0** because an
autonomous agent cannot find or call it. Directory verifiers reach the
`/.well-known/x402.json`, then reject endpoints that advertise `method: POST`
but carry **no `extensions.bazaar`**, no `input.method`, or an empty example
body. The agent never sees a usable challenge, so it never pays. Price is not
the binding constraint; machine-discoverability is.

## The check

```bash
python3 scripts/bazaar-readiness.py --pretty \
  contract-eye-x402 rae-fleet-router royal-ruby-x402
```

For every advertised endpoint the auditor reports `READY` or `GAP` on the five
fields discovery requires:

1. `accepts.scheme == exact`
2. `accepts.network == eip155:8453`
3. `accepts.payTo == 0x9b8a27e03ceba490953cda8ab1291c0e13baf72f` (case-insensitive)
4. `extensions.bazaar.info.input.method` present and a valid HTTP verb
5. `extensions.bazaar.info.input.body` present and non-empty

A `READY` endpoint also emits a `registration_payload` — a 402index-style
`{url, http_method, probe_body, price_usd, payment_asset, payment_network}`
object built from the *served* manifest, so the probe reaches a 402 instead of
a 400. No field is invented; no number is hardcoded.

## Worked example (live read, 2026-11-25 14:4x CT)

Across 14 reachable manifests / 41 advertised endpoints:

| Wall | Endpoints | READY | Verdict |
|---|---|---|---|
| contract-eye-x402 | 4 | 3 | `/api/analyze-contract` $0.005 POST with a real `{text, focus}` body — READY |
| rae-fleet-router | 7 | 0 | all bundle/tip routes advertise POST but no bazaar method/body — GAP (Gate 4) |
| royal-ruby-x402 | 12 (7 paid) | 5 | law-lookup, validate-json, address-check, x402-audit, site-audit READY; ping/cold-start-kit GET-only |
| briefsnap-x402 | 4 | 0 | four POST routes with empty bazaar bodies — GAP |
| nanobanana-x402 | 2 | 2 | both image routes READY at $0.01 |
| suprapack-x402 | 3 | 3 | all three READY at $0.005 |

36 of 41 endpoints pay the canonical address; the other 5 are free (non-paid)
royal-ruby routes with no `accepts` block — not drift.

## Turning a GAP into a listing

1. Fix the manifest at the source so the served `.well-known/x402.json` carries
   a real `input.method` plus a non-empty `body` for the paid route.
2. Re-read with this tool — the endpoint must flip to `READY` **live**, not just
   in the repo. A source-only fix that has not shipped is still a GAP.
3. Take the emitted `registration_payload` and POST it to the directory. Never
   hand-write a `probe_body` from memory — that is how a probe lands on a 400.
4. Confirm the directory reads the URL back with the same `http_method` and a
   non-empty body. "Submitted" is not "listed"; read the record back.

## Falsifier

If a wall is `READY` here and still shows zero discovery after a settled
payment through the CDP facilitator, the metadata theory is dead and the gate
is rail/settlement only — record that and stop patching manifests.

## Boundaries

Read-only. It fetches public JSON and prints JSON. It does not register,
sign, spend, deploy, or mutate any service. Screenshots of a manifest are not
evidence — the live JSON is.
