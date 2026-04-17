"""offers-test

Revision ID: efc36fd41e2c
Revises: 
Create Date: 2026-03-30 13:08:54.479324

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'efc36fd41e2c'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    statements = [
        # 1. Subtables for `addresses`
        """
        CREATE TABLE countries
        (
            id   SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL
        );
        """,
        """
        CREATE TABLE cities
        (
            id         SERIAL PRIMARY KEY,
            name       VARCHAR(100) NOT NULL,
            country_id INTEGER      NOT NULL REFERENCES countries (id) ON DELETE CASCADE
        );
        """,
        # 2. Users
        """
        CREATE TABLE users
        (
            id         SERIAL PRIMARY KEY,
            first_name VARCHAR(50)         NOT NULL,
            last_name  VARCHAR(50)         NOT NULL,
            phone      VARCHAR(20)         NOT NULL,
            email      VARCHAR(100) UNIQUE NOT NULL,
            password   VARCHAR(255)        NOT NULL
        );
        """,
        # 3. Addresses - bound to `countries` and `cities`
        """
        CREATE TABLE addresses
        (
            id           SERIAL PRIMARY KEY,
            user_id      INTEGER      NOT NULL REFERENCES users (id) ON DELETE CASCADE,
            city_id      INTEGER      NOT NULL REFERENCES cities (id),
            street       VARCHAR(255) NOT NULL,
            house_number VARCHAR(10)  NOT NULL,
            postal_code  VARCHAR(15)  NOT NULL
        );
        """,
        # 4. Categories - with recursive relationship for subcategories
        """
        CREATE TABLE categories
        (
            id        SERIAL PRIMARY KEY,
            name      VARCHAR(100) NOT NULL,
            parent_id INTEGER      REFERENCES categories (id) ON DELETE SET NULL
        );
        """,
        # 5. Offers
        """
        CREATE TABLE offers
        (
            id          SERIAL PRIMARY KEY,
            owner_id    INTEGER        NOT NULL REFERENCES users (id) ON DELETE CASCADE,
            title       VARCHAR(255)   NOT NULL,
            description TEXT,
            price       NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
            created_at  TIMESTAMP DEFAULT NOW(),
            edited_at   TIMESTAMP
        );
        """,
        # 6. Photos
        """
        CREATE TABLE photos
        (
            id       SERIAL PRIMARY KEY,
            offer_id INTEGER NOT NULL REFERENCES offers (id) ON DELETE CASCADE,
            url      TEXT    NOT NULL
        );
        """,
        # 7. User favorite (marked) offers
        """
        CREATE TABLE favorite_offers
        (
            user_id  INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
            offer_id INTEGER NOT NULL REFERENCES offers (id) ON DELETE CASCADE,
            PRIMARY KEY (user_id, offer_id)
        );
        """,
        # 8. Offer reservations
        """
        CREATE TABLE reservations
        (
            id          SERIAL PRIMARY KEY,
            offer_id    INTEGER     NOT NULL REFERENCES offers (id) ON DELETE CASCADE,
            user_id     INTEGER     NOT NULL REFERENCES users (id) ON DELETE CASCADE,
            status      VARCHAR(50) NOT NULL DEFAULT 'pending',
            created_at  TIMESTAMP            DEFAULT NOW(),
            expiry_date TIMESTAMP
        );
        """,
        # 9. Offer categories
        """
        CREATE TABLE offer_categories
        (
            offer_id    INTEGER NOT NULL REFERENCES offers (id) ON DELETE CASCADE,
            category_id INTEGER NOT NULL REFERENCES categories (id) ON DELETE CASCADE,
            PRIMARY KEY (offer_id, category_id)
        );
        """
    ]

    for statement in statements:
        op.execute(sa.text(statement))


def downgrade() -> None:
    """Downgrade schema."""
    # Deleting in reverse order
    tables = [
        "offer_categories",
        "reservations",
        "favorite_offers",
        "photos",
        "offers",
        "categories",
        "addresses",
        "users",
        "cities",
        "countries"
    ]

    for table in tables:
        op.execute(sa.text(f"DROP TABLE IF EXISTS {table} CASCADE;"))
