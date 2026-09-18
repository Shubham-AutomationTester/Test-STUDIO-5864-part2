"""Declarative, isolated crawl fixtures for STUDIO-5864. Python stdlib only."""
from html import escape

TICKET = 'https://searchstax.atlassian.net/browse/STUDIO-5864'

def make_cases(config):
    cases = []
    bot = config['bot_meta_name']
    def add(cid, title, group, *, meta=None, head='', body='', headers=None,
            index=True, follow=True, gate='Ready', note='', requires=None,
            targets=None, links=None, priority='High', blocked=False):
        root = '/cases/' + cid.lower() + '/'
        parent = root + ('blocked/' if blocked else '')
        if targets is None:
            targets = [{'slug': 'child', 'fetch': follow, 'index': follow}]
        # Targets are never shared between cases. Special graphs remain inside one case.
        ts = []
        for target in targets:
            t = dict(target)
            t['url'] = root + t['slug'] + ('/' if t.get('type', 'html') == 'html' else '.txt')
            t.setdefault('fetch', True)
            t.setdefault('index', t['fetch'])
            t.setdefault('headers', [])
            ts.append(t)
        if links is None:
            links = [{'target': t['slug'], 'rel': t.get('rel')} for t in ts]
        raw_head = '\n'.join('<meta name="{}" content="{}">'.format(escape(n, quote=True), escape(v, quote=True)) for n,v in (meta or []))
        if head:
            raw_head += ('\n' if raw_head else '') + head
        req = list(requires or [])
        if headers and 'headers' not in req:
            req.append('headers')
        c = dict(id=cid, title=title, group=group, root=root, seed=root, parent=parent,
                 raw_head=raw_head, raw_body=body, headers=headers or [],
                 index=index, follow=follow, gate=gate, note=note, requires=req,
                 targets=ts, links=links, priority=priority, robots_blocked=blocked,
                 source=TICKET, phase=config['phase'])
        cases.append(c)
        return c

    # Generic meta: exact tokens, location, formatting and independent behavior.
    add('M01', 'Control: no robots directives', 'HTML meta')
    add('M02', 'Explicit index and follow', 'HTML meta', meta=[('robots','index, follow')])
    add('M03', 'noindex still discovers the child', 'HTML meta', meta=[('robots','noindex')], index=False)
    add('M04', 'nofollow still indexes the parent', 'HTML meta', meta=[('robots','nofollow')], follow=False)
    add('M05', 'Combined tokens: no spaces', 'HTML meta', meta=[('robots','noindex,nofollow')], index=False, follow=False)
    add('M06', 'Combined tokens: uppercase', 'HTML meta', meta=[('robots','NOINDEX, NOFOLLOW')], index=False, follow=False)
    add('M07', 'Combined tokens: comma and space', 'HTML meta', meta=[('robots','noindex, nofollow')], index=False, follow=False)
    add('M08', 'Whitespace-separated tokens', 'HTML meta', meta=[('robots','noindex nofollow')], index=False, follow=False)
    add('M09', 'Tabs, newlines and extra whitespace', 'HTML meta', meta=[('robots','  noindex\t\n nofollow  ')], index=False, follow=False)
    add('M10', 'Mixed-case tag, name and attributes', 'HTML meta', head='<META CONTENT="NoInDeX, NoFoLlOw" NAME="RoBoTs">', index=False, follow=False)
    add('M11', 'Empty separators surrounding valid tokens', 'HTML meta', meta=[('robots',', noindex,, nofollow, ')], index=False, follow=False,
        note='Robustness expectation: empty comma-separated tokens have no meaning; valid tokens must still apply.')
    add('M12', 'Repeated identical directives', 'HTML meta', meta=[('robots','noindex noindex, nofollow nofollow')], index=False, follow=False)
    add('M13', 'Unknown token beside valid noindex', 'HTML meta', meta=[('robots','qa-unknown, noindex')], index=False,
        note='Unknown token must not cause valid noindex to be discarded or the crawl to fail.')
    add('M14', 'Empty robots content', 'HTML meta', meta=[('robots','')], priority='Medium')
    add('M15', 'Missing content attribute', 'HTML meta', head='<meta name="robots">', priority='Medium',
        note='Malformed-input robustness: no crash, and no unsupported restriction should be invented.')
    add('M16', 'Directive substrings are not tokens', 'HTML meta', meta=[('robots','xnoindex nofollowish noindex=false')],
        note='Exact token matching only. These strings are not noindex or nofollow.')
    add('M17', 'Robots tag inside an HTML comment', 'HTML meta', head='<!-- <meta name="robots" content="noindex, nofollow"> -->',
        note='A commented-out tag is not an active head element.')
    add('M18', 'Robots meta in body, not head', 'HTML meta', body='<meta name="robots" content="noindex, nofollow">',
        note='Ticket-specific head-only expectation. This is not a claim about Google, which may honor body tags. Verify against raw response HTML, not a repaired browser DOM.')
    add('M19', 'http-equiv is not a real HTTP header', 'HTML meta', head='<meta http-equiv="X-Robots-Tag" content="noindex, nofollow">',
        note='No response X-Robots-Tag exists. This is neither a name=robots tag nor the HTTP-header feature in the ticket.')
    add('M20', 'Separate generic meta tags', 'HTML meta', meta=[('robots','noindex'),('robots','nofollow')], index=None, follow=None, gate='Confirm',
        note='Ticket does not specify aggregation across multiple tags. Proposed decision: combine restrictions to noindex + nofollow. Do not report a defect until agreed.')
    add('M21', 'Conflicting directives in one meta tag', 'HTML meta', meta=[('robots','index,noindex,follow,nofollow')], index=None, follow=None, gate='Confirm',
        note='Conflict precedence is not defined in the ticket. Proposed decision: restrictive wins; confirm before pass/fail.')
    add('M22', 'The none shorthand is outside explicit scope', 'HTML meta', meta=[('robots','none')], index=None, follow=None, gate='Confirm', priority='Medium',
        note='Ask whether none (a common alias for noindex,nofollow) is supported. The ticket only requires noindex and nofollow.')

    # A placeholder token is never silently treated as a confirmed SearchStax name.
    add('B01', 'googlebot-only directives must not apply', 'Bot targeting', meta=[('googlebot','noindex,nofollow')],
        note='Run with a confirmed non-Googlebot SearchStax crawler identity.')
    add('B02', 'bingbot-only directives must not apply', 'Bot targeting', meta=[('bingbot','noindex,nofollow')])
    add('B03', 'An unrelated bot name is ignored', 'Bot targeting', meta=[('unrelated-qa-bot','noindex,nofollow')])
    add('B04', 'Generic noindex survives unrelated bot allow', 'Bot targeting', meta=[('robots','noindex'),('googlebot','index,follow')], index=False)
    add('B05', 'Matching configured bot: noindex', 'Bot targeting', meta=[(bot,'noindex')], index=False, gate='Conditional', requires=['bot-token'],
        note='Applies only after the exact supported meta-name mapping is confirmed; current token is configurable.')
    add('B06', 'Matching bot name and directive case', 'Bot targeting', meta=[(bot.upper(),'NoFoLlOw')], follow=False, gate='Conditional', requires=['bot-token'])
    add('B07', 'Specific allow overrides generic block', 'Bot targeting', meta=[('robots','noindex,nofollow'),(bot,'index,follow')], gate='Conditional', requires=['bot-token'],
        note='Expected per this ticket: the supported specific tag takes precedence. Do not substitute Google-style restriction merging.')
    add('B08', 'Specific precedence is independent of tag order', 'Bot targeting', meta=[(bot,'index,follow'),('robots','noindex,nofollow')], gate='Conditional', requires=['bot-token'])
    add('B09', 'Specific tag specifies only one dimension', 'Bot targeting', meta=[('robots','noindex,nofollow'),(bot,'index')], index=None, follow=None, gate='Confirm', requires=['bot-token'],
        note='Clarify whole-tag replacement versus per-directive override. With specific index, should the generic nofollow remain?')
    add('B10', 'Partial bot-name match is not enough', 'Bot targeting', meta=[(bot+'-lookalike','noindex,nofollow')], gate='Conditional', requires=['bot-token'],
        note='Verify supported name mapping, not a substring of the HTTP User-Agent. This lookalike must not match unless explicitly registered.')
    add('B11', 'Specific block overrides generic allow', 'Bot targeting', meta=[('robots','index,follow'),(bot,'noindex,nofollow')], index=False, follow=False, gate='Conditional', requires=['bot-token'])

    # Header fixtures use host rules; content never pretends to be an HTTP response.
    add('H01', 'Header-only noindex', 'HTTP headers', headers=[['X-Robots-Tag','noindex']], index=False)
    add('H02', 'Header-only nofollow', 'HTTP headers', headers=[['X-Robots-Tag','nofollow']], follow=False)
    add('H03', 'Header-only noindex and nofollow', 'HTTP headers', headers=[['X-Robots-Tag','noindex, nofollow']], index=False, follow=False)
    add('H04', 'Uppercase header directives', 'HTTP headers', headers=[['X-Robots-Tag','NOINDEX, NOFOLLOW']], index=False, follow=False)
    add('H05', 'Whitespace-separated header directives', 'HTTP headers', headers=[['X-Robots-Tag','noindex nofollow']], index=False, follow=False)
    add('H06', 'Mixed-case HTTP field name', 'HTTP headers', headers=[['x-RoBoTs-TaG','noindex']], index=False,
        note='A CDN may normalize field-name case. The local server preserves this wire casing; behavior must remain case-insensitive.')
    add('H07', 'Repeated X-Robots-Tag field lines', 'HTTP headers', headers=[['X-Robots-Tag','noindex'],['X-Robots-Tag','nofollow']], index=None, follow=None, gate='Confirm', requires=['raw-duplicate-headers'],
        note='Clarify aggregation. Local server emits two physical field lines. Static CDNs may combine them; verify raw GET response before claiming the repeated-field variant was tested.')
    add('H08', 'Text document: restricted and allowed controls', 'HTTP headers', requires=['headers','text-parser'], gate='Conditional',
        targets=[{'slug':'allowed','type':'text','fetch':True,'index':True},
                 {'slug':'restricted','type':'text','fetch':True,'index':False,'headers':[['X-Robots-Tag','noindex']]}],
        note='The parent has no restriction. Both text URLs are fetchable. Restricted text must not index, while allowed text must index. Establish .txt support first; otherwise mark Blocked, not Passed.')
    add('H09', 'Header noindex plus meta nofollow', 'HTTP headers', meta=[('robots','nofollow')], headers=[['X-Robots-Tag','noindex']], index=None, follow=None, gate='Confirm',
        note='Cross-source merge behavior is not explicit. Proposed: apply both independent restrictions; obtain product confirmation.')
    add('H10', 'Header block versus meta allow', 'HTTP headers', meta=[('robots','index,follow')], headers=[['X-Robots-Tag','noindex,nofollow']], index=None, follow=None, gate='Confirm',
        note='Header-versus-meta conflict precedence requires a decision.')
    add('H11', 'Meta block versus header allow', 'HTTP headers', meta=[('robots','noindex,nofollow')], headers=[['X-Robots-Tag','index,follow']], index=None, follow=None, gate='Confirm',
        note='Reverse of H10; confirm the same deterministic conflict policy.')
    add('H12', 'Bot-scoped header for googlebot', 'HTTP headers', headers=[['X-Robots-Tag','googlebot: noindex,nofollow']], index=None, follow=None, gate='Confirm',
        note='Bot-scoped HTTP header syntax is not explicitly promised by this ticket. Proposed: ignore this scope for a non-Googlebot crawler.')
    add('H13', 'Bot-scoped header for configured bot', 'HTTP headers', headers=[['X-Robots-Tag',bot+': noindex,nofollow']], index=None, follow=None, gate='Confirm', requires=['bot-token'],
        note='Confirm support for bot-scoped HTTP headers and exact token mapping before grading.')
    add('H14', 'Misspelled response header is not X-Robots-Tag', 'HTTP headers', headers=[['X-Robots-Tags','noindex,nofollow']],
        note='Exact field-name match is required; the pluralized custom field does not impose page restrictions.')

    def linked(cid, title, *, rel='nofollow', headmeta=None, index=True, follow=True, note='', links=None, targets=None):
        if targets is None:
            targets=[{'slug':'restricted','fetch':False,'index':False}, {'slug':'allowed','fetch':True,'index':True}]
        if links is None:
            links=[{'target':'restricted','rel':rel}, {'target':'allowed'}]
        return add(cid, title, 'Link rules', meta=headmeta, index=index, follow=follow, targets=targets, links=links, note=note)
    linked('L01','One nofollow link and one normal link')
    linked('L02','Uppercase rel=NOFOLLOW',rel='NOFOLLOW')
    linked('L03','Multiple rel tokens: external nofollow',rel='external nofollow')
    linked('L04','Mixed case, tabs and newlines in rel',rel='external\tNoFoLlOw\nnoopener')
    linked('L05','nofollowish is not a nofollow token',rel='nofollowish', targets=[{'slug':'restricted','fetch':True,'index':True},{'slug':'allowed','fetch':True,'index':True}],
           note='Target slug says restricted for fixture consistency, but this occurrence must be eligible.')
    linked('L06','Unrelated rel values stay followable',rel='noopener noreferrer', targets=[{'slug':'restricted','fetch':True,'index':True},{'slug':'allowed','fetch':True,'index':True}])
    linked('L07','Empty rel and missing rel',rel='', targets=[{'slug':'restricted','fetch':True,'index':True},{'slug':'allowed','fetch':True,'index':True}])
    linked('L08','Same URL: nofollow occurrence comes first',targets=[{'slug':'shared','fetch':True,'index':True}],
           links=[{'target':'shared','rel':'nofollow'},{'target':'shared'}],
           note='The permitted occurrence can enqueue the URL. Assert one unique indexed URL, not exactly one physical request: retries are possible.')
    linked('L09','Same URL: permitted occurrence comes first',targets=[{'slug':'shared','fetch':True,'index':True}],
           links=[{'target':'shared'},{'target':'shared','rel':'nofollow'}],
           note='A later nofollow occurrence must not remove a URL legitimately queued from the earlier occurrence.')
    c=linked('L10','Alternate permitted path reaches the same target', targets=[{'slug':'shared','fetch':True,'index':True},{'slug':'bridge','fetch':True,'index':True}],
             links=[{'target':'shared','rel':'nofollow'},{'target':'bridge'}],
             note='Graph: parent -nofollow-> shared; parent -> bridge -> shared. The bridge makes shared eligible.')
    c['target_links']={'bridge':[{'target':'shared'}]}
    c=add('L11','Page nofollow is not a global URL blacklist','Link rules',
          targets=[{'slug':'blocked-source','fetch':True,'index':True,'meta':[['robots','nofollow']]},
                   {'slug':'allowed-source','fetch':True,'index':True}, {'slug':'shared','fetch':True,'index':True}],
          links=[{'target':'blocked-source'},{'target':'allowed-source'}],
          note='Seed links to both source pages. Both source pages link to shared; the allowed source can enqueue it. This also detects state leaking from one page to another.')
    c['target_links']={'blocked-source':[{'target':'shared'}], 'allowed-source':[{'target':'shared'}]}
    linked('L12','noindex parent with mixed link-level rules',headmeta=[('robots','noindex')],index=False)
    linked('L13','Page nofollow overrides an unrestricted link',headmeta=[('robots','nofollow')],follow=False,
           targets=[{'slug':'restricted','fetch':False,'index':False},{'slug':'allowed','fetch':False,'index':False}],
           links=[{'target':'restricted','rel':'follow'},{'target':'allowed'}],
           note='rel=follow does not cancel page-level nofollow; neither occurrence may enqueue a child.')
    linked('L14','Multiple fragment occurrences are all nofollow',targets=[{'slug':'shared','fetch':False,'index':False}],
           links=[{'target':'shared','rel':'nofollow','fragment':'first'},{'target':'shared','rel':'nofollow','fragment':'second'}],
           note='Fragments do not create an unrestricted occurrence. Do not seed shared directly.')
    linked('L15','Comma is not a rel-token separator',rel='nofollow,external',
           targets=[{'slug':'restricted','fetch':True,'index':True},{'slug':'allowed','fetch':True,'index':True}],
           note='HTML rel is a whitespace-separated token list, unlike comma-or-whitespace robots content. Here the sole token is nofollow,external, not nofollow.')

    # Every blocked parent has an allowed entry and allowed-path children.
    # This prevents robots.txt from accidentally masking a follow decision on a child.
    for cid,title,meta,index,follow in [
        ('R01','robots.txt block with no page directive',[],True,True),
        ('R02','robots.txt block plus noindex',[('robots','noindex')],False,True),
        ('R03','robots.txt block plus nofollow',[('robots','nofollow')],True,False),
        ('R04','robots.txt block plus both directives',[('robots','noindex,nofollow')],False,False),
    ]:
        add(cid,title,'robots.txt switch',meta=meta,index=index,follow=follow,blocked=True,
            requires=['host-root-robots'],note='Run in two fresh crawls. Ignore robots.txt OFF: blocked parent is not fetched and no child is discovered from it. ON: fetch parent, then apply the page directives shown here. Seed is the allowed case entry, not the blocked page.')
    add('R05','robots.txt ignore does not bypass link nofollow','robots.txt switch',blocked=True,
        targets=[{'slug':'restricted','fetch':False,'index':False},{'slug':'allowed','fetch':True,'index':True}],
        links=[{'target':'restricted','rel':'nofollow'},{'target':'allowed'}],requires=['host-root-robots'],
        note='OFF: blocked parent is not fetched. ON: parent indexes; only its normal link may enqueue a child. Child paths themselves are allowed by robots.txt.')
    add('R06','robots.txt ignore does not bypass response headers','robots.txt switch',blocked=True,
        headers=[['X-Robots-Tag','noindex,nofollow']],index=False,follow=False,requires=['host-root-robots'],
        note='OFF: blocked parent is not fetched. ON: parent is fetched but not indexed, and neither links nor children are queued from it.')

    # Same URL across builds: do not confuse a second URL with an update test.
    phase=config['phase']
    blocked_phase=phase=='restricted'
    for cid,title,is_header in [('U01','Existing document: add/remove meta noindex',False),('U02','Existing document: add/remove header noindex',True)]:
        add(cid,title,'Lifecycle',meta=[('robots','noindex')] if blocked_phase and not is_header else [],
            headers=[['X-Robots-Tag','noindex' if blocked_phase else 'index,follow']] if is_header else [],
            index=None if blocked_phase else True,gate='Lifecycle',requires=['headers'] if is_header else [],
            note='Same parent URL in baseline V1, restricted V2, restored V3. Seed V1 first. Under noindex, V2 must not be added or update the existing document. Whether V1 is retained or removed is an open product decision; do not assert deletion. Restore directives and verify V3 indexes. Use a forced/full re-fetch; record any independent stale-document cleanup policy.')
    add('U03','Add page nofollow before introducing a new child','Lifecycle',
        meta=[('robots','nofollow')] if blocked_phase else [],follow=not blocked_phase,gate='Lifecycle',
        targets=[{'slug':'old-child','fetch':not blocked_phase,'index':not blocked_phase}]+([] if phase=='baseline' else [{'slug':'new-child','fetch':not blocked_phase,'index':not blocked_phase}]),
        note='Baseline links only old-child. Restricted V2 introduces new-child while setting page nofollow: new-child must not be queued. Old-child may already exist; do not use its presence as failure evidence. Restored V3 removes nofollow and permits both children.')
    add('U04','Add link nofollow before introducing a new child','Lifecycle',gate='Lifecycle',
        targets=[{'slug':'old-child','fetch':True,'index':True}]+([] if phase=='baseline' else [{'slug':'new-child','fetch':not blocked_phase,'index':not blocked_phase}]),
        links=[{'target':'old-child'}]+([] if phase=='baseline' else [{'target':'new-child','rel':'nofollow' if blocked_phase else None}]),
        note='Baseline exposes old-child only. Restricted V2 exposes new-child only through a nofollow link: old-child remains eligible, new-child must not be queued. Restored V3 removes the new-child rel restriction.')
    return cases
