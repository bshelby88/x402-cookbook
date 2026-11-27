# 61 — Machine-Buyer Price-Band Conformance Auditor

**Purpose.** Grade every kept-live paid wall's LIVE 402 price against the
data-derived machine-buyer winner band, not merely against its own docs.

**Why this exists.** The owner's MAIN OBJECTIVE is autonomous agents buying
on RAEN, and new challenges must be compared to ACQUIRED DATA before acting.
The consolidated world audit (88,788 Bazaar resources, dollar-verified
earners) found that the only proven machine-buyer winners sell per-call
consumables at **p25/median/p75 = $0.003/$0.003/$0.005**, winner band
**$0.003–$0.01**. A wall priced above $0.01 sits in the dead zone (too much
for a micro-budget agent, too little for a human); below $0.003 is under the
proven floor. Tools 48 (schema parity), 57 (bridge doc-vs-live) and 58
(volume-tier docs) never evaluated price against this acquired band.

**What it does.** READ-ONLY, stdlib-only, unpaid. For each of the 3 direct
walls + 5 gateway tools, POST the paid route with a body and NO X-PAYMENT,
base64-decode the 402 `payment-required` header, read `accepts[0].amount`
(x402 v2, 6-dp base units), verify canonical payTo + `exact` + `eip155:8453`,
and grade `IN_BAND` / `BELOW_BAND` / `ABOVE_BAND` / gate-defect. Never signs,
never pays, never changes a price.

**Run**
```
python3 scripts/price-band.py
python3 scripts/price-band.py --out registry/price-band.json
python3 scripts/price-band.py --check
```
`--check` exits 1 ONLY on a hard gate defect (noncanonical payTo, network/
scheme drift, no decodable 402, unreachable). Band drift is a WARN + owner
handoff, never an auto-fix — pricing is owner-gated.

**Latest run (2026-11-27).** 8 probes, 7 IN_BAND, 0 hard defects. One signal:
`gateway:ticker` at **$0.001 is BELOW the $0.003 winner floor** (consistent
with the persistent advertised-$0.005 / live-$0.001 drift). Owner-gated
handoff only — no price changed.
