#!/usr/bin/env python3
"""Innovation 56 - Lapsed Machine-Buyer Churn & Reactivation Auditor.

Read-only, stdlib-only. Measures the RETENTION side of the owner KPI
(repeat buyers x calls/payer) from the collector ledger, re-applying the
breadth-crawler exclusion discovered by tools 50/51/52 so crawler dust can
never be counted as a lapsed/reactivation buyer. Sizes a suggested return
credit from a LIVE 402 price. NEVER moves funds, signs, sends, or deploys.
"""
import json, sys, urllib.request, urllib.error, base64, datetime, argparse

CANONICAL = '0x9b8a27e03ceba490953cda8ab1291c0e13baf72f'
RETIRED   = '0x7861db4efc14a1ed5dd8c96c528a3796560f1393'
AGENTCASH = '0xfbc0eb7811d477e55261d956df39f0046e192240'
COLLECTOR = 'https://settlement-collector.fly.dev'
BREADTH_URL = ('https://raw.githubusercontent.com/bshelby88/x402-cookbook/'
               'main/registry/breadth-detector.json')
LIVE_WALL = ('https://royal-ruby-x402.fly.dev', '/api/law-lookup')
LAPSED_DAYS = 7.0          # configurable churn threshold
UA = 'Mozilla/5.0 (compatible; RAEN-Tiffany/56; +https://raen.dev)'

def fetch(url, data=None, headers=None, timeout=25):
    h = {'User-Agent': UA}
    if headers: h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read(), dict(r.headers)

def json_url(url):
    _, b, _ = fetch(url)
    return json.loads(b)

def crawl_set():
    """Behaviour-discovered breadth crawlers (tool 51) with a safe fallback."""
    try:
        d = json_url(BREADTH_URL)
        return set(x.lower() for x in d.get('breadth_crawlers', [])), 'live-registry'
    except Exception:
        return set(['0x171d8021b98c53dcbb3c9c30cbbbeb1b01850fca',
                    '0xc9c7b38c0942914fc8ea12063bc92dcd3b581670']), 'embedded-fallback'

def live_price():
    """Decode the LIVE 402 amount (x402 v2 'amount', atoms) for offer sizing."""
    try:
        body = json.dumps({'topic': 'credit report dispute', 'state': 'federal-only'}).encode()
        try:
            fetch(LIVE_WALL[0] + LIVE_WALL[1], data=body,
                  headers={'Content-Type': 'application/json'})
            return None, 'no-402 (unexpected 2xx)'
        except urllib.error.HTTPError as e:
            hdrs = dict(e.headers)
            pr = hdrs.get('payment-required') or hdrs.get('x-payment-required') or ''
            raw = pr
            try: raw = base64.b64decode(pr).decode()
            except Exception: pass
            j = json.loads(raw)
            acc = j.get('accepts', [{}])[0]
            atoms = int(acc.get('amount') or 0)
            return {'amount_atoms': atoms, 'usd': atoms/1e6,
                    'scheme': acc.get('scheme'), 'network': acc.get('network'),
                    'payTo': acc.get('payTo')}, 'live-402'
    except Exception as e:
        return None, 'unavailable:' + type(e).__name__

def classify(payer, crawlers, tx):
    p = (payer or '').lower()
    if p in (CANONICAL, RETIRED, AGENTCASH):
        return 'internal'
    if p in crawlers or 'crawler' in str(tx.get('payer_label', '')).lower() \
       or tx.get('classification') == 'crawler':
        return 'crawler'
    if tx.get('classification') == 'internal' or tx.get('profile_known'):
        return 'internal'
    return 'genuine_external'

def run(check=False):
    crawlers, csrc = crawl_set()
    led = json_url(COLLECTOR + '/ledger.json')
    stats = json_url(COLLECTOR + '/stats')
    txs = led.get('transactions', [])
    price, psrc = live_price()

    buckets = {'internal': 0, 'crawler': 0, 'genuine_external': 0}
    payers = {}
    now_ms = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)
    for t in txs:
        k = classify(t.get('payer'), crawlers, t)
        buckets[k] += 1
        if k != 'genuine_external':
            continue
        p = t.get('payer').lower()
        rec = payers.setdefault(p, {'payer': p, 'calls': 0, 'total_usd': 0.0,
                                    'services': set(), 'first_ts': t['ts'],
                                    'last_ts': t['ts'], 'txs': []})
        rec['calls'] += 1
        rec['total_usd'] += float(t.get('amount_usd') or 0)
        rec['services'].add(t.get('service'))
        rec['first_ts'] = min(rec['first_ts'], t['ts'])
        rec['last_ts'] = max(rec['last_ts'], t['ts'])
        rec['txs'].append(t.get('tx'))

    genuine = []
    for p, rec in payers.items():
        days = (now_ms - rec['last_ts']) / 86400000.0
        rec['days_since_last_call'] = round(days, 2)
        rec['lapsed'] = days >= LAPSED_DAYS
        rec['verdict'] = 'LAPSED_REACTIVATION_CANDIDATE' if rec['lapsed'] else 'ACTIVE'
        # Suggested return credit: 3 calls at the LIVE price, capped $0.05.
        unit = price['usd'] if price else 0.005
        rec['suggested_return_credit_usd'] = round(min(3 * unit, 0.05), 4)
        rec['redemption_path'] = 'claims desk (cookbook recipe 22) - NO auto-send'
        rec['services'] = sorted(rec['services'])
        genuine.append(rec)
    genuine.sort(key=lambda r: -r['calls'])

    external_spend = round(sum(r['total_usd'] for r in genuine), 6)
    lapsed = [r for r in genuine if r['lapsed']]
    total_calls = sum(r['calls'] for r in genuine)
    fleet = stats.get('fleet_24h', {})

    out = {
        'tool': 'buyer-churn', 'innovation': 56,
        'generated_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'chain_scope': 'ledger from settlement-collector; price cross-checked on Base',
        'thresholds': {'lapsed_days': LAPSED_DAYS,
                       'reactivation_offer': 'min(3 x live price, $0.05)'},
        'data_sources': {'ledger_tx_count': len(txs),
                         'breadth_source': csrc, 'price_source': psrc,
                         'live_price': price},
        'exclusions': {'internal_tx': buckets['internal'],
                       'breadth_crawler_tx': buckets['crawler'],
                       'breadth_addresses': sorted(crawlers),
                       'note': 'internal wallets + behaviour-discovered crawlers are '
                               'NOT buyers; excluded before churn KPI'},
        'kpi': {'genuine_external_payers': len(genuine),
                'active_buyers': len(genuine) - len(lapsed),
                'lapsed_buyers': len(lapsed),
                'reactivation_candidates': len(lapsed),
                'calls_per_payer': round(total_calls/len(genuine), 3) if genuine else 0.0,
                'honest_external_earned_usd': external_spend,
                'collector_reported_external_usd_24h': fleet.get('revenue_external_usd'),
                'total_calls_tracked': total_calls},
        'genuine_buyers': genuine,
        'verdict': ('CHURN_TRACKING' if genuine else 'NO_GENUINE_BUYERS'),
        'method': ('Retention half of the KPI: from the collector ledger, exclude '
                   'internal wallets (canonical/retired/AgentCash) and behaviour-'
                   'discovered breadth crawlers (tool 51/52), then aggregate genuine '
                   'external payers by first/last call to flag lapse and size a '
                   'LIVE-priced return credit.NO funds moved, no signing, no sends, '
                   'no deploy. Read-only.'),
    }
    # canonical drift guard on the live price (if present)
    drift = bool(price and price.get('payTo') and
                 price['payTo'].lower() != CANONICAL)
    # misclassification guard: a genuine payer must not be an internal/crawler addr
    misclass = any(r['payer'] in crawlers or r['payer'] in
                   (CANONICAL, RETIRED, AGENTCASH) for r in genuine)
    out['guards'] = {'canonical_payto_drift': drift,
                     'misclassified_internal_as_buyer': misclass}
    if check:
        bad = drift or misclass
        print(('FAIL' if bad else 'OK') + ' buyer-churn guards: '
              'canonical_drift=' + str(drift) +
              ' misclassification=' + str(misclass))
        return 1 if bad else 0
    print(json.dumps(out, indent=2))
    return 0

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    sys.exit(run(check=a.check))
