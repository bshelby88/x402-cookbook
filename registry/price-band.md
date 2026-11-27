# Registry entry — price-band (Innovation 61)

- **tool**: price-band
- **script**: `scripts/price-band.py`
- **recipe**: `recipes/61-price-band-auditor.md`
- **snapshot**: `registry/price-band.json`
- **category**: machine-buyer acquisition / pricing conformance
- **data basis**: consolidated world audit 2026-11-26 — winner band $0.003–$0.01, p25/median/p75 $0.003/$0.003/$0.005
- **mode**: read-only, stdlib-only, unpaid probes (no X-PAYMENT), never moves money, never changes a price
- **ci gate**: `--check` fails only on hard gate defects (noncanonical payTo, gate drift, no 402, unreachable); band drift = WARN/owner handoff
- **latest**: 8 probes, 7 in band, 0 hard defects; `gateway:ticker` $0.001 below the $0.003 winner floor (owner-gated WARN)
