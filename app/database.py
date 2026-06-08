import os
import random

from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv

load_dotenv()

user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
db_name = os.getenv("DB_NAME")
host = os.getenv("DB_HOST", "localhost")

# DB_PORT=5433 (Primary) oraz DB_PORT_2=5434 (Standby)
port = os.getenv("DB_PORT", "5433")
secondaryPort = os.getenv("DB_PORT_2", "5434")


PRIMARY_URL = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db_name}"
STANDBY_URL = f"postgresql+asyncpg://{user}:{password}@{host}:{secondaryPort}/{db_name}"


engine_primary = create_async_engine(PRIMARY_URL)
engine_standby = create_async_engine(STANDBY_URL)




# Ten generator dajesz tam, gdzie robisz INSERT / UPDATE / DELETE
async def get_write_db():
    async with engine_primary.connect() as conn:
        yield conn  # Daje połączenie do routera (baza główna - port 5433)

# Ten generator dajesz tam, gdzie robisz SELECT (przeglądanie ofert)
async def get_read_db():
    random_engine = random.choice([engine_primary, engine_standby])
    async with random_engine.connect() as conn:
        yield conn  # Daje połączenie do routera (replika - port 5434)
        # Połączenie zamyka się automatycznie po zakończeniu funkcji w routerze