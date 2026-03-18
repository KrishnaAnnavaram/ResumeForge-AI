"""Tests for application tracker — status updates and event log."""
import pytest
from datetime import date


async def _get_token(client, user_data):
    res = await client.post("/api/auth/register", json=user_data)
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_create_application(client, test_user_data):
    token = await _get_token(client, test_user_data)
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post("/api/tracker/applications", json={
        "company": "Acme Corp",
        "role_title": "Senior ML Engineer",
        "applied_date": str(date.today()),
    }, headers=headers)

    assert response.status_code == 201
    data = response.json()
    assert data["company"] == "Acme Corp"
    assert data["status"] == "applied"


@pytest.mark.asyncio
async def test_status_update_creates_event(client, test_user_data):
    token = await _get_token(client, test_user_data)
    headers = {"Authorization": f"Bearer {token}"}

    create_res = await client.post("/api/tracker/applications", json={
        "company": "Acme Corp",
        "role_title": "Engineer",
        "applied_date": str(date.today()),
    }, headers=headers)
    app_id = create_res.json()["id"]

    # Update status
    update_res = await client.patch(f"/api/tracker/applications/{app_id}/status", json={
        "new_status": "screening",
        "note": "Recruiter reached out",
    }, headers=headers)
    assert update_res.status_code == 200

    # Events should exist
    events_res = await client.get(f"/api/tracker/applications/{app_id}/events", headers=headers)
    events = events_res.json()
    assert len(events) >= 2  # creation + status change

    status_change = next(e for e in events if e["event_type"] == "status_change" and e.get("new_value") == "screening")
    assert status_change is not None
    assert status_change["old_value"] == "applied"
    assert status_change["note"] == "Recruiter reached out"


@pytest.mark.asyncio
async def test_application_events_append_only(client, test_user_data):
    """Verify that updating status doesn't modify existing events."""
    token = await _get_token(client, test_user_data)
    headers = {"Authorization": f"Bearer {token}"}

    create_res = await client.post("/api/tracker/applications", json={
        "company": "TestCo",
        "role_title": "Dev",
        "applied_date": str(date.today()),
    }, headers=headers)
    app_id = create_res.json()["id"]

    # Make three status updates
    for status in ["screening", "technical", "offer"]:
        await client.patch(f"/api/tracker/applications/{app_id}/status", json={"new_status": status}, headers=headers)

    events_res = await client.get(f"/api/tracker/applications/{app_id}/events", headers=headers)
    events = events_res.json()

    # Should have 4 events (1 creation + 3 updates)
    assert len(events) == 4
    # Events should be in chronological order and unique IDs
    ids = [e["id"] for e in events]
    assert len(set(ids)) == len(ids)  # all unique


@pytest.mark.asyncio
async def test_list_applications_filter_by_status(client, test_user_data):
    token = await _get_token(client, test_user_data)
    headers = {"Authorization": f"Bearer {token}"}

    # Create two applications
    for company, status in [("AppliedCo", "applied"), ("ScreeningCo", "screening")]:
        res = await client.post("/api/tracker/applications", json={
            "company": company, "role_title": "Dev", "applied_date": str(date.today()),
        }, headers=headers)
        if status != "applied":
            await client.patch(f"/api/tracker/applications/{res.json()['id']}/status", json={"new_status": status}, headers=headers)

    filtered_res = await client.get("/api/tracker/applications?status=screening", headers=headers)
    filtered = filtered_res.json()
    assert all(a["status"] == "screening" for a in filtered)
