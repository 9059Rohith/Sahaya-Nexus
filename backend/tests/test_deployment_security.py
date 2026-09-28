import hashlib
import hmac
import time

import pytest
from fastapi import Request
from pydantic import ValidationError

from app.config import Settings, settings
from app.services.rate_limit import (
    InvalidProxyIdentity,
    permitted,
    signed_client_address,
)


def request_with_identity(address: str, stamp: str, signature: str) -> Request:
    headers = [
        (b"x-sahaya-client-address", address.encode()),
        (b"x-sahaya-client-time", stamp.encode()),
        (b"x-sahaya-client-signature", signature.encode()),
    ]
    return Request({"type": "http", "method": "POST", "path": "/api/v1/auth/login", "query_string": b"", "headers": headers, "client": ("172.18.0.4", 5000), "server": ("api", 8000), "scheme": "http"})


def test_signed_proxy_address_rejects_forgery_and_replay(monkeypatch):
    secret = "test-only-unique-shared-proxy-secret-32"
    monkeypatch.setattr(settings, "bff_shared_secret", secret)
    stamp = str(int(time.time()))
    address = "203.0.113.20"
    signature = hmac.new(secret.encode(), f"{stamp}:{address}".encode(), hashlib.sha256).hexdigest()
    assert signed_client_address(request_with_identity(address, stamp, signature)) == address
    assert signed_client_address(request_with_identity("203.0.113.21", stamp, signature)) is None
    assert signed_client_address(request_with_identity(address, str(int(stamp) - 31), signature)) is None
    assert signed_client_address(request_with_identity("not-an-ip", stamp, signature)) is None
    with pytest.raises(InvalidProxyIdentity):
        permitted(request_with_identity(address, stamp, "forged"))


def test_production_rejects_default_secret_and_sqlite():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_mode="production", secret_key="local-development-only-change-before-deployment", database_url="postgresql+psycopg://u:p@db/sahaya")
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_mode="production", secret_key="a-unique-production-secret-more-than-32-chars", database_url="sqlite:///./sahaya.db")
