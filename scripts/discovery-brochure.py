#!/usr/bin/env python3
"""Tiffany Innovation 59 - Discovery Brochure Auditor.

The public buyer-facing 'brochure' (GitHub Pages buyer tools, the cookbook, law
pages, llms.txt, the router catalog, MCP Registry) is the first surface a machine
buyer or its code generator reads. Tools 1-58 grade walls, docs-at-the-wall, the
payer, the ledger and the chain -- but none grades this storefront window for
liveness (the Vercel 'Ready but 404 on all paths' trap) or for a RETIRED payTo
leak that silently misroutes money. This tool closes that gap.

Read-only, stdlib-only. No signing, no X-PAYMENT, no funds, no deploy, no sends.
--check exits 1 ONLY on HARD_DRIFT (retired payTo leak) -- never on a missing
payer, a down page (a GAP, handed off), or owner-gated price/doc drift.
"""
import json, sys, re, urllib.request, datetime

CANON = '0x9b8a27e03ceba490953cda8ab1291c0e13baf72f'.lower()
RETIRED = '0x7861db4efc14a1ed5dd8c96c528a3796560f1393'.lower()
AGENTCASH = '0xfbc0eb7811d477e55261d956df39f0046e192240'.lower()
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36'}

# url, label, expects_canonical_payto
SURFACES = [
    ('https://raw.githubusercontent.com/bshelby88/x402-cookbook/main/README.md', 'cookbook README', True),
    ('https://bshelby88.github.io/raen-first-call-free/', 'first-call-free Pages', True),
    ('https://bshelby88.github.io/raen-payback-calculator/', 'payback-calculator Pages', False),
    ('https://bshelby88.github.io/x402-scorecard/', 'x402-scorecard Pages', True),
    ('https://raen-law-pages.vercel.app', 'law pages', False),
    ('https://raen-agent-directory.vercel.app/llms.txt', 'agent directory llms.txt', True),
    ('https://rae-fleet-router.fly.dev/catalog.json', 'router catalog', True),
    ('https://registry.modelcontextprotocol.io/v0.1/servers?search=raen', 'MCP Registry listing', False),
]

ADDR_RE = re.compile(r'0x[0-9a-fA-F]{40}')
# A retired address in a WARN context ("reject the retired wallet ...") is correct
# buyer guidance, not drift. Only an un-warned occurrence is a money-misroute risk.
REJECT_KW = re.compile(r'reject|retired|avoid|do\s+not|deprecated|old|homoglyph|'
                       r'lookalike|poison|banned|stale|not\s+canonical|misrou|'
                       r'stranded|retire|no\s+longer', re.I)

def retired_drift(body):
    """Occurrences of the retired payTo NOT wrapped in a rejection warning."""
    low = body.lower()
    bad = []
    for m in re.finditer(RETIRED, low):
        window = low[max(0, m.start() - 120):m.end() + 60]
        if REJECT_KW.search(window):
            continue
        bad.append(window.strip()[:140])
    return bad

def fetch(url):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=25) as r:
            return getattr(r, 'status', None) or r.getcode(), r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, ''
    except Exception as e:
        return 0, 'ERR:' + str(e)[:80]

def hdist(a, b):
    return sum(x != y for x, y in zip(a, b))

def audit():
    rows = []
    for url, label, expect in SURFACES:
        code, body = fetch(url)
        low = body.lower()
        canon_n = low.count(CANON)
        retired_n = low.count(RETIRED)
        addrs = set(a.lower() for a in ADDR_RE.findall(body))
        poison = sorted(a for a in addrs
                        if a not in (CANON, RETIRED, AGENTCASH)
                        and (hdist(a, CANON) <= 2 or hdist(a, RETIRED) <= 2))
        empty = (not body) or body.startswith('ERR:')
        drift_ctx = retired_drift(body)
        if drift_ctx:
            verdict = 'HARD_DRIFT'          # un-warned retired payTo misroutes money
        elif code != 200 or empty:
            verdict = 'DOWN'                # GAP -> handoff, not a drift failure
        elif expect and canon_n == 0:
            verdict = 'PAYTO_MISSING'       # reader can't copy the canonical address
        elif poison:
            verdict = 'POISON_SUSPECT'
        elif expect:
            verdict = 'LIVE_CANONICAL'
        else:
            verdict = 'LIVE_INFO'
        rows.append({'label': label, 'url': url, 'http': code, 'bytes': len(body),
                     'canonical_count': canon_n, 'retired_count': retired_n,
                     'retired_drift_count': len(drift_ctx), 'retired_drift_context': drift_ctx,
                     'poison_addresses': poison, 'expects_canonical': expect,
                     'verdict': verdict})
    hard = [r for r in rows if r['verdict'] == 'HARD_DRIFT']
    warns = [r for r in rows if r['verdict'] in ('DOWN', 'PAYTO_MISSING', 'POISON_SUSPECT')]
    snap = {
        'tool': 'discovery-brochure', 'innovation': 59, 'author': 'tiffany',
        'generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'canonical_payto': CANON, 'retired_payto': RETIRED,
        'verdict': 'HARD_DRIFT' if hard else ('WARN' if warns else 'CANONICAL'),
        'surfaces': rows, 'hard': len(hard), 'warns': len(warns),
        'note': 'Read-only. --check fails only on retired-payTo leak (HARD_DRIFT). '
                'DOWN/PAYTO_MISSING are GAPs handed off, never silently auto-fixed. '
                'Price and doc drift are owner-gated and never changed here.',
    }
    return snap

def main():
    snap = audit()
    print('Discovery Brochure Auditor - innovation 59 - ' + snap['generated_at'])
    for r in snap['surfaces']:
        print('  %-13s %4s %7dB canon=%-3d retired=%d  %s' %
              (r['verdict'], r['http'], r['bytes'], r['canonical_count'],
               r['retired_count'], r['label']))
    print('VERDICT=%s  hard=%d warns=%d' % (snap['verdict'], snap['hard'], snap['warns']))
    if '--write' in sys.argv:
        with open('registry/discovery-brochure.json', 'w', encoding='utf-8') as f:
            json.dump(snap, f, indent=2)
        print('wrote registry/discovery-brochure.json')
    if '--check' in sys.argv:
        sys.exit(1 if snap['hard'] else 0)

if __name__ == '__main__':
    main()
