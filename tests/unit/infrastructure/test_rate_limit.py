"""Rate limit должен отвечать 429, а не падать с исключением."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.interfaces.api.middlewares import rate_limit
from app.interfaces.api.middlewares.rate_limit import RateLimitMiddleware


class FakeCache:
    def __init__(self, *args, **kwargs):
        self.counts = {}

    async def incr(self, key, ttl):
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]


def make_client(monkeypatch, limit):
    monkeypatch.setattr(rate_limit, "RedisCache", FakeCache)
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, limit=limit, window=60)

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    return TestClient(app)


def test_requests_under_limit_pass_with_headers(monkeypatch):
    client = make_client(monkeypatch, limit=2)
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.headers["X-RateLimit-Remaining"] == "1"


def test_request_over_limit_returns_429(monkeypatch):
    client = make_client(monkeypatch, limit=1)
    client.get("/ping")
    response = client.get("/ping")
    assert response.status_code == 429
    assert response.json() == {"detail": "Rate limit exceeded"}
    assert response.headers["Retry-After"] == "60"


def test_limit_is_per_client_ip(monkeypatch):
    client = make_client(monkeypatch, limit=1)
    assert client.get("/ping", headers={"X-Real-IP": "1.1.1.1"}).status_code == 200
    assert client.get("/ping", headers={"X-Real-IP": "2.2.2.2"}).status_code == 200
    assert client.get("/ping", headers={"X-Real-IP": "1.1.1.1"}).status_code == 429


def test_spoofed_x_forwarded_for_does_not_bypass_limit(monkeypatch):
    """nginx лишь дописывает к X-Forwarded-For, первое значение шлёт клиент — доверять нельзя."""
    client = make_client(monkeypatch, limit=1)
    real = {"X-Real-IP": "9.9.9.9"}
    assert client.get("/ping", headers={**real, "X-Forwarded-For": "1.1.1.1"}).status_code == 200
    assert client.get("/ping", headers={**real, "X-Forwarded-For": "2.2.2.2"}).status_code == 429
