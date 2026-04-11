import pytest
from fastapi.testclient import TestClient
from main import app, API_KEY

client = TestClient(app)
HEADERS = {"X-API-Key": API_KEY}

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200

def test_unauthorized_access():
    response = client.post("/api/v1/manual-entry", json={}, headers={"X-API-Key": "wrongkey"})
    assert response.status_code == 401

def test_manual_entry():
    payload = {"date": "2023-10-27", "soreness": 5, "mood": 8, "energy": 7}
    response = client.post("/api/v1/manual-entry", json=payload, headers=HEADERS)
    assert response.status_code == 200
