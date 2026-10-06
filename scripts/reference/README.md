# scripts/reference/

Keeps the public site's country reference file
(`apps/public-site/reference/countries.json`) current. Public.

| Script | Role |
|---|---|
| `refresh_country_reference.py` | Researches each country's officeholders, commanders and elections with Claude and web search, and stores what it finds as a **proposal** with a source per entry. Runs nightly for countries whose events signal a change or whose entry has not been checked in 30 days |
| `review_reference.py` | The review step: `list`, `show`, `approve` or `dismiss` a proposal. Approval publishes it and records the reviewer and date |

The public page never shows a proposed value. Until an analyst decides, it keeps the
current values and marks the affected fields "Under review".

An entry that was updated automatically before the review step existed (`auto_updated`
set, `reviewed` not) is listed for **sign-off**: `review_reference.py signoff <country>
--reviewer <name>`.

**In the analyst console.** The same items appear under the *Reference* tab. The nightly
sync pushes them as the `content_review_items` snapshot (`review_items()`); an analyst's
decision is a row in the Supabase table `content_reviews`; the next sync applies it with
`scripts/sync/pull_content_reviews_from_supabase.py`, which calls the same `decide()` as
the command line and stamps the row so it is never applied twice. A decision made for one
proposal is not applied to a later one (the `item_key` must still match).

Every proposal and decision is appended to `apps/public-site/reference/changes.json`.
