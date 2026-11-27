# Challenge Constructability — buyer card

Before your agent signs anything, confirm the wall gave you enough to build a
valid payment. An `accepts[0]` that has a price but no `extra.name` /
`extra.version` (the EIP-3009 domain), no `asset`, or no `maxTimeoutSeconds`
cannot be turned into a typed-data authorization by a strict client.

Run `python3 scripts/challenge-fields.py --check`. Exit 0 means every kept-live
wall returned an unpaid 402 whose challenge is constructible and whose header
and body agree. A `DEFECT`, `INVALID_CHALLENGE`, `FREE_BACKDOOR` or
`NO_CHALLENGE` verdict means do not send that buyer traffic.

Prices below $0.003 or above $0.01 are WARN only (owner-gated ladder), not a
constructability failure. Live snapshot: `registry/challenge-fields.json`.
