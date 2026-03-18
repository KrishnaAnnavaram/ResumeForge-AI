"""Tests for auth API endpoints."""
import pytest


@pytest.mark.asyncio
async def test_register_user(client, test_user_data):
    response = await client.post("/api/auth/register", json=test_user_data)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["email"] == test_user_data["email"]


@pytest.mark.asyncio
async def test_login_user(client, test_user_data):
    # Register first
    await client.post("/api/auth/register", json=test_user_data)
    # Login
    response = await client.post("/api/auth/login", json={
        "email": test_user_data["email"],
        "password": test_user_data["password"],
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client, test_user_data):
    await client.post("/api/auth/register", json=test_user_data)
    response = await client.post("/api/auth/login", json={
        "email": test_user_data["email"],
        "password": "wrongpassword",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_duplicate_register(client, test_user_data):
    await client.post("/api/auth/register", json=test_user_data)
    response = await client.post("/api/auth/register", json=test_user_data)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_get_me(client, test_user_data):
    reg = await client.post("/api/auth/register", json=test_user_data)
    token = reg.json()["access_token"]
    response = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == test_user_data["email"]


@pytest.mark.asyncio
async def test_unauthorized_access(client):
    response = await client.get("/api/auth/me", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401
