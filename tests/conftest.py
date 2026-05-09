import os
from collections.abc import AsyncIterator

import asyncpg
import bcrypt
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


def _env(name: str, default: str | None = None) -> str:
    val = os.getenv(name, default)
    if val is None or val == "":
        raise RuntimeError(f"Missing required env var: {name}")
    return val


def _pg_dsn() -> str:
    user = _env("DB_USER")
    password = _env("DB_PASSWORD")
    db_name = _env("DB_NAME")
    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "5432"))
    return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture()
async def pg() -> AsyncIterator[asyncpg.Connection]:
    conn = await asyncpg.connect(_pg_dsn())
    try:
        yield conn
    finally:
        await conn.close()


@pytest.fixture()
async def seeded_db(pg: asyncpg.Connection) -> None:
    # Minimal dataset for all endpoints.
    # Assumes migrations already ran (tables + enum exist).
    await pg.execute(
        """
        TRUNCATE TABLE
            reservations,
            offer_categories,
            favorite_offers,
            photos,
            offers,
            addresses,
            users,
            cities,
            countries,
            categories
        RESTART IDENTITY CASCADE;
        """
    )

    await pg.execute("INSERT INTO countries (name) VALUES ('Polska');")
    await pg.execute("INSERT INTO cities (name, country_id) VALUES ('Wroclaw', 1);")
    await pg.execute("INSERT INTO categories (name, parent_id) VALUES ('Kategoria 1', NULL);")

    password_plain = "Password0001!!"
    password_hash = bcrypt.hashpw(password_plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    await pg.execute(
        """
        INSERT INTO users (first_name, last_name, phone, email, password)
        VALUES
            ('Jan', 'Kowalski', '+48 600 000 001', 'jan@example.com',
             $1);
        """,
        password_hash,
    )
    await pg.execute(
        """
        INSERT INTO addresses (user_id, city_id, street, house_number, postal_code)
        VALUES (1, 1, 'Testowa', '1', '00-001');
        """
    )

    await pg.execute(
        """
        INSERT INTO offers (owner_id, title, description, price, created_at, edited_at)
        VALUES
            (1, 'Sofa Test', 'Opis', 100.00, NOW(), NOW()),
            (1, 'Biurko Test', 'Opis', 0.00, NOW() - INTERVAL '1 day', NOW());
        """
    )
    await pg.execute(
        """
        INSERT INTO photos (offer_id, url, sort_order)
        VALUES
            (1, 'https://example.test/offer1.jpg', 0),
            (2, 'https://example.test/offer2.jpg', 0);
        """
    )
    await pg.execute(
        """
        INSERT INTO offer_categories (offer_id, category_id)
        VALUES
            (1, 1),
            (2, 1);
        """
    )


@pytest.fixture()
async def client(seeded_db: None) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _login_and_get_cookie(client: AsyncClient, email: str, password: str) -> str:
    resp = await client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )
    set_cookie = resp.headers.get("set-cookie", "")
    assert resp.status_code in (302, 303), resp.text
    assert "access-token=" in set_cookie or "access_token=" in set_cookie or set_cookie, set_cookie
    return set_cookie


@pytest.fixture()
async def authed_client(client: AsyncClient) -> AsyncIterator[AsyncClient]:
    # Use API's login to obtain auth cookie.
    await _login_and_get_cookie(client, "jan@example.com", "Password0001!!")
    yield client

