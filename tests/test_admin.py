import uuid

import pytest

from tests.conftest import requires_falkordb


@requires_falkordb
@pytest.mark.asyncio
async def test_create_domain(client, admin_headers):
    slug = f"test-domain-{uuid.uuid4().hex[:8]}"
    resp = await client.post(
        "/admin/domains",
        json={"name": "Test Domain", "slug": slug},
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["slug"] == slug
    assert data["name"] == "Test Domain"


@requires_falkordb
@pytest.mark.asyncio
async def test_create_entity_and_retrieve(client, admin_headers):
    slug = f"test-domain-{uuid.uuid4().hex[:8]}"
    await client.post(
        "/admin/domains",
        json={"name": "Test Domain", "slug": slug},
        headers=admin_headers,
    )

    resp = await client.post(
        "/admin/entities",
        json={"name": "Test Entity", "aliases": ["TE", "T Entity"], "domain_slugs": [slug]},
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    entity = resp.json()
    assert entity["name"] == "Test Entity"
    assert "TE" in entity["aliases"]

    resp2 = await client.get(f"/entities/{entity['id']}")
    assert resp2.status_code == 200
    assert resp2.json()["id"] == entity["id"]


@requires_falkordb
@pytest.mark.asyncio
async def test_create_fact_and_conflict_detection(client, admin_headers):
    slug = f"td-{uuid.uuid4().hex[:8]}"
    await client.post("/admin/domains", json={"name": "TD", "slug": slug}, headers=admin_headers)

    entity_resp = await client.post(
        "/admin/entities",
        json={"name": f"Entity {slug}", "aliases": [], "domain_slugs": [slug]},
        headers=admin_headers,
    )
    entity_id = entity_resp.json()["id"]

    attr_resp = await client.post(
        "/admin/attributes",
        json={"name": "Uptime SLA", "unit": "%", "domain_slugs": [slug]},
        headers=admin_headers,
    )
    attribute_id = attr_resp.json()["id"]

    for value in ["99.9", "99.99"]:
        resp = await client.post(
            "/admin/facts",
            json={
                "entity_id": entity_id,
                "attribute_id": attribute_id,
                "value": value,
                "source_type": "admin",
                "confidence": 1.0,
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201, resp.text

    resp = await client.get(f"/entities/{entity_id}")
    assert resp.status_code == 200
    data = resp.json()
    groups = data["fact_groups"]
    assert len(groups) == 1
    assert groups[0]["conflict"] is True
    assert len(groups[0]["facts"]) == 2


@pytest.mark.asyncio
async def test_admin_guard_rejects_missing_key(client):
    resp = await client.post("/admin/domains", json={"name": "X", "slug": "x"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_guard_rejects_wrong_key(client):
    resp = await client.post(
        "/admin/domains",
        json={"name": "X", "slug": "x"},
        headers={"x-admin-key": "wrong"},
    )
    assert resp.status_code == 401
