#!/usr/bin/env python3
"""Verify published fixture HTTP responses and source HTML. Never grades the crawler.

Example: python3 tools/verify.py https://YOUR-SITE.onrender.com --report qa/live-fixtures.json
"""
import argparse
import json
import re
import sys
import time
from collections import defaultdict
from datetime import datetime,timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError,URLError
from urllib.parse import urljoin,urlsplit,urldefrag
from urllib.request import Request,urlopen
from urllib.robotparser import RobotFileParser

ROOT=Path(__file__).resolve().parents[1]
UA='STUDIO5864FixtureVerifier/1.0'

class SourceParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_head=False;self.metas=[];self.anchors=[];self.canonical=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='head':self.in_head=True
        if tag=='meta':self.metas.append((self.in_head,a.get('name',''),a.get('content'),a.get('http-equiv','')))
        if tag=='a' and 'href' in a:self.anchors.append((a['href'],a.get('rel')))
        if tag=='link' and a.get('rel','').lower()=='canonical':self.canonical.append(a.get('href'))
    def handle_startendtag(self,tag,attrs):self.handle_starttag(tag,attrs)
    def handle_endtag(self,tag):
        if tag=='head':self.in_head=False

def normalize(value):
    return re.sub(r'\s*,\s*',',',re.sub(r'\s+',' ',value)).strip().lower()

def local_file(path):
    return ROOT/'docs'/path.lstrip('/')/'index.html' if path.endswith('/') else ROOT/'docs'/path.lstrip('/')

def structural_audit(manifest):
    failures=[];pages={p['url']:p for p in manifest['pages']}
    case_seeds={c['seed'] for c in manifest['cases']}
    incoming=defaultdict(list)
    tokens=set()
    for p in manifest['pages']:
        if not local_file(p['url']).is_file():failures.append('Missing generated file: '+p['url'])
        if p['marker']:
            if p['marker'] in tokens:failures.append('Duplicate unique marker: '+p['marker'])
            tokens.add(p['marker'])
        for link in p['links']:
            dest=pages.get(link['url'])
            if not dest:failures.append('Unknown graph destination: '+link['url']);continue
            incoming[link['url']].append(p['url'])
            if p['role']=='suite' and link['url'] not in case_seeds:
                failures.append('Suite exposes non-seed target: '+link['url'])
            if p['case_id'] and p['case_id']!=dest['case_id']:
                failures.append('Cross-case discovery leak: '+p['url']+' -> '+link['url'])
    for p in manifest['pages']:
        if p['role']=='target' and not incoming[p['url']]:failures.append('Unreachable target has no authored occurrence: '+p['url'])
    if list((ROOT/'docs').glob('**/sitemap*')):failures.append('Unexpected sitemap can contaminate discovery.')
    return {'kind':'Structural graph audit, not crawler execution','checked_urls':len(pages),'unique_markers':len(tokens),'failures':failures}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base_url',nargs='?',help='Published site root, including /repo/ for a project site')
    parser.add_argument('--case',action='append',dest='cases',help='Verify only this case ID; repeat as needed')
    parser.add_argument('--profile',choices=['full','github'],default='full',help='github verifies static body/meta/link content but skips custom response-header and host-root robots assertions')
    parser.add_argument('--require-repeated',action='store_true',help='Require H07 to expose two separate X-Robots-Tag field lines; use with local server')
    parser.add_argument('--timeout',type=float,default=15)
    parser.add_argument('--delay',type=float,default=0)
    parser.add_argument('--report',default=str(ROOT/'qa/fixture-verification.json'))
    parser.add_argument('--structural-only',action='store_true')
    args=parser.parse_args()
    manifest=json.loads((ROOT/'qa/expected-results.json').read_text())
    audit=structural_audit(manifest)
    report={'scope':'FIXTURE VERIFICATION ONLY - no SearchStax crawler results',
            'created_at':datetime.now(timezone.utc).isoformat(),'phase':manifest['build_phase'],
            'profile':args.profile,'user_agent':UA,'base_url':args.base_url,'structural_audit':audit,
            'checks':[],'crawler_execution':'Not run','warnings':[]}
    if not args.structural_only:
        if not args.base_url:parser.error('Provide base_url, or use --structural-only.')
        base=args.base_url.rstrip('/')+'/'
        if urlsplit(base).scheme not in ('http','https'):parser.error('Use an http:// or https:// URL.')
        chosen=set(x.upper() for x in (args.cases or []))
        unknown=chosen-{c['id'] for c in manifest['cases']}
        if unknown:parser.error('Unknown case IDs: '+', '.join(sorted(unknown)))
        pages=[p for p in manifest['pages'] if not chosen or p['case_id'] in chosen]
        for p in pages:
            item={'path':p['url'],'case_id':p['case_id'],'failures':[]}
            expected_url=urljoin(base,p['url'].lstrip('/'))
            def request(method):
                with urlopen(Request(expected_url,headers={'User-Agent':UA,'Cache-Control':'no-cache'},method=method),timeout=args.timeout) as r:
                    return r.status,r.headers,r.geturl(),r.read()
            try:
                status,headers,final,body=request('GET')
                item.update(status=status,final_url=final,actual_x_robots_tag=headers.get_all('X-Robots-Tag') or [])
                if status!=200:item['failures'].append('Expected HTTP 200; got '+str(status))
                decoded=body.decode('utf-8')
                if p['marker'] and p['marker'] not in decoded:item['failures'].append('Expected unique marker missing.')
                if p['kind']=='html':
                    actual=SourceParser();actual.feed(decoded)
                    source=SourceParser();source.feed(local_file(p['url']).read_text())
                    if actual.metas!=source.metas:item['failures'].append('Meta directives differ from the local source fixture.')
                    if actual.canonical:item['failures'].append('Unexpected canonical link may change URL identity.')
                    observed=[]
                    for href,rel in actual.anchors:
                        dest,frag=urldefrag(urljoin(final,href));observed.append((dest,rel,frag))
                    required=[(urljoin(base,l['url'].lstrip('/')),l.get('rel'),l.get('fragment','')) for l in p['links']]
                    if observed!=required:item['failures'].append('Anchor discovery graph differs from the authored fixture (including rel and fragment).')
                if args.profile=='full':
                    grouped=defaultdict(list)
                    for name,value in p['headers']:grouped[name.lower()].append(value)
                    for name in set(grouped)|{'x-robots-tag'}:
                        actual_values=headers.get_all(name) or []
                        expected_values=grouped.get(name,[])
                        if normalize(', '.join(actual_values))!=normalize(', '.join(expected_values)):
                            item['failures'].append(f'Header {name}: expected {expected_values!r}, got {actual_values!r}.')
                    head_status,head_headers,head_final,_=request('HEAD')
                    if head_status!=status or head_final!=final:item['failures'].append('HEAD status/final URL differs from GET.')
                    if normalize(', '.join(head_headers.get_all('X-Robots-Tag') or []))!=normalize(', '.join(headers.get_all('X-Robots-Tag') or [])):
                        item['failures'].append('GET/HEAD X-Robots-Tag mismatch.')
                    if args.require_repeated and p['case_id']=='H07' and p['role']=='parent' and len(headers.get_all('X-Robots-Tag') or [])!=2:
                        item['failures'].append('H07 does not contain two physical X-Robots-Tag field lines.')
                else:item['header_checks']='Skipped - GitHub Pages partial profile'
            except (HTTPError,URLError,TimeoutError,UnicodeError,OSError) as e:
                item['failures'].append(str(e))
            item['result']='FAIL' if item['failures'] else 'Fixture verified'
            report['checks'].append(item)
            if item['failures']:print('FAIL',p['url'], '; '.join(item['failures']))
            if args.delay:time.sleep(max(0,args.delay))
        if args.profile=='full':
            origin=urlsplit(base)
            robots_url=origin.scheme+'://'+origin.netloc+'/robots.txt'
            result={'path':robots_url,'kind':'Host-root robots configuration','failures':[]}
            try:
                with urlopen(Request(robots_url,headers={'User-Agent':UA}),timeout=args.timeout) as r:
                    robot_text=r.read().decode('utf-8')
                robots=RobotFileParser();robots.parse(robot_text.splitlines())
                for c in manifest['cases']:
                    if not c['robots_blocked']:continue
                    parent=urljoin(base,c['parent'].lstrip('/'))
                    if robots.can_fetch(UA,parent):result['failures'].append(c['id']+' parent is not blocked at host root.')
                    if not robots.can_fetch(UA,urljoin(base,c['seed'].lstrip('/'))):result['failures'].append(c['id']+' entry seed is unexpectedly blocked.')
                    for t in c['targets']:
                        if not robots.can_fetch(UA,urljoin(base,t['url'].lstrip('/'))):result['failures'].append(c['id']+' target is blocked and masks page-level behavior.')
            except (HTTPError,URLError,TimeoutError,UnicodeError,OSError) as e:result['failures'].append(str(e))
            report['checks'].append(result)
        else:report['warnings'].append('HTTP header and host-root robots assertions were skipped; this is not full fixture coverage.')
    failures=len(audit['failures'])+sum(len(c['failures']) for c in report['checks'])
    report['summary']={'fixture_checks':len(report['checks']),'failures':failures,'crawler_cases_executed':0}
    destination=Path(args.report);destination.parent.mkdir(parents=True,exist_ok=True);destination.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report['summary'],indent=2));print('Report:',destination)
    return 1 if failures else 0

if __name__=='__main__':sys.exit(main())
