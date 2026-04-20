import os
import random
import asyncio
from datetime import datetime, timedelta

import asyncpg
from dotenv import load_dotenv


def _env(name: str, default: str | None = None) -> str:
    val = os.getenv(name, default)
    if val is None or val == "":
        raise RuntimeError(f"Missing required env var: {name}")
    return val


async def main() -> None:
    load_dotenv()

    db_name = _env("DB_NAME")
    db_user = _env("DB_USER")
    db_password = _env("DB_PASSWORD")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = int(os.getenv("DB_PORT", "5432"))

    users_count = int(os.getenv("SEED_USERS_COUNT", "200"))
    cities_count = int(os.getenv("SEED_CITIES_COUNT", "50"))
    categories_count = int(os.getenv("SEED_CATEGORIES_COUNT", "20"))
    offers_count = int(os.getenv("SEED_OFFERS_COUNT", "1000"))
    reservations_per_offer = int(os.getenv("SEED_RES_PER_OFFER", "2"))
    truncate = os.getenv("SEED_TRUNCATE", "1") in ("1", "true", "True", "yes", "YES")

    conn = await asyncpg.connect(
        user=db_user,
        password=db_password,
        database=db_name,
        host=db_host,
        port=db_port,
    )
    try:
        if truncate:
            await conn.execute(
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

        # --- Countries / Cities ---
        await conn.execute("INSERT INTO countries (name) VALUES ($1);", "Polska")
        await conn.executemany(
            "INSERT INTO cities (name, country_id) VALUES ($1, 1);",
            [(f"Miasto {i}",) for i in range(1, cities_count + 1)],
        )

        # --- Users / Addresses ---
        def hash_password(password: str) -> str:
            import bcrypt

            pwd_bytes = password.encode("utf-8")
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(pwd_bytes, salt)
            return hashed.decode("utf-8")

        users_rows: list[tuple[str, str, str, str, str]] = []
        for i in range(1, users_count + 1):
            email = f"user{i}@example.com"
            password_plain = f"Password{i:04d}!!"  # >= 12 chars
            users_rows.append(
                (
                    f"Imie{i}",
                    f"Nazwisko{i}",
                    f"+48 600 000 {i:03d}",
                    email,
                    hash_password(password_plain),
                )
            )

        await conn.executemany(
            """
            INSERT INTO users (first_name, last_name, phone, email, password)
            VALUES ($1, $2, $3, $4, $5);
            """,
            users_rows,
        )

        await conn.executemany(
            """
            INSERT INTO addresses (user_id, city_id, street, house_number, postal_code)
            VALUES ($1, $2, $3, $4, $5);
            """,
            [
                (
                    uid,
                    random.randint(1, cities_count),
                    f"Ulica {uid}",
                    str(random.randint(1, 200)),
                    f"{random.randint(10, 99)}-{random.randint(100, 999)}",
                )
                for uid in range(1, users_count + 1)
            ],
        )

        # --- Categories ---
        await conn.executemany(
            "INSERT INTO categories (name, parent_id) VALUES ($1, $2);",
            [(f"Kategoria {i}", None) for i in range(1, categories_count + 1)],
        )

        # --- Offers ---
        adjectives = ["Szybki", "Tani", "Solidny", "Nowy", "Używany", "Sprawdzony", "Ekologiczny"]
        nouns = ["rower", "telefon", "odkurzacz", "wózek", "laptop", "monitor", "krzesło", "biurko", "głośnik"]

        start_date = datetime.now() - timedelta(days=365 * 2)
        offers: list[tuple[int, str, str, float, datetime, datetime | None]] = []
        for _ in range(offers_count):
            created_at = start_date + timedelta(days=random.randint(0, 365 * 2))
            edited_at = created_at + timedelta(days=random.randint(0, 30))
            title = f"{random.choice(adjectives)} {random.choice(nouns)}"
            description = f"Oferta: {title}. Stan: {random.choice(['idealny', 'dobry', 'średni'])}."
            price = round(random.uniform(0, 5000), 2)
            owner_id = random.randint(1, users_count)
            offers.append((owner_id, title, description, price, created_at, edited_at))

        await conn.executemany(
            """
            INSERT INTO offers (owner_id, title, description, price, created_at, edited_at)
            VALUES ($1, $2, $3, $4, $5, $6);
            """,
            offers,
        )

        # --- Photos (1 per offer) ---
        await conn.executemany(
            "INSERT INTO photos (offer_id, url, sort_order) VALUES ($1, $2, 0);",
            [(oid, f"https://picsum.photos/seed/offer{oid}/600/400") for oid in range(1, offers_count + 1)],
        )

        # --- Offer categories (1-3 per offer) ---
        oc_rows: list[tuple[int, int]] = []
        for oid in range(1, offers_count + 1):
            for cid in random.sample(range(1, categories_count + 1), k=random.randint(1, min(3, categories_count))):
                oc_rows.append((oid, cid))
        await conn.executemany(
            "INSERT INTO offer_categories (offer_id, category_id) VALUES ($1, $2);",
            oc_rows,
        )

        # --- Reservations ---
        statuses = ["ACTIVE", "PENDING", "CANCELED", "EXPIRED", "FULFILLED", "REJECTED"]
        res_rows: list[tuple[int, int, str, datetime, datetime]] = []
        for oid in range(1, offers_count + 1):
            for _ in range(reservations_per_offer):
                created_at = start_date + timedelta(days=random.randint(0, 365 * 2))
                expiry = created_at + timedelta(days=random.randint(1, 3))
                res_rows.append(
                    (
                        oid,
                        random.randint(1, users_count),
                        random.choice(statuses),
                        created_at,
                        expiry,
                    )
                )

        await conn.executemany(
            """
            INSERT INTO reservations (offer_id, user_id, status, created_at, expiry_date)
            VALUES ($1, $2, $3::reservation_status, $4, $5);
            """,
            res_rows,
        )
    finally:
        await conn.close()

    print(
        "Seed complete: "
        f"users={users_count}, cities={cities_count}, categories={categories_count}, "
        f"offers={offers_count}, reservations={offers_count * reservations_per_offer}"
    )


if __name__ == "__main__":
    asyncio.run(main())
