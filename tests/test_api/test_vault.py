"""Tests for vault API endpoints."""
import pytest


async def _get_token(client, user_data):
    res = await client.post("/api/auth/register", json=user_data)
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_create_and_list_skills(client, test_user_data):
    token = await _get_token(client, test_user_data)
    headers = {"Authorization": f"Bearer {token}"}

    create_res = await client.post("/api/vault/skills", json={
        "name": "Python", "category": "Language", "proficiency": "expert",
    }, headers=headers)
    assert create_res.status_code == 201
    assert create_res.json()["name"] == "Python"

    list_res = await client.get("/api/vault/skills", headers=headers)
    assert list_res.status_code == 200
    assert any(s["name"] == "Python" for s in list_res.json())


@pytest.mark.asyncio
async def test_vault_health_returns_scores(client, test_user_data):
    token = await _get_token(client, test_user_data)
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.get("/api/vault/health", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "completeness_score" in data
    assert "warnings" in data
    assert 0.0 <= data["completeness_score"] <= 1.0


@pytest.mark.asyncio
async def test_update_profile(client, test_user_data):
    token = await _get_token(client, test_user_data)
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.patch("/api/vault/profile", json={
        "full_name": "Test User",
        "headline": "Senior ML Engineer",
        "summary": "10 years building production AI systems.",
    }, headers=headers)
    assert res.status_code == 200
    assert res.json()["full_name"] == "Test User"
