# tests/

This is the pytest suite for the SENTINEL pipeline, prompts, and public data contract.
It is public.

```bash
python3 -m pytest            # from the repo root (Python 3.11+, requirements-ci.txt + pytest)
```

`conftest.py` puts `scripts/` and its subdirectories on `sys.path`. That way, tests
import the scripts the same way they import each other at runtime.

| File | Guards |
|---|---|
| `test_prompt_library.py` | `prompts/manifest.json` ↔ prompt files; strict placeholder rendering |
| `test_pipeline_core.py` | Per-incident `stable_id`, citable IDs, geolocation, pre-filter recall |
| `test_normalize_articles.py` | Article IDs, domain inference, NewsAPI source allowlist |
| `test_taxonomy.py` | Taxonomy completeness; every classifier type exists in the taxonomy |
| `test_published_contract.py` | `data/published/events_public.json`: field allowlist, no private fields, publish policy |
| `test_historical_ingest.py` | Historical runner: monthly units, coverage floors, resume, retry-empty, archive QA |
| `test_build_gold_layer.py` | Gold layer: eligibility thresholds, field-level corrections, decision extraction |

The tests make no network or API calls. CI runs them via `.github/workflows/tests.yml`
on every push that touches code.
