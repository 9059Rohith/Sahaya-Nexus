import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ops"))
from preflight import check  # noqa: E402


def test_production_preflight_rejects_placeholders_and_shared_secrets():
    invalid = {
        "POSTGRES_PASSWORD": "replace-with-32-or-more-url-safe-random-characters",
        "SECRET_KEY": "a" * 40,
        "BFF_SHARED_SECRET": "a" * 40,
        "SAHAYA_DOMAIN": "help.example.org",
        "TLS_EMAIL": "operator@example.org",
    }
    assert len(check(invalid)) >= 4


def test_production_preflight_accepts_distinct_values():
    valid = {
        "POSTGRES_PASSWORD": "a" * 40,
        "SECRET_KEY": "b" * 40,
        "BFF_SHARED_SECRET": "c" * 40,
        "SAHAYA_DOMAIN": "help.sahaya.org",
        "TLS_EMAIL": "owner@sahaya.org",
    }
    assert check(valid) == []


def test_production_preflight_rejects_reserved_and_malformed_hosts():
    valid = {
        "POSTGRES_PASSWORD": "a" * 40,
        "SECRET_KEY": "b" * 40,
        "BFF_SHARED_SECRET": "c" * 40,
        "SAHAYA_DOMAIN": "help.sahaya.org",
        "TLS_EMAIL": "owner@sahaya.org",
    }
    for domain in ("help.sahaya.test", "help.example.org", "-bad.sahaya.org", "localhost"):
        assert any("SAHAYA_DOMAIN" in error for error in check({**valid, "SAHAYA_DOMAIN": domain}))
    for email in ("owner@example.org", "owner@invalid.test", "owner@-bad.org"):
        assert any("TLS_EMAIL" in error for error in check({**valid, "TLS_EMAIL": email}))
