import os
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv

load_dotenv()

user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
db_name = os.getenv("DB_NAME")

DATABASE_URL = f"postgresql+asyncpg://{user}:{password}@localhost/{db_name}"
engine = create_async_engine(DATABASE_URL)

# Connection generator
async def get_db():
    async with engine.connect() as conn:
        yield conn  # Gives connection to router
        # Connection closes automatically when function in router finishes