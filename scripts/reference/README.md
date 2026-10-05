# scripts/reference/

Keeps the public site's country reference file
(`apps/public-site/reference/countries.json`) current. Public.

| Script | Role |
|---|---|
| `refresh_country_reference.py` | Researches each country's officeholders, commanders and elections with Claude and web search, and writes sourced, dated entries. Run nightly for countries whose events signal a change or whose entry is old; see its docstring |

Every change is appended to `apps/public-site/reference/changes.json`.
