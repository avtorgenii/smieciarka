import pytest


@pytest.mark.asyncio
async def test_home_page_ok(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_login_page_ok(client):
    resp = await client.get("/login")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_register_page_ok(client):
    resp = await client.get("/register")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_offers_search_default_ok(client):
    resp = await client.get("/offers")
    assert resp.status_code == 200
    # Template contains a form + offer cards; we just smoke-check.
    assert "text/html" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_offers_search_with_query_ok(client):
    resp = await client.get("/offers", params={"search": "Sofa", "page": 1, "size": 20})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_profile_requires_auth(client):
    resp = await client.get("/profile/")
    # fastapi-login will reject missing cookie
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_profile_ok_when_authed(authed_client):
    resp = await authed_client.get("/profile/")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_reservation_flow(authed_client):
    # 1) Reserve offer 1 -> should succeed (creates PENDING reservation)
    resp1 = await authed_client.post("/reservations/1")
    assert resp1.status_code in (200, 201)
    body1 = resp1.text
    assert "Item reserved successfully" in body1

    # 2) Reserve the same offer again -> should fail (already reserved)
    resp2 = await authed_client.post("/reservations/1")
    assert resp2.status_code == 200
    assert "Too late!" in resp2.text


@pytest.mark.asyncio
async def test_logout(client):
    resp = await client.get("/auth/logout", follow_redirects=False)
    assert resp.status_code in (302, 303)

