# scripts/reference/

Keeps the public site's country reference file
(`apps/public-site/reference/countries.json`) current. Public.

| Script | Role |
|---|---|
| `refresh_country_reference.py` | Researches each country's officeholders, commanders and elections with Claude and web search, and stores what it finds as a **proposal** with a source per entry. Runs nightly for countries whose events signal a change or whose entry has not been checked in 30 days |
| `review_reference.py` | The review step: `list`, `show`, `approve` or `dismiss` a proposal. Approval publishes it and records the reviewer and date |

The public page never shows a proposed value. Until an analyst decides, it keeps the
current values and marks the affected fields "Under review".

Every proposal and decision is appended to `apps/public-site/reference/changes.json`.
