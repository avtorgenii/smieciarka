import os
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv

load_dotenv()

user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
db_name = os.getenv("DB_NAME")
port = os.getenv("DB_PORT", "5432")
host = os.getenv("DB_HOST", "localhost")

DATABASE_URL = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db_name}"
engine = create_async_engine(DATABASE_URL)

# Connection generator
async def get_db():
    async with engine.connect() as conn:
        yield conn  # Gives connection to router
        # Connection closes automatically when function in router finishes