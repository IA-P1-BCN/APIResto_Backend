from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_cors_deja_leer_retry_after_a_la_web():
    """Sin exponerla, el navegador no deja leer `Retry-After` del 429 (HU-31) desde otro origen."""
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert "retry-after" in response.headers["access-control-expose-headers"].lower()
