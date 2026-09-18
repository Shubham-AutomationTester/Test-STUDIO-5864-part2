# STUDIO-5864 - Page-level robots QA plan

## Objective and release risk

Verify that SearchStax independently controls page processing, index add/update and link enqueueing using HTML robots meta, supported bot-specific meta, response X-Robots-Tag and link-level rel=nofollow. The existing Ignore robots.txt setting must bypass only host-level robots.txt restrictions.

The highest risks are prohibited documents being indexed, nofollow targets entering the queue, permitted children being lost under noindex, unrelated bot tags restricting SearchStax, and generic/specific precedence behaving differently by tag order. Lifecycle tests additionally protect against prohibited updates and treating nofollow as a global target blacklist.

## Acceptance authority and coverage

Source: https://searchstax.atlassian.net/browse/STUDIO-5864 (retrieved September 19, 2026). No comments added clarification when the ticket was read.

| Area | IDs | Scope |
|---|---|---|
| HTML meta | M01-M22 | Controls; independent/combined directives; case and separators; repeated tokens; empty/missing values; exact token matching; comments; body-only tag; fake HTTP meta; aggregation/conflicts/alias decisions |
| Bot targeting | B01-B11 | Ignore unrelated bots; preserve generic constraints; confirmed-token match; case; explicit precedence in both tag orders; partial-dimension and token-boundary questions |
| HTTP response | H01-H14 | Header-only directives; case/whitespace; repeated physical fields; text extraction control pair; header/meta interaction; scoped headers; misspelled field |
| Link rules | L01-L15 | Per-occurrence suppression; rel case/whitespace; multiple values; empty/irrelevant tokens; duplicate URLs in both orders; alternate paths; page-vs-link restrictions; fragments; comma non-token |
| robots.txt switch | R01-R06 | Allowed discovery seed -> blocked parent -> otherwise allowed children; OFF/ON combinations for page/header/link restrictions |
| Lifecycle | U01-U04 | Same-URL index V1 -> restricted V2 -> restored V3; newly introduced nofollow targets; preserved existing index state |

Readiness is explicit: **51 Ready, 7 Conditional, 10 Confirm, 4 Lifecycle**. Ready means the expected behavior is defined; it does not mean the test is executed or its hosting preconditions are satisfied. Conditional and lifecycle tests are not silently counted as product passes.

## Test environment and entry criteria

Use a dedicated non-production app/index. Record environment, app/tenant identifiers where available, crawler build/version, crawl-definition ID, run ID, UTC start/end time, settings and actual HTTP User-Agent. Confirm the supported robots meta-name token with engineering; the shipped `searchstax` value is a placeholder.

Deploy at a host that provides the response headers required by the selected case. Verify the final GET status, headers, original head/body markup, source graph and root robots file. A rendered browser DOM can repair malformed/body metadata; it is not the sole source-of-truth artifact for placement tests.

Use one selected suite or case seed. Include all intended case and suite paths; depth >= 5 and item budget >= 500. Ensure URL filters, content-type restrictions, redirects, canonicalization, authentication, scheduling, stale-document cleanup, robots caching and earlier crawl queues do not mask the assertion. Disable sitemap/independent URL discovery and finish previous runs before resetting state.

For independent runs, clear the test index and reset the crawl frontier through supported product controls or use a fresh dedicated app/definition. Do not clear an unrelated app. For U01-U04, retain the baseline indexed documents and use forced re-fetching between phases.

## Execution strategy

### A. Fixture gate

Run `tools/verify.py` against the published base. Save the output and live GET response. Resolve header, missing-file, root-robots and graph errors before assessing the product. Separate verifier and human browser requests from actual crawler activity by user-agent and time window.

No mock crawler result is supplied. The fixture audit confirms only that the controlled input exists. A physical repeated-header test is not fulfilled by a CDN-coalesced value.

### B. Product smoke, then regression

Start with M01, M03, M04, M05, B01, H01, H02, H03, L01, L08, L10, R01, R04 and R06. Execute the remaining defined-expectation cases after smoke is stable. Repeat allowed-page suites with Ignore robots.txt OFF and ON: the page/header/link outcomes must be unchanged.

For R01-R06, use fresh state per toggle. The seed page is allowed in both runs. OFF must prevent processing of the blocked parent, so directives on that parent cannot be observed by the crawler. ON must permit fetching that parent but still enforce applicable page-level and occurrence-level restrictions.

For B05-B08 and B10-B11, resolve the supported token first. For H08, establish that the identical positive .txt control is extractable and indexed. A negative .txt that is absent because all .txt extraction is disabled is not proof that noindex works.

### C. Lifecycle and resilience

For each U-case: build/deploy baseline; crawl and capture V1/old-child; build/deploy restricted; inspect the live response and force-crawl the same URL; build/deploy restored; inspect/crawl again and verify recovery. Preserve the intended prior index state. U02 explicitly replaces restricted HTTP directives with neutral index,follow on restoration so omitted-host-rule persistence cannot falsify the result.

Repeat a stable crawl once to check consistent decisions and one unique document per normalized URL. Physical HTTP request count may exceed one because of retries, validation or transport behavior; do not equate that with duplicate indexing. In alternate-path cases, a permitted occurrence may schedule a target even if another occurrence is nofollow.

### D. Product decisions

Keep these cases exploratory/Blocked until decisions are documented in Jira:

| Cases | Required decision |
|---|---|
| M20 | How multiple generic meta tags aggregate |
| M21 | Conflicting positive/negative tokens in one tag |
| M22 | Whether the none alias is supported in this ticket |
| B09 | Whole-tag replacement versus per-dimension specific precedence |
| H07 | How repeated X-Robots-Tag fields aggregate |
| H09 | How compatible meta/header restrictions combine |
| H10-H11 | Precedence when response headers and HTML meta conflict |
| H12-H13 | Whether bot-scoped HTTP header syntax is supported |

Additional prerequisites/decisions: exact supported bot-name mapping; retention versus deletion of already indexed documents when noindex is introduced; supported document types; and meaningful customer-visible outcomes/logging where not specified. Do not invent issue codes, status names or deletion requirements.

## Minimum assertion model

| Input | Parent fetched/processed | Parent can add/update | Child eligible from this occurrence |
|---|---|---|---|
| No restriction | Yes | Yes | Yes |
| noindex | Yes | No | Yes |
| nofollow | Yes | Yes | No |
| noindex,nofollow | Yes | No | No |
| One link rel=nofollow | Yes | Yes | No for that link only |
| robots-disallowed parent; Ignore OFF | No | No new content from this run | No discovery from that parent |
| robots-disallowed parent; Ignore ON | Yes | Determined by applicable page directives | Determined by page and individual link directives |

These results assume no other blocking configuration and a clean run for the first five rows. An existing target can remain indexed despite new nofollow, and another permitted occurrence can independently queue it. For noindex lifecycle cases, assert V2 was not added or used to update the document; inspect legacy retention/removal separately.

## Evidence and defect standard

For each case, capture the exact parent and target URLs, unique markers, source directives, live HTTP headers, active robots setting, actual user-agent, timestamps and product run identifiers. In pipeline logs, distinguish validation/HEAD checks, successful content fetch, parsing, link discovery, enqueue, filtering, index add/update and deletion. Use the product's actual event names/codes, not expected names invented for this plan.

For nofollow, index absence alone is insufficient: a target might be fetched and then fail parsing. Use queue provenance or URL-level pipeline outcomes to demonstrate no enqueue from the restricted source. For noindex, search preview alone is insufficient: inspect the underlying indexed document/version and processing evidence, accounting for ingestion delays.

In Datadog, narrow by the identifiers and time window available in your environment, then confirm field names and event types from actual records. The fixture server's `qa.fixture.request` is only an access-log event and is not a SearchStax `operational.outcome.recorded` event.

A defect should include: case ID; expected versus actual behavior; precondition verification; minimal seed; source/header evidence; run IDs; exact indexed marker/document URL; affected occurrence and alternate-path exclusions; reproducibility; and customer impact. Separate an invalid fixture or unresolved contract from a product failure.

## Exit criteria

All applicable defined-expectation cases pass on the release-candidate build with traceable evidence; both robots toggle states are covered; confirmed-token cases pass or have an explicitly approved scope decision; lifecycle restrictions and recovery are verified; high-risk failures are resolved/retested; unresolved cases have a recorded owner and disposition; and the known hosting/parser limitations are disclosed.

Do not report an aggregate success rate that counts Conditional, Confirm, Lifecycle or Not run cases as Passed. Export the dashboard's manually entered run evidence and preserve the actual backend evidence separately. A successful local fixture-verification report is not product sign-off.

## Sources for fixture mechanics

- Render HTTP headers: https://render.com/docs/static-site-headers
- Render Blueprint preservation behavior: https://render.com/docs/blueprint-spec
- Netlify response-header rules: https://docs.netlify.com/manage/routing/headers/
- HTML rel whitespace/case semantics: https://html.spec.whatwg.org/multipage/links.html
- Robots background (Google behavior, not the SearchStax acceptance contract): https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag
