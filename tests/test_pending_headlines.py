"""The degraded path: when the model API is unavailable, collected headlines are published uncoded."""

import json
import sys
from pathlib import Path

from types import SimpleNamespace

import pytest

anthropic = pytest.importorskip("anthropic")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "publish"))
import pending_headlines  # noqa: E402


def _error(cls, status, message):
    # A stand-in for the HTTP response, so the test does not depend on the SDK's transport library.
    response = SimpleNamespace(status_code=status, headers={}, request=None)
    return cls(message, response=response, body={"error": {"message": message}})


def test_account_errors_count_as_unavailable():
    credit = "Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits."
    assert pending_headlines.is_api_unavailable(_error(anthropic.BadRequestError, 400, credit))
    assert pending_headlines.is_api_unavailable(_error(anthropic.AuthenticationError, 401, "invalid x-api-key"))
    assert pending_headlines.is_api_unavailable(_error(anthropic.PermissionDeniedError, 403, "disabled"))


def test_ordinary_errors_still_fail_the_run():
    assert not pending_headlines.is_api_unavailable(_error(anthropic.BadRequestError, 400, "messages: text content blocks must be non-empty"))
    assert not pending_headlines.is_api_unavailable(RuntimeError("All 12 coding requests failed"))
    assert not pending_headlines.is_api_unavailable(KeyError("country"))


def test_country_is_guessed_only_when_one_is_named():
    patterns = pending_headlines._country_patterns()
    assert pending_headlines.guess_country("Ejército de México despliega tropas en Sinaloa", patterns) == "Mexico"
    assert pending_headlines.guess_country("Haïti : la police reprend un quartier", patterns) == "Haiti"
    assert pending_headlines.guess_country("Colombia and Venezuela reopen border crossing", patterns) is None
    assert pending_headlines.guess_country("Regional ministers meet on drug policy", patterns) is None


def test_write_and_clear(tmp_path):
    path = tmp_path / "pending_headlines.json"
    articles = [
        {"title": "Peru declares emergency in Lima", "url": "https://a.example/1", "source": "A", "date": "2026-10-15", "description": "long text"},
        {"title": "Peru declares emergency in Lima", "url": "https://a.example/1", "source": "A", "date": "2026-10-15"},
        {"title": "No link", "url": "", "source": "B", "date": "2026-10-16"},
        {"title": "Brasil prende líder do PCC", "url": "https://b.example/2", "source": "B", "date": "2026-10-16"},
    ]
    assert pending_headlines.write_pending(articles, "BadRequestError: credit", path) == 2
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload["headlines"]
    assert [r["date"] for r in rows] == ["2026-10-16", "2026-10-15"]
    assert [r["country"] for r in rows] == ["Brazil", "Peru"]
    assert all(set(r) == {"title", "url", "source", "date", "country"} for r in rows), "no article text is republished"
    assert pending_headlines.clear_pending(path) and not path.exists()
    assert not pending_headlines.clear_pending(path)
